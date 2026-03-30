"""
Email notification service for search completion.
Attaches all 3 tiered PDF reports (confirmed, suspicious, rejected).
"""
import os, smtplib, logging
from typing import Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from config import get_settings, PDFS_DIR

settings = get_settings()
log = logging.getLogger("rpf")

SMTP_SERVER = settings.smtp_server
SMTP_PORT = settings.smtp_port
SMTP_USER = settings.smtp_user
SMTP_PASSWORD = settings.smtp_password
SMTP_FROM = settings.smtp_from


def _as_result_dict(result: Any) -> dict:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if isinstance(result, dict):
        return result
    return {}


def _attach_pdf(msg: MIMEMultipart, filepath: str, display_name: str):
    """Attach a PDF file to the email."""
    if not filepath or not os.path.exists(filepath):
        return
    try:
        with open(filepath, "rb") as f:
            part = MIMEBase("application", "pdf")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename=\"{display_name}\"")
            msg.attach(part)
    except Exception as e:
        log.warning(f"Could not attach PDF {filepath}: {e}")


async def send_completion_email(recipient_email: str, query: str, result: Any) -> bool:
    """Send email with search results and attached PDF reports."""
    if not SMTP_SERVER or not SMTP_USER or not SMTP_PASSWORD:
        log.warning("Email not configured. Set SMTP_SERVER, SMTP_USER, SMTP_PASSWORD in .env")
        return False

    try:
        result_data = _as_result_dict(result)
        total_papers = result_data.get("total_found", 0)
        suspicious = result_data.get("total_suspicious", 0)
        rejected = result_data.get("total_rejected", 0)

        pdf_reports = result_data.get("pdf_reports", {})
        confirmed_pdf = pdf_reports.get("confirmed")
        suspicious_pdf = pdf_reports.get("suspicious")
        rejected_pdf = pdf_reports.get("rejected")

        # Count attachments
        attachments = []
        if confirmed_pdf:
            attachments.append(("Confirmed", confirmed_pdf))
        if suspicious_pdf:
            attachments.append(("Suspicious", suspicious_pdf))
        if rejected_pdf:
            attachments.append(("Rejected", rejected_pdf))

        subject = f"Research Papers Found: {query[:80]}"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #0e8046, #0a5c32); padding: 20px 24px; border-radius: 8px 8px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 22px;">Research Paper Finder</h1>
                <p style="color: #b8e6cc; margin: 4px 0 0;">Search Results Ready</p>
            </div>
            <div style="background: #f8f9fa; padding: 24px; border: 1px solid #e0e0e0;">
                <h2 style="color: #1a1a1a; margin-top: 0;">Query: {query}</h2>
                <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                    <tr style="background: #e8f5e9;">
                        <td style="padding: 10px 14px; border: 1px solid #c8e6c9; font-weight: bold; color: #2e7d32;">Confirmed (score >= 70)</td>
                        <td style="padding: 10px 14px; border: 1px solid #c8e6c9; text-align: center; font-size: 20px; font-weight: bold; color: #2e7d32;">{total_papers}</td>
                    </tr>
                    <tr style="background: #fff8e1;">
                        <td style="padding: 10px 14px; border: 1px solid #ffecb3; font-weight: bold; color: #f57f17;">Suspicious (score 40-69)</td>
                        <td style="padding: 10px 14px; border: 1px solid #ffecb3; text-align: center; font-size: 20px; font-weight: bold; color: #f57f17;">{suspicious}</td>
                    </tr>
                    <tr style="background: #fce4ec;">
                        <td style="padding: 10px 14px; border: 1px solid #f8bbd0; font-weight: bold; color: #c62828;">Rejected (score &lt; 40)</td>
                        <td style="padding: 10px 14px; border: 1px solid #f8bbd0; text-align: center; font-size: 20px; font-weight: bold; color: #c62828;">{rejected}</td>
                    </tr>
                </table>
                <p style="color: #555; font-size: 14px;">
                    {"<strong>" + str(len(attachments)) + " PDF report(s) attached</strong> to this email." if attachments else "No PDF reports were generated for this search."}
                </p>
                <ul style="color: #555; font-size: 13px; padding-left: 20px;">
                    {"".join(f'<li>{name} Papers Report ({fname})</li>' for name, fname in attachments)}
                </ul>
            </div>
            <div style="background: #f0f0f0; padding: 12px 24px; border-radius: 0 0 8px 8px; border: 1px solid #e0e0e0; border-top: 0;">
                <p style="margin: 0; color: #888; font-size: 12px; text-align: center;">
                    Developed by Pardeep Beniwal, PhD Research Scholar - Punjab Agricultural University, Ludhiana
                </p>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = recipient_email

        msg.attach(MIMEText(html_body, "html"))

        # Attach all 3 PDF reports
        for display_name, filename in attachments:
            filepath = os.path.join(PDFS_DIR, filename)
            _attach_pdf(msg, filepath, filename)

        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)

        log.info(f"Email with {len(attachments)} PDFs sent to {recipient_email} for query: {query}")
        return True

    except Exception as e:
        log.error(f"Failed to send email to {recipient_email}: {e}", exc_info=True)
        return False
