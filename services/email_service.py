import logging

import resend

from config import Config

logger = logging.getLogger(__name__)

def send_password_reset_email(recipient_email, reset_url):
    """
    Send a password reset email using Resend.
    Returns True if successfully sent (or simulated in tests), False otherwise.
    """
    if not Config.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY is not configured. Skipping password reset email delivery.")
        return False

    if not Config.MAIL_FROM:
        logger.warning("MAIL_FROM is not configured. Skipping password reset email delivery.")
        return False

    resend.api_key = Config.RESEND_API_KEY

    subject = "Password Reset - TalentAI"
    html_content = (
        "<p>Hello,</p>"
        "<p>You requested a password reset for your TalentAI account. Click the link below to set a new password:</p>"
        f'<p><a href="{reset_url}" style="display:inline-block;padding:10px 20px;'
        'background-color:#6366F1;color:white;text-decoration:none;border-radius:5px;">Reset Password</a></p>'
        "<p>If you did not request this, please ignore this email.</p>"
    )

    text_content = (
        "Hello,\n\nYou requested a password reset. Please copy and paste the following URL into your browser:\n\n"
        f"{reset_url}\n\nIf you did not request this, please ignore this email."
    )

    try:
        resend.Emails.send({
            "from": Config.MAIL_FROM,
            "to": recipient_email,
            "subject": subject,
            "html": html_content,
            "text": text_content,
        })
        return True
    except Exception as e:
        # Log the exception safely without exposing tokens or the full URL
        logger.error(f"Failed to send password reset email to {recipient_email}. Provider Error: {str(e)}")
        return False
