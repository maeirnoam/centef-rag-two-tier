"""
Email service for CENTEF RAG system.
Handles sending password reset emails and other notifications.
Uses Gmail SMTP for sending emails.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)

# Email configuration from environment variables
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
SENDER_NAME = os.getenv("SENDER_NAME", "CENTEF AI Platform")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://centef-rag-frontend-51695993895.us-central1.run.app")

# Gmail SMTP configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def send_password_reset_email(to_email: str, reset_token: str, user_name: Optional[str] = None) -> bool:
    """
    Send a password reset email to the user using Gmail SMTP.

    Args:
        to_email: Recipient email address
        reset_token: Password reset token
        user_name: Optional user name for personalization

    Returns:
        True if email was sent successfully, False otherwise
    """
    if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
        logger.warning("Gmail credentials not configured. Email not sent.")
        logger.info(f"Development mode: Reset link would be sent to {to_email}")
        logger.info(f"Reset URL: {FRONTEND_URL}/reset-password.html?token={reset_token}")
        return False

    try:
        # Create reset URL
        reset_url = f"{FRONTEND_URL}/reset-password.html?token={reset_token}"

        # Personalize greeting
        greeting = f"Hello {user_name}," if user_name else "Hello,"

        # Create email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #080851;
                    background-color: #fcfdfd;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    padding: 20px 0;
                    background-color: #142772;
                    color: #fcfdfd;
                    border-radius: 8px 8px 0 0;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .content {{
                    background-color: #ffffff;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    margin: 20px 0;
                    background-color: #388ed3;
                    color: #ffffff !important;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 500;
                }}
                .button:hover {{
                    background-color: #2b7bb7;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #6b6f97;
                    font-size: 14px;
                }}
                .warning {{
                    background-color: #fef3c7;
                    border-left: 4px solid #f59e0b;
                    padding: 12px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .code {{
                    background-color: #f3f4f6;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-family: monospace;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>CENTEF AI Platform</h1>
                </div>
                <div class="content">
                    <p>{greeting}</p>

                    <p>You recently requested to reset your password for your CENTEF AI Platform account. Click the button below to reset it:</p>

                    <div style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Your Password</a>
                    </div>

                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #388ed3;">{reset_url}</p>

                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong><br>
                        This password reset link will expire in <strong>1 hour</strong> for security reasons.
                    </div>

                    <p>If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>

                    <p>For security reasons, please do not share this link with anyone.</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from CENTEF AI Platform.<br>
                    Please do not reply to this email.</p>
                    <p>&copy; 2024 CENTEF. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_content = f"""
        {greeting}

        You recently requested to reset your password for your CENTEF AI Platform account.

        Click this link to reset your password:
        {reset_url}

        This link will expire in 1 hour for security reasons.

        If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.

        For security reasons, please do not share this link with anyone.

        ---
        This is an automated message from CENTEF AI Platform.
        Please do not reply to this email.

        © 2024 CENTEF. All rights reserved.
        """

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Reset Your CENTEF AI Platform Password"
        msg['From'] = f"{SENDER_NAME} <{GMAIL_EMAIL}>"
        msg['To'] = to_email

        # Attach both plain text and HTML versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)

        # Send email via Gmail SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Password reset email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Error sending password reset email: {e}", exc_info=True)
        return False


def send_welcome_email(to_email: str, user_name: str, temporary_password: Optional[str] = None) -> bool:
    """
    Send a welcome email to a new user using Gmail SMTP.

    Args:
        to_email: Recipient email address
        user_name: User's full name
        temporary_password: Optional temporary password

    Returns:
        True if email was sent successfully, False otherwise
    """
    if not GMAIL_EMAIL or not GMAIL_APP_PASSWORD:
        logger.warning("Gmail credentials not configured. Email not sent.")
        return False

    try:
        login_url = f"{FRONTEND_URL}/login.html"

        # Create email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #080851;
                    background-color: #fcfdfd;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    padding: 20px 0;
                    background-color: #142772;
                    color: #fcfdfd;
                    border-radius: 8px 8px 0 0;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .content {{
                    background-color: #ffffff;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    margin: 20px 0;
                    background-color: #388ed3;
                    color: #ffffff !important;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 500;
                }}
                .credentials {{
                    background-color: #f3f4f6;
                    padding: 15px;
                    border-radius: 6px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #6b6f97;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to CENTEF AI Platform</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>

                    <p>Welcome to the CENTEF AI Platform! Your account has been created successfully.</p>

                    {"<div class='credentials'><p><strong>Your login credentials:</strong></p><p>Email: " + to_email + "</p><p>Temporary Password: <code>" + temporary_password + "</code></p></div>" if temporary_password else ""}

                    <div style="text-align: center;">
                        <a href="{login_url}" class="button">Login Now</a>
                    </div>

                    {"<p><strong>Important:</strong> Please change your password after your first login for security.</p>" if temporary_password else ""}

                    <p>If you have any questions or need assistance, please don't hesitate to reach out.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 CENTEF. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Build credentials section if temporary password is provided
        credentials_text = ""
        if temporary_password:
            credentials_text = f"""Your login credentials:
Email: {to_email}
Temporary Password: {temporary_password}

Important: Please change your password after your first login for security.
"""

        text_content = f"""
        Hello {user_name},

        Welcome to the CENTEF AI Platform! Your account has been created successfully.

        {credentials_text}
        Login here: {login_url}

        If you have any questions or need assistance, please don't hesitate to reach out.

        © 2024 CENTEF. All rights reserved.
        """

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Welcome to CENTEF AI Platform"
        msg['From'] = f"{SENDER_NAME} <{GMAIL_EMAIL}>"
        msg['To'] = to_email

        # Attach both plain text and HTML versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)

        # Send email via Gmail SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Welcome email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Error sending welcome email: {e}", exc_info=True)
        return False
