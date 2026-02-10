from google import genai
import os
import json
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        self.client = genai.Client(api_key=self.api_key)
        # Using a stable model alias or specific version as per new SDK recommendations
        self.model_name = 'gemini-1.5-flash' 
    
    def extract_schedule_info(self, user_message: str) -> Dict:
        """
        使用 Gemini 從用戶訊息中提取行程資訊
        """
        today = datetime.now()
        prompt = f"""
你是一個行程助手。請分析以下用戶訊息，提取行程資訊並以 JSON 格式回應。

用戶訊息："{user_message}"

今天日期：{today.strftime("%Y-%m-%d %A")}

請提取以下資訊（如果訊息中沒有提到，設為 null）：
- title: 行程標題
- description: 行程描述
- start_time: 開始時間（ISO 8601 格式，例如：2026-02-09T15:00:00）
- location: 地點名稱
- transport_mode: 交通方式（car/motorcycle/transit/bike/walk）
- type: 行程類型（"meeting" 表示與他人有約，"personal" 表示個人行程）
- attendees: 參與者姓名（字串，如果有多人請用逗號分隔，若無則 null）
- is_reminder: 是否需要提醒（布林值 true/false，如果用戶語氣包含"提醒我"、"別忘了"等意圖則為 true）

**重要規則**：
1. 如果用戶說「明天」、「後天」，請根據今天日期計算實際日期
2. 如果只提到時間（如「下午3點」）但沒說日期，假設是今天
3. transport_mode 只能是 car/motorcycle/transit/bike/walk 其中之一，若用戶未提及則設為 null (不要預設 car)
4. 如果是與人約會（如"跟Robert吃飯"），type設為"meeting"，attendees設為"Robert"
5. 只回應 JSON，不要有其他文字

範例回應格式：
{{
  "title": "跟Robert吃飯",
  "description": "聚餐",
  "start_time": "2026-02-09T18:00:00",
  "location": "信義區",
  "transport_mode": "car",
  "type": "meeting",
  "attendees": "Robert",
  "is_reminder": false
}}
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            # 提取 JSON（處理可能的 markdown 代碼塊）
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()
            
            schedule_data = json.loads(text)
            return schedule_data
        except Exception as e:
            print(f"Gemini API Error: {e}")
            if hasattr(e, 'response') and e.response:
                 print(f"Response: {e.response.text}")
            raise ValueError("AI 無法理解訊息格式，請提供更清楚的資訊")
    
    def generate_confirmation_message(self, schedule_data: Dict) -> str:
        """生成確認訊息"""
        start_time_str = schedule_data.get('start_time')
        if start_time_str:
             start_time = datetime.fromisoformat(start_time_str)
             time_display = start_time.strftime('%Y-%m-%d %H:%M')
        else:
             time_display = "未指定時間"
        
        msg = f"✅ 已為您建立行程：\n\n"
        msg += f"📅 **{schedule_data.get('title', '未命名行程')}**\n"
        msg += f"⏰ {time_display}\n"
        
        if schedule_data.get('location'):
            msg += f"📍 {schedule_data['location']}\n"
        
        if schedule_data.get('description'):
            msg += f"📝 {schedule_data['description']}\n"
            
        if schedule_data.get('type') == 'meeting' and schedule_data.get('attendees'):
            msg += f"👥 與會者: {schedule_data['attendees']}\n"
            
        if schedule_data.get('is_reminder'):
            msg += f"🔔 已設定提醒\n"
        
        return msg

gemini_service = GeminiService()
