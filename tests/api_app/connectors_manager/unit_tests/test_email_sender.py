# This file is a part of IntelOwl https://github.com/intelowlproject/IntelOwl
# See the file 'LICENSE' for copying permission.

from unittest.mock import patch

from api_app.choices import Classification
from api_app.connectors_manager.connectors.email_sender import EmailSender

from .base_test_class import BaseConnectorTest


class EmailSenderTestCase(BaseConnectorTest):
    connector_class = EmailSender

    def get_mocked_response(self):
        return patch("django.core.mail.EmailMessage.send", return_value="Email sent")

    def test_email_sender_run(self):
        params = {
            "subject": "Test Issue",
            "body": "Test body",
        }
        res = self.execute_run_logic(
            "EmailSender",
            observable_name="test@example.com",
            observable_type=Classification.GENERIC,
            params=params,
        )
        self.assertIn("subject", res)
        self.assertEqual(res["to"], ["test@example.com"])
