# This file is a part of IntelOwl https://github.com/intelowlproject/IntelOwl
# See the file 'LICENSE' for copying permission.

import requests

from api_app.analyzers_manager.classes import ObservableAnalyzer
from api_app.analyzers_manager.exceptions import AnalyzerRunException
from api_app.choices import Classification


class HybridAnalysisGet(ObservableAnalyzer):
    url: str = "https://www.hybrid-analysis.com"
    api_url: str = f"{url}/api/v2/"
    sample_url: str = f"{url}/sample"

    _api_key_name: str

    @classmethod
    def update(cls) -> bool:
        pass

    def run(self):
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
                f"not supported observable type {obs_clsfn}. "
                "Supported are: hash, ip, domain and url"
            )

        response.raise_for_status()
        result = response.json()

        if obs_clsfn == Classification.HASH and isinstance(result, list):
            detailed_results = []
            for item in result:
                if isinstance(item, dict) and (
                    item.get("job_id") or item.get("verdict") or item.get("threat_score")
                ):
                    sha256 = item.get("sha256", "")
                    job_id = item.get("job_id", "")
                    if sha256:
                        item["permalink"] = f"{self.sample_url}/{sha256}"
                        if job_id:
                            item["permalink"] += f"/{job_id}"
                    detailed_results.append(item)
                else:
                    sha256 = item if isinstance(item, str) else item.get("sha256") or item.get("hash")
                    if sha256:
                        overview_uri = f"overview/{sha256}"
                        try:
                            overview_response = requests.get(
                                self.api_url + overview_uri, headers=headers
                            )
                            overview_response.raise_for_status()
                            sample_summary = overview_response.json()
                            job_id = sample_summary.get("job_id", "")
                            sample_summary["permalink"] = f"{self.sample_url}/{sha256}"
                            if job_id:
                                sample_summary["permalink"] += f"/{job_id}"
                            detailed_results.append(sample_summary)
                        except requests.RequestException:
                            if isinstance(item, dict):
                                item["permalink"] = f"{self.sample_url}/{sha256}"
                                detailed_results.append(item)
                            elif isinstance(item, str):
                                detailed_results.append(
                                    {
                                        "sha256": sha256,
                                        "permalink": f"{self.sample_url}/{sha256}",
                                    }
                                )
            result = detailed_results if detailed_results else result
        else:
            if isinstance(result, list):
                for job in result:
                    sha256 = job.get("sha256", "")
                    job_id = job.get("job_id", "")
                    if sha256:
                        job["permalink"] = f"{self.sample_url}/{sha256}"
                        if job_id:
                            job["permalink"] += f"/{job_id}"

        return result
<<<<<<< HEAD
=======

    @classmethod
    def _monkeypatch(cls):
        def side_effect(*args, **kwargs):
            url = args[0] if args else kwargs.get("url", "")
            # Mock GET /search/hash response (returns list of hashes)
            if "search/hash" in url and kwargs.get("params"):
                return MockUpResponse(
                    ["abcdefgh"],
                    200,
                )
            # Mock GET /overview/{sha256} response (returns full SampleSummary)
            elif "overview/" in url:
                return MockUpResponse(
                    {
                        "job_id": "1",
                        "sha256": "abcdefgh",
                        "verdict": "malicious",
                    },
                    200,
                )
            # Mock POST /search/terms response (for domain, IP, URL)
            else:
                return MockUpResponse(
                    [
                        {
                            "job_id": "1",
                            "sha256": "abcdefgh",
                        }
                    ],
                    200,
                )

        patches = [
            if_mock_connections(
                patch("requests.get", side_effect=side_effect),
                patch("requests.post", side_effect=side_effect),
            )
        ]
        return super()._monkeypatch(patches=patches)
>>>>>>> 781a8a22 (Initial sync before fix)
