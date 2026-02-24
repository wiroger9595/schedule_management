import google.genai as genai
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
        # Use the latest stable Gemini 2.5 Flash model
        # Model name must include 'models/' prefix as per google-genai SDK
        self.model_name = 'models/gemini-2.5-flash' 
    
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
- attends: 參與者姓名（字串，如果有多人請用逗號分隔，若無則 null）
- is_reminder: 是否需要提醒（布林值 true/false，如果用戶語氣包含"提醒我"、"別忘了"等意圖則為 true）

**重要規則**：
1. 如果用戶說「明天」、「後天」，請根據今天日期計算實際日期
2. 如果只提到時間（如「下午3點」）但沒說日期，假設是今天
3. transport_mode 只能是 car/motorcycle/transit/bike/walk 其中之一，若用戶未提及則設為 null (不要預設 car)
4. 如果是與人約會（如"跟Robert吃飯"），type設為"meeting"，attends設為"Robert"
5. 只回應 JSON，不要有其他文字

範例回應格式：
{{
  "title": "跟Robert吃飯",
  "description": "聚餐",
  "start_time": "2026-02-09T18:00:00",
  "location": "信義區",
  "transport_mode": "car",
  "type": "meeting",
  "attends": "Robert",
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
        
        msg = f"✅ 已為您建立行程：\\n\\n"
        msg += f"📅 **{schedule_data.get('title', '未命名行程')}**\\n"
        msg += f"⏰ {time_display}\\n"
        
        if schedule_data.get('location'):
            msg += f"📍 {schedule_data['location']}\\n"
        
        if schedule_data.get('description'):
            msg += f"📝 {schedule_data['description']}\\n"
            
        if schedule_data.get('type') == 'meeting' and schedule_data.get('attends'):
            msg += f"👥 與會者: {schedule_data['attends']}\\n"
            
        if schedule_data.get('is_reminder'):
            msg += f"🔔 已設定提醒\\n"
        
        return msg
    
    
    
    def process_conversation(self, user_message: str, current_context: dict = None) -> dict:
        """
        處理對話，判斷資訊是否完整，並回傳更新後的狀態與回應。
        支持多輪對話，當資訊不足時會詢問用戶。
        """
        if current_context is None:
            current_context = {}
        
        # 取得今天日期供 AI 參考
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d %A")
        
        # 定義 Prompt，教 AI 如何當一個秘書
        prompt = f"""你是一個專業的行程管理助理。你的目標是從對話中收集建立行程所需的資訊。

【必要資訊】：
1. title (做什麼事/標題) - 例如：打棒球、開會、吃飯
2. start_time (什麼時候，格式 YYYY-MM-DD HH:MM:SS) - 例如：2026-02-17 10:00:00
3. location (在哪裡) - 例如：河濱公園、信義區、台北101

【非必要資訊】：
4. participants (跟誰，以 list 格式) - 例如：["阿明", "阿甘", "小新"]

【今天日期】：{today_str}

【目前已知資訊 (JSON)】：
{json.dumps(current_context, ensure_ascii=False, indent=2)}

【使用者最新輸入】：
"{user_message}"

【任務】：
1. 將「使用者最新輸入」與「目前已知資訊」合併更新
2. 時間處理：
   - 如果用戶說「下星期一」、「明天」，請計算實際日期
   - 如果只說時間（早上10點）沒說日期，如果已有日期就用已知日期，否則假設是今天
3. 地點處理 (location)：
   - 仔細尋找表示地點的關鍵字，如「在」、「去」、「到」後面的名詞
   - 例如：「去台北101吃飯」-> location: "台北101"
   - 例如：「約在星巴克」-> location: "星巴克"
   - 例如：「明天台中出差」-> location: "台中"
4. 如果使用者修改了之前的資訊（例如改時間、改地點），請覆蓋舊資訊
5. 檢查「必要資訊」是否都齊全
6. 如果不齊全：
   - reply 中用親切的語氣詢問缺少的資訊
   - 一次最多問 1-2 個最重要的缺少項目
   - 例如：「請問哪一天，什麼時間？」或「請問在哪裡？」
7. 如果齊全：
   - reply 請回傳確認訊息，格式如下：
     「已確認行程：
     目的：[title]
     時間：[start_time 的人類易讀格式，例如 2月17日 星期一 早上10:00]
     地點：[location]
     人員：[participants 用逗號分隔，如果沒有就不顯示此行]」

請回傳純 JSON 格式，不要用 Markdown 包裝，格式如下：
{{
    "updated_data": {{
        "title": "打棒球",
        "start_time": "2026-02-17 10:00:00",
        "location": "河濱公園",
        "participants": ["阿明", "阿甘", "小新"]
    }},
    "missing_fields": [],  // 缺少的欄位名稱清單，例如 ["location", "start_time"]
    "is_complete": true,   // 是否所有必要資訊都有了
    "reply": "已確認行程：\\n目的：打棒球\\n時間：2月17日 星期一 早上10:00\\n地點：河濱公園\\n人員：阿明, 阿甘, 小新"
}}
"""

        try:
            # 呼叫 Gemini API
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            # 清理回應中的 ```json 等標記
            clean_text = response.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:-3].strip()
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:-3].strip()
            
            result = json.loads(clean_text)
            
            # 確保回傳格式正確
            if "updated_data" not in result:
                result["updated_data"] = current_context
            if "missing_fields" not in result:
                result["missing_fields"] = []
            if "is_complete" not in result:
                result["is_complete"] = False
            if "reply" not in result:
                result["reply"] = "我不太確定，可以再說一次嗎？"
                
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            print(f"Response text: {response.text if 'response' in locals() else 'No response'}")
            # JSON 解析失敗的 fallback
            return {
                "updated_data": current_context,
                "missing_fields": [],
                "is_complete": False,
                "reply": "抱歉，我沒有理解清楚。請問您想要安排什麼行程？（至少需要標題、時間和地點）"
            }
        except Exception as e:
            print(f"Gemini Error: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"API Response: {e.response}")
            # 發生錯誤時的 fallback
            return {
                "updated_data": current_context,
                "missing_fields": [],
                "is_complete": False,
                "reply": "抱歉，系統暫時無法處理。請稍後再試，或直接提供完整資訊（做什麼、什麼時候、在哪裡）。"
            }

    

gemini_service = GeminiService()
