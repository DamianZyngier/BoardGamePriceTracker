import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.config import Config
from src.logger import setup_logger

logger = setup_logger(__name__)

class EmailNotifier:
    def __init__(self):
        self.sender = Config.EMAIL_SENDER
        self.password = Config.EMAIL_APP_PASSWORD
        self.receiver = Config.EMAIL_RECEIVER

    def send(self, subject: str, body: str):
        """Sends an email notification."""
        if not self.sender or not self.password:
            logger.warning("Email sending skipped: EMAIL_SENDER or EMAIL_APP_PASSWORD not set.")
            logger.info(f"\n--- EMAIL ALERT (skipped) ---\nSubject: {subject}\nBody:\n{body}\n---------------------------\n")
            return

        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = self.receiver
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(self.sender, self.password)
                smtp.send_message(msg)
            logger.info(f"Email sent successfully to {self.receiver}!")
        except Exception as e:
            logger.error(f"Error sending email: {e}")
