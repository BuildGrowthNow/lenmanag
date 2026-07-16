import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_verification_email(
    email: str, verification_token: str, base_url: str
) -> bool:
    try:
        from resend import Resend  # type: ignore[import-untyped]

        if not settings.resend_api_key:
            logger.warning("RESEND_API_KEY not configured, skipping email send")
            return False

        resend = Resend(api_key=settings.resend_api_key)

        verification_url = f"{base_url}/verify-email?token={verification_token}"

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
