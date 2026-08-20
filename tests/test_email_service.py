import logging
from unittest.mock import patch

from services.email_service import send_password_reset_email


def test_send_email_success():
    with patch("services.email_service.Config.RESEND_API_KEY", "test_key"), \
         patch("services.email_service.Config.MAIL_FROM", "test@test.com"), \
         patch("services.email_service.resend.Emails.send") as mock_send:

        result = send_password_reset_email("user@test.com", "http://reset.link")

        assert result is True
        mock_send.assert_called_once()
        args = mock_send.call_args[0][0]
        assert args["to"] == "user@test.com"
        assert args["from"] == "test@test.com"
        assert "http://reset.link" in args["html"]

def test_send_email_missing_api_key():
    with patch("services.email_service.Config.RESEND_API_KEY", ""), \
         patch("services.email_service.Config.MAIL_FROM", "test@test.com"), \
         patch("services.email_service.resend.Emails.send") as mock_send:

        result = send_password_reset_email("user@test.com", "http://reset.link")

        assert result is False
        mock_send.assert_not_called()

def test_send_email_missing_mail_from():
    with patch("services.email_service.Config.RESEND_API_KEY", "test_key"), \
         patch("services.email_service.Config.MAIL_FROM", ""), \
         patch("services.email_service.resend.Emails.send") as mock_send:

        result = send_password_reset_email("user@test.com", "http://reset.link")

        assert result is False
        mock_send.assert_not_called()

def test_send_email_catches_provider_exception(caplog):
    with patch("services.email_service.Config.RESEND_API_KEY", "test_key"), \
         patch("services.email_service.Config.MAIL_FROM", "test@test.com"), \
         patch("services.email_service.resend.Emails.send", side_effect=Exception("API Down")):

        with caplog.at_level(logging.ERROR):
            result = send_password_reset_email("user@test.com", "http://reset.link")

            assert result is False
            assert "Failed to send password reset email to user@test.com" in caplog.text
            assert "API Down" in caplog.text
            assert "http://reset.link" not in caplog.text  # URL not logged
