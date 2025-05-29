import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.from_name = os.getenv("FROM_NAME", "Your App")
        self.base_url = os.getenv("BASE_URL", "http://localhost:8000")
        self.app_name = os.getenv("APP_NAME", "Your App")

        if not all([self.smtp_username, self.smtp_password]):
            logger.warning("Email service not properly configured. Missing SMTP credentials.")

    async def send_email(
            self,
            to_email: str,
            subject: str,
            html_body: str,
            text_body: Optional[str] = None
    ) -> bool:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email

            if text_body:
                text_part = MIMEText(text_body, 'plain')
                msg.attach(text_part)

            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def get_verification_email_html(self, username: str, verification_url: str) -> str:
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify Your Email Address</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f4f4f4;
                }}
                .container {{
                    background-color: #ffffff;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #2563eb;
                    margin-bottom: 10px;
                }}
                h1 {{
                    color: #1f2937;
                    margin-bottom: 20px;
                    font-size: 24px;
                }}
                .verification-button {{
                    display: inline-block;
                    background-color: #2563eb;
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 16px;
                    margin: 20px 0;
                }}
                .verification-link {{
                    background-color: #f8fafc;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #2563eb;
                    margin: 20px 0;
                    word-break: break-all;
                    font-family: monospace;
                    font-size: 12px;
                    color: #6b7280;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    text-align: center;
                    color: #6b7280;
                    font-size: 14px;
                }}
                .warning {{
                    background-color: #fef3c7;
                    border: 1px solid #f59e0b;
                    border-radius: 6px;
                    padding: 12px;
                    margin: 20px 0;
                    color: #92400e;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">{self.app_name}</div>
                </div>

                <h1>Welcome, {username}!</h1>

                <p>Thank you for signing up with {self.app_name}. To complete your registration and activate your account, please verify your email address by clicking the button below:</p>

                <div style="text-align: center;">
                    <a href="{verification_url}" class="verification-button">Verify Email Address</a>
                </div>

                <p>If the button above doesn't work, you can copy and paste this link into your browser:</p>

                <div class="verification-link">
                    {verification_url}
                </div>

                <div class="warning">
                    <strong>Security Note:</strong> This verification link will expire in 24 hours for security reasons. If you didn't create an account with {self.app_name}, please ignore this email.
                </div>

                <p>Once your email is verified, you'll be able to access all features of your account.</p>

                <div class="footer">
                    <p>Best regards,<br>The {self.app_name} Team</p>
                    <p style="margin-top: 20px; font-size: 12px;">
                        This email was sent to verify your account registration. If you didn't sign up for {self.app_name}, you can safely ignore this email.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

    def get_welcome_email_html(self, username: str, login_url: str) -> str:
        """Generate HTML for welcome email"""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to {self.app_name}!</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f4f4f4;
                }}
                .container {{
                    background-color: #ffffff;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #059669;
                    margin-bottom: 10px;
                }}
                .success-icon {{
                    width: 60px;
                    height: 60px;
                    background-color: #10b981;
                    border-radius: 50%;
                    margin: 0 auto 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 24px;
                }}
                h1 {{
                    color: #1f2937;
                    margin-bottom: 20px;
                    font-size: 24px;
                }}
                .login-button {{
                    display: inline-block;
                    background-color: #059669;
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 16px;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    text-align: center;
                    color: #6b7280;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">{self.app_name}</div>
                    <div class="success-icon">✓</div>
                </div>

                <h1>Welcome to {self.app_name}, {username}!</h1>

                <p>🎉 <strong>Congratulations!</strong> Your email has been successfully verified and your account is now active.</p>

                <p>You're all set to start exploring everything {self.app_name} has to offer. Click the button below to log in and get started:</p>

                <div style="text-align: center;">
                    <a href="{login_url}" class="login-button">Log In to Your Account</a>
                </div>

                <p>We're excited to have you as part of the {self.app_name} community. If you have any questions or feedback, don't hesitate to reach out to us.</p>

                <div class="footer">
                    <p>Thank you for choosing {self.app_name}!<br>The {self.app_name} Team</p>
                </div>
            </div>
        </body>
        </html>
        """


email_service = EmailService()


async def send_verification_email(email: str, username: str, verification_token: str) -> bool:
    try:
        verification_url = f"{email_service.base_url}/auth/verify-email?token={verification_token}"

        html_body = email_service.get_verification_email_html(username, verification_url)

        text_body = f"""
Hello {username},

Welcome to {email_service.app_name}!

Please verify your email address by clicking the link below:
{verification_url}

If you didn't create an account, please ignore this email.

This verification link will expire in 24 hours for security reasons.

Best regards,
The {email_service.app_name} Team
        """

        subject = f"Verify your email address - {email_service.app_name}"

        success = await email_service.send_email(
            to_email=email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )

        if success:
            logger.info(f"Verification email sent successfully to {email}")
        else:
            logger.error(f"Failed to send verification email to {email}")

        return success

    except Exception as e:
        logger.error(f"Error sending verification email to {email}: {str(e)}")
        return False


async def send_welcome_email(email: str, username: str) -> bool:
    """Send welcome email after successful verification"""
    try:
        login_url = f"{email_service.base_url}/login"

        html_body = email_service.get_welcome_email_html(username, login_url)

        text_body = f"""
Hello {username},

Welcome to {email_service.app_name}!

Your account has been successfully verified and you can now log in.

Thank you for joining us!

Best regards,
The {email_service.app_name} Team
        """

        subject = f"Welcome to {email_service.app_name}!"

        success = await email_service.send_email(
            to_email=email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )

        if success:
            logger.info(f"Welcome email sent successfully to {email}")
        else:
            logger.error(f"Failed to send welcome email to {email}")

        return success

    except Exception as e:
        logger.error(f"Error sending welcome email to {email}: {str(e)}")
        return False
