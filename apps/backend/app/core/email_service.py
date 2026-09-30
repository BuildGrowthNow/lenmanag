import logging
from html import escape

try:
    import resend  # type: ignore[import-untyped]
except ImportError:  # Optional in local/test environments.
    resend = None  # type: ignore[assignment]

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_verification_email(email: str, verification_token: str) -> bool:
    try:
        if not settings.resend_api_key or resend is None:
            logger.warning("RESEND_API_KEY not configured, skipping email send")
            return False

        resend.api_key = settings.resend_api_key  # type: ignore[attr-defined]
        frontend_url = settings.frontend_url.rstrip("/")
        verification_url = f"{frontend_url}/verify-email?token={verification_token}"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #0c1016;">Verify your email address</h2>
                    <p>Thank you for signing up! Please verify your email address by clicking the button below:</p>
                    <div style="margin: 30px 0;">
                        <a href="{verification_url}"
                           style="background-color: #0c1016; color: white; padding: 12px 24px;
                                  text-decoration: none; border-radius: 6px; display: inline-block;">
                            Verify Email
                        </a>
                    </div>
                    <p style="color: #666; font-size: 14px;">
                        Or copy and paste this link into your browser:<br>
                        <a href="{verification_url}" style="color: #0c1016;">{verification_url}</a>
                    </p>
                    <p style="color: #999; font-size: 12px; margin-top: 40px;">
                        If you didn't create an account, you can safely ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """

        params = {
            "from": settings.resend_from_email,
            "to": [email],
            "subject": "Verify your email address",
            "html": html_content,
        }

        result = resend.Emails.send(params)  # type: ignore[attr-defined]
        logger.info(f"Verification email sent to {email}, id: {result.id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")
        return False


async def send_password_reset_email(email: str, reset_token: str) -> bool:
    try:
        if not settings.resend_api_key or resend is None:
            logger.warning("RESEND_API_KEY not configured, skipping email send")
            return False

        resend.api_key = settings.resend_api_key  # type: ignore[attr-defined]
        frontend_url = settings.frontend_url.rstrip("/")
        reset_url = f"{frontend_url}/reset-password?token={reset_token}"

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #0c1016;">Reset your password</h2>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <div style="margin: 30px 0;">
                        <a href="{reset_url}"
                           style="background-color: #0c1016; color: white; padding: 12px 24px;
                                  text-decoration: none; border-radius: 6px; display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    <p style="color: #666; font-size: 14px;">
                        Or copy and paste this link into your browser:<br>
                        <a href="{reset_url}" style="color: #0c1016;">{reset_url}</a>
                    </p>
                    <p style="color: #666; font-size: 14px;">
                        This link will expire in 24 hours.
                    </p>
                    <p style="color: #999; font-size: 12px; margin-top: 40px;">
                        If you didn't request a password reset, you can safely ignore this email.
                        Your password will remain unchanged.
                    </p>
                </div>
            </body>
        </html>
        """

        params = {
            "from": settings.resend_from_email,
            "to": [email],
            "subject": "Reset your password",
            "html": html_content,
        }

        result = resend.Emails.send(params)  # type: ignore[attr-defined]
        logger.info(f"Password reset email sent to {email}, id: {result.id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        return False


async def send_public_form_notification(
    *,
    recipient: str,
    submission_id: str,
    site_id: str,
    name: str,
    email: str,
    message: str,
    phone: str = "",
    company: str = "",
) -> bool:
    """Deliver a generated-site submission to the configured business inbox."""
    try:
        if not settings.resend_api_key or not recipient or resend is None:
            logger.warning("Public form notification unavailable: email delivery is not configured")
            return False
        resend.api_key = settings.resend_api_key  # type: ignore[attr-defined]
        html_content = (
            "<h2>New generated-site form submission</h2>"
            f"<p><strong>Site:</strong> {escape(site_id)}</p>"
            f"<p><strong>Name:</strong> {escape(name)}</p>"
            f"<p><strong>Email:</strong> {escape(email)}</p>"
            f"<p><strong>Company:</strong> {escape(company)}</p>"
            f"<p><strong>Phone:</strong> {escape(phone)}</p>"
            f"<p><strong>Message:</strong><br>{escape(message).replace(chr(10), '<br>')}</p>"
            f"<p><small>Submission id: {escape(submission_id)}</small></p>"
        )
        resend.Emails.send(  # type: ignore[attr-defined]
            {
                "from": settings.resend_from_email,
                "to": [recipient],
                "reply_to": [email],
                "subject": f"New website inquiry from {name or email}",
                "html": html_content,
            }
        )
        logger.info("Public form notification sent for %s", submission_id)
        return True
    except Exception as exc:
        logger.error("Public form notification failed for %s: %s", submission_id, exc)
        return False
