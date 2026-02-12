import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.enabled = self.smtp_user and self.smtp_password

    def send_reset_code(self, email: str, code: str):
        """
        發送密碼重置驗證碼
        如果未設定 SMTP 帳號密碼，則僅印出驗證碼到控制台 (用於開發測試)
        """
        if not self.enabled:
            print(f"============================================")
            print(f"[EmailService] Mock Send to {email}")
            print(f"[EmailService] Reset Code: {code}")
            print(f"============================================")
            return True

        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = email
            msg['Subject'] = "密碼重置驗證碼"

            body = f"您的密碼重置驗證碼是: {code}\n請在 10 分鐘內使用此驗證碼重置您的密碼。"
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.smtp_user, email, text)
            server.quit()
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

email_service = EmailService()
