# This file is a part of IntelOwl https://github.com/intelowlproject/IntelOwl
# See the file 'LICENSE' for copying permission.

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from api_app.analyzers_manager.classes import ObservableAnalyzer
from api_app.analyzers_manager.exceptions import AnalyzerRunException
from api_app.choices import Classification
from tests.mock_utils import MockUpResponse, if_mock_connections, patch


class HybridAnalysisGet(ObservableAnalyzer):
    url: str = "https://www.hybrid-analysis.com"
    api_url: str = f"{url}/api/v2/"
    sample_url: str = f"{url}/sample"

    _api_key_name: str

    @classmethod
    def update(cls) -> bool:
        """Return True indicating analyzer metadata update succeeded (no-op)."""
        return True

    def _fetch_sample_summary(
        self, sha256: str, headers: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch sample overview/summary for a given sha256.
        Returns the parsed JSON dict on success, or None on failure.
        """
        overview_uri = f"overview/{sha256}"
        try:
            overview_response = requests.get(
                self.api_url + overview_uri, headers=headers
            )
            overview_response.raise_for_status()
            summary = overview_response.json()
            return summary if isinstance(summary, dict) else None
        except requests.RequestException:
            return None

    def run(self) -> Any:
        """
        Execute the analyzer for the configured observable.
        Returns the parsed JSON result (list or dict) as produced by Hybrid Analysis,
        augmenting results with `permalink` where applicable.
        """
        headers = {
            "api-key": self._api_key_name,
            "user-agent": "Falcon Sandbox",
            "accept": "application/json",
        }

        obs_clsfn = self.observable_classification

        if obs_clsfn == Classification.DOMAIN:
            data = {"domain": self.observable_name}
            uri = "search/terms"
            response = requests.post(self.api_url + uri, data=data, headers=headers)

        elif obs_clsfn == Classification.IP:
            data = {"host": self.observable_name}
            uri = "search/terms"
            response = requests.post(self.api_url + uri, data=data, headers=headers)

        elif obs_clsfn == Classification.URL:
            data = {"url": self.observable_name}
            uri = "search/terms"
            response = requests.post(self.api_url + uri, data=data, headers=headers)

        elif obs_clsfn == Classification.HASH:
            uri = "search/hash"
            params = {"hash": self.observable_name}
            response = requests.get(self.api_url + uri, params=params, headers=headers)

        else:
            raise AnalyzerRunException(
                f"not supported observable type {obs_clsfn}. Supported are: hash, ip, domain and url"
            )

        response.raise_for_status()
        result = response.json()

        # HASH handling: result may be list of full summaries OR list of hashes/minimal entries
        if obs_clsfn == Classification.HASH and isinstance(result, list):
            detailed_results: List[Dict[str, Any]] = []
            for item in result:
                # If item already looks like a full summary (contains job_id/verdict/threat_score)
                if isinstance(item, dict) and (
                    item.get("job_id")
                    or item.get("verdict")
                    or item.get("threat_score")
                ):
                    sha256 = item.get("sha256", "")
                    job_id = item.get("job_id", "")
                    if sha256:
                        item["permalink"] = f"{self.sample_url}/{sha256}"
                        if job_id:
                            item["permalink"] += f"/{job_id}"
                    detailed_results.append(item)
                    continue

                # Otherwise treat item as minimal (string hash) or dict with 'sha256'/'hash'
                sha256 = (
                    item
                    if isinstance(item, str)
                    else item.get("sha256") or item.get("hash")
                )
                if not sha256:
                    # skip malformed entry
                    continue

                summary = self._fetch_sample_summary(sha256, headers)
                if summary:
                    # ensure permalink exists
                    job_id = summary.get("job_id", "")
                    summary["permalink"] = f"{self.sample_url}/{sha256}"
                    if job_id:
                        summary["permalink"] += f"/{job_id}"
                    detailed_results.append(summary)
                else:
                    # fallback to minimal structure with permalink
                    if isinstance(item, dict):
                        item["permalink"] = f"{self.sample_url}/{sha256}"
                        detailed_results.append(item)
                    else:
                        detailed_results.append(
                            {
                                "sha256": sha256,
                                "permalink": f"{self.sample_url}/{sha256}",
                            }
                        )

            result = detailed_results if detailed_results else result

        else:
            # For non-hash searches, attach permalink if possible
            if isinstance(result, list):
                for job in result:
                    sha256 = job.get("sha256", "")
                    job_id = job.get("job_id", "")
                    if sha256:
                        job["permalink"] = f"{self.sample_url}/{sha256}"
                        if job_id:
                            job["permalink"] += f"/{job_id}"

        return result

    @classmethod
    def _monkeypatch(cls):
        """
        Provide mocks for tests: GET /search/hash -> list of hashes,
        GET /overview/<sha> -> full summary, POST /search/terms -> job list.
        """

        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")

            if "search/hash" in url and kwargs.get("params"):
                return MockUpResponse(["abcdefgh"], 200)

            if "overview/" in url:
                return MockUpResponse(
                    {"job_id": "1", "sha256": "abcdefgh", "verdict": "malicious"}, 200
                )

            return MockUpResponse([{"job_id": "1", "sha256": "abcdefgh"}], 200)

        patches = [
            if_mock_connections(
                patch("requests.get", side_effect=side_effect),
                patch("requests.post", side_effect=side_effect),
            )
        ]
        return super()._monkeypatch(patches=patches)
