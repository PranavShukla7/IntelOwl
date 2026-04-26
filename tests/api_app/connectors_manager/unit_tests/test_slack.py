# This file is a part of IntelOwl https://github.com/intelowlproject/IntelOwl
# See the file 'LICENSE' for copying permission.

from unittest.mock import patch

from api_app.choices import Classification
from api_app.connectors_manager.connectors.slack import Slack

from .base_test_class import BaseConnectorTest


class MockClient:
    def __init__(self, *args, **kwargs):
        pass

    def chat_postMessage(self, *args, **kwargs):
        pass


class SlackTestCase(BaseConnectorTest):
    connector_class = Slack

    def get_mocked_response(self):
        return patch("slack_sdk.WebClient", side_effect=MockClient)

    def test_slack_run(self):
        params = {
            "channel": "#general",
            "slack_username": "intelowl",
            "token": "xoxb-123",
        }
        res = self.execute_run_logic(
            "Slack",
            observable_name="8.8.8.8",
            observable_type=Classification.IP,
            params=params,
        )
        self.assertEqual(res, {})
