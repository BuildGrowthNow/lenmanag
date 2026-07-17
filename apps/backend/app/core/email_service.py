import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_resend_client():  # type: ignore[no-untyped-def]
    from resend import Resend  # type: ignore[import-untyped]

    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not configured, skipping email send")
        return None
    return Resend(api_key=settings.resend_api_key)


async def send_verification_email(email: str, verification_token: str) -> bool:
    try:
        resend = _get_resend_client()
        if not resend:
            return False

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

        result = resend.emails.send(params)
        logger.info(f"Verification email sent to {email}, id: {result.get('id')}")
        return True

    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")
        return False


async def send_password_reset_email(email: str, reset_token: str) -> bool:
    try:
        resend = _get_resend_client()
        if not resend:
            return False

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

        result = resend.emails.send(params)
        logger.info(f"Password reset email sent to {email}, id: {result.get('id')}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        return False
