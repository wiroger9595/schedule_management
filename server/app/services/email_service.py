import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

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

    def send_event_invitation(self, email: str, contact_name: str, schedule: "Any"):
        """
        Send an HTML email invitation for an event to a non-user contact.
        """
        if not self.enabled:
            print(f"============================================")
            print(f"[EmailService] Mock Send Event Invitation to {email} ({contact_name})")
            print(f"[EmailService] Event: {schedule.title}")
            print(f"[EmailService] Time: {schedule.meeting_start_time} - {schedule.meeting_end_time}")
            print(f"[EmailService] Location: {schedule.meeting_location}")
            print(f"[EmailService] Description: {schedule.description}")
            print(f"============================================")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg['From'] = self.smtp_user
            msg['To'] = email
            msg['Subject'] = f"活動邀請: {schedule.title}"

            start_time_str = schedule.meeting_start_time.strftime("%Y-%m-%d %H:%M") if schedule.meeting_start_time else "未定"
            end_time_str = schedule.meeting_end_time.strftime("%Y-%m-%d %H:%M") if schedule.meeting_end_time else "未定"
            location_str = schedule.meeting_location or "未定"
            desc_str = schedule.description or "無"

            html = f"""\\
            <html>
              <head>
                <style>
                  body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f7f6; padding: 20px; }}
                  .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                  h2 {{ color: #2c3e50; text-align: center; }}
                  .details {{ margin-top: 20px; }}
                  .field {{ margin-bottom: 10px; }}
                  .label {{ font-weight: bold; color: #7f8c8d; }}
                  .value {{ color: #34495e; }}
                  .footer {{ margin-top: 30px; text-align: center; color: #bdc3c7; font-size: 12px; }}
                </style>
              </head>
              <body>
                <div class="container">
                  <h2>您收到了一個新的活動邀請！</h2>
                  <p>親愛的 {{contact_name}}，</p>
                  <p>有人邀請您參加一個精彩的活動，以下是活動詳情：</p>
                  
                  <div class="details">
                    <div class="field"><span class="label">活動名稱：</span> <span class="value">{{schedule.title}}</span></div>
                    <div class="field"><span class="label">開始時間：</span> <span class="value">{{start_time_str}}</span></div>
                    <div class="field"><span class="label">結束時間：</span> <span class="value">{{end_time_str}}</span></div>
                    <div class="field"><span class="label">活動地點：</span> <span class="value">{{location_str}}</span></div>
                    <div class="field"><span class="label">活動描述：</span> <span class="value">{{desc_str}}</span></div>
                  </div>
                  
                  <div class="footer">
                    <p>這是一封系統自動發送的郵件，請勿直接回覆。</p>
                  </div>
                </div>
              </body>
            </html>
            """
            
            part2 = MIMEText(html, 'html')
            msg.attach(part2)

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.smtp_user, email, text)
            server.quit()
            return True
        except Exception as e:
            print(f"Failed to send event email: {e}")
            return False

    def send_attend_invitation_to_user(self, email: str, user_name: str, schedule: "Any", attend_id: str, inviter_name: str = "某人"):
        """
        發送 RSVP 邀請給已存在的用戶（含接受/拒絕按鈕）
        """
        base_url = os.getenv("SERVER_BASE_URL", "http://localhost:8000/api")
        accept_url = f"{base_url}/schedules/rsvp?token={attend_id}&action=accept"
        decline_url = f"{base_url}/schedules/rsvp?token={attend_id}&action=decline"

        start_time_str = schedule.meeting_start_time.strftime("%Y-%m-%d %H:%M") if schedule.meeting_start_time else "未定"
        end_time_str = schedule.meeting_end_time.strftime("%Y-%m-%d %H:%M") if schedule.meeting_end_time else "未定"
        location_str = schedule.meeting_location or "未定"

        if not self.enabled:
            print(f"============================================")
            print(f"[EmailService] Mock RSVP Invite to {email} ({user_name})")
            print(f"[EmailService] Event: {schedule.title} | {start_time_str} - {end_time_str}")
            print(f"[EmailService] Accept: {accept_url}")
            print(f"[EmailService] Decline: {decline_url}")
            print(f"============================================")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg['From'] = self.smtp_user
            msg['To'] = email
            msg['Subject'] = f"活動邀請：{schedule.title}"

            html = f"""
            <html>
              <head>
                <style>
                  body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f7f6; padding: 20px; }}
                  .container {{ max-width: 600px; margin: 0 auto; background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                  h2 {{ color: #2c3e50; }}
                  .field {{ margin-bottom: 8px; }}
                  .label {{ font-weight: bold; color: #7f8c8d; }}
                  .buttons {{ margin-top: 30px; text-align: center; }}
                  .btn {{ display: inline-block; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: bold; margin: 0 10px; }}
                  .accept {{ background-color: #27ae60; color: #fff; }}
                  .decline {{ background-color: #e74c3c; color: #fff; }}
                  .footer {{ margin-top: 30px; text-align: center; color: #bdc3c7; font-size: 12px; }}
                </style>
              </head>
              <body>
                <div class="container">
                  <h2>您有一個新的活動邀請！</h2>
                  <p>親愛的 {user_name}，</p>
                  <p><strong>{inviter_name}</strong> 邀請您參加以下活動：</p>
                  <div class="field"><span class="label">活動名稱：</span>{schedule.title}</div>
                  <div class="field"><span class="label">開始時間：</span>{start_time_str}</div>
                  <div class="field"><span class="label">結束時間：</span>{end_time_str}</div>
                  <div class="field"><span class="label">活動地點：</span>{location_str}</div>
                  <div class="buttons">
                    <a href="{accept_url}" class="btn accept">接受邀請</a>
                    <a href="{decline_url}" class="btn decline">拒絕邀請</a>
                  </div>
                  <div class="footer"><p>這是一封系統自動發送的郵件，請勿直接回覆。</p></div>
                </div>
              </body>
            </html>
            """
            msg.attach(MIMEText(html, 'html'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, email, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            print(f"Failed to send RSVP invitation email: {e}")
            return False

    def send_registration_invitation(self, email: str, contact_name: str, schedule: "Any", inviter_name: str = "某人"):
        """
        發送邀請未註冊用戶加入平台的 email
        """
        register_url = os.getenv("REGISTER_URL", "https://schedule-management-mu.vercel.app/register")
        start_time_str = schedule.meeting_start_time.strftime("%Y-%m-%d %H:%M") if schedule.meeting_start_time else "未定"
        end_time_str = schedule.meeting_end_time.strftime("%Y-%m-%d %H:%M") if schedule.meeting_end_time else "未定"
        location_str = schedule.meeting_location or "未定"

        if not self.enabled:
            print(f"============================================")
            print(f"[EmailService] Mock Registration Invite to {email} ({contact_name})")
            print(f"[EmailService] Event: {schedule.title} | {start_time_str} - {end_time_str}")
            print(f"[EmailService] Register URL: {register_url}")
            print(f"============================================")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg['From'] = self.smtp_user
            msg['To'] = email
            msg['Subject'] = f"您被邀請參加活動：{schedule.title}"

            html = f"""
            <html>
              <head>
                <style>
                  body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f7f6; padding: 20px; }}
                  .container {{ max-width: 600px; margin: 0 auto; background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                  h2 {{ color: #2c3e50; }}
                  .field {{ margin-bottom: 8px; }}
                  .label {{ font-weight: bold; color: #7f8c8d; }}
                  .cta {{ margin-top: 30px; text-align: center; }}
                  .btn {{ display: inline-block; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: bold; background-color: #3498db; color: #fff; }}
                  .footer {{ margin-top: 30px; text-align: center; color: #bdc3c7; font-size: 12px; }}
                </style>
              </head>
              <body>
                <div class="container">
                  <h2>您被邀請參加活動！</h2>
                  <p>親愛的 {contact_name}，</p>
                  <p><strong>{inviter_name}</strong> 邀請您參加以下活動：</p>
                  <div class="field"><span class="label">活動名稱：</span>{schedule.title}</div>
                  <div class="field"><span class="label">開始時間：</span>{start_time_str}</div>
                  <div class="field"><span class="label">結束時間：</span>{end_time_str}</div>
                  <div class="field"><span class="label">活動地點：</span>{location_str}</div>
                  <p style="margin-top:20px;">若要接受邀請並查看完整活動詳情，請先註冊成為我們的用戶：</p>
                  <div class="cta">
                    <a href="{register_url}" class="btn">立即註冊</a>
                  </div>
                  <div class="footer"><p>這是一封系統自動發送的郵件，請勿直接回覆。</p></div>
                </div>
              </body>
            </html>
            """
            msg.attach(MIMEText(html, 'html'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, email, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            print(f"Failed to send registration invitation email: {e}")
            return False

    def send_decline_notification(self, creator_email: str, creator_name: str, attendee_name: str, schedule_title: str):
        """
        通知活動建立者有人拒絕了邀請
        """
        if not self.enabled:
            print(f"============================================")
            print(f"[EmailService] Mock Decline Notification to {creator_email}")
            print(f"[EmailService] {attendee_name} 拒絕了「{schedule_title}」的邀請")
            print(f"============================================")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg['From'] = self.smtp_user
            msg['To'] = creator_email
            msg['Subject'] = f"邀請回應：{attendee_name} 無法參加「{schedule_title}」"

            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="max-width:600px; margin:0 auto; background:#fff; padding:30px; border-radius:8px; border:1px solid #eee;">
                  <h2 style="color:#e74c3c;">邀請遭到拒絕</h2>
                  <p>親愛的 {creator_name}，</p>
                  <p><strong>{attendee_name}</strong> 無法參加您的活動「<strong>{schedule_title}</strong>」。</p>
                  <p style="color:#7f8c8d; font-size:12px;">這是一封系統自動發送的郵件，請勿直接回覆。</p>
                </div>
              </body>
            </html>
            """
            msg.attach(MIMEText(html, 'html'))

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, creator_email, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            print(f"Failed to send decline notification email: {e}")
            return False


email_service = EmailService()
