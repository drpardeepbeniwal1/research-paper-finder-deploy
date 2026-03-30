"""
Email notification service for search completion.
"""
import smtplib
import logging
from typing import Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import get_settings

settings = get_settings()
log = logging.getLogger("rpf")

# Email config (set in .env)
SMTP_SERVER = settings.smtp_server if hasattr(settings, 'smtp_server') else None
SMTP_PORT = settings.smtp_port if hasattr(settings, 'smtp_port') else 587
SMTP_USER = settings.smtp_user if hasattr(settings, 'smtp_user') else None
SMTP_PASSWORD = settings.smtp_password if hasattr(settings, 'smtp_password') else None
SMTP_FROM = settings.smtp_from if hasattr(settings, 'smtp_from') else "noreply@research-paper-finder.com"


def _as_result_dict(result: Any) -> dict:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return {}


async def send_completion_email(recipient_email: str, query: str, result: Any) -> bool:
    """Send email notification when search completes."""
    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASSWORD:
        log.warning("Email not configured. Set SMTP_SERVER, SMTP_USER, SMTP_PASSWORD in .env")
        return False

    try:
        result_data = _as_result_dict(result)
        total_papers = result_data.get("total_found", 0)
        confirmed = len(result_data.get("papers", []))
        suspicious = result_data.get("total_suspicious", 0)
        rejected = result_data.get("total_rejected", 0)

        subject = f"Research Papers Found: {query}"

        html_body = f"""
        <html>
            <body>
                <h2>Search Complete: {query}</h2>
                <p>Your research paper search has completed.</p>
                <hr>
                <h3>Results Summary</h3>
                <ul>
                    <li><strong>Confirmed (≥70 relevance):</strong> {confirmed} papers</li>
                    <li><strong>Suspicious (40-69 relevance):</strong> {suspicious} papers</li>
                    <li><strong>Rejected (<40 relevance):</strong> {rejected} papers</li>
                    <li><strong>Total Found:</strong> {total_papers} papers</li>
                </ul>
                <p>Your search results are ready in Research Paper Finder.</p>
                <hr>
                <p><small>Research Paper Finder v3.0</small></p>
            </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = recipient_email

        msg.attach(MIMEText(html_body, "html"))

        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)

        log.info(f"Email sent to {recipient_email} for query: {query}")
        return True

    except Exception as e:
        log.error(f"Failed to send email: {e}")
        return False
