import os
import json
from datetime import datetime
from typing import Dict
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class AIService:
    def __init__(self):
        self.api_key = os.getenv("CEREBRAS_API_KEY")
        if not self.api_key:
            raise ValueError("CEREBRAS_API_KEY not found in environment")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.cerebras.ai/v1"
        )
        self.model_name = 'llama3.1-8b'
    
    def extract_schedule_info(self, user_message: str) -> Dict:
        """
        使用 Cerebras Inference 從用戶訊息中提取行程資訊
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
3. 如果用戶【完全沒有】提到任何關於時間或日期的資訊，請絕對不可以自己發明或假設時間，必須將 start_time 設為 null
3. transport_mode 只能是 car/motorcycle/transit/bike/walk 其中之一，若用戶未提及則設為 null (不要預設 car)
4. 如果是與人約會（如"跟Robert吃飯"），type設為"meeting"，attends設為"Robert"
5. 只回應 JSON，不要有其他文字。必須是一個可解析的 JSON 對象。

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
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful JSON extraction assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                timeout=15.0
            )
            
            text = response.choices[0].message.content.strip()
            schedule_data = json.loads(text)
            return schedule_data
        except Exception as e:
            print(f"AI API Error: {e}")
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
            
        if schedule_data.get('type') == 'meeting' and schedule_data.get('attends'):
            msg += f"👥 與會者: {schedule_data['attends']}\n"
            
        if schedule_data.get('is_reminder'):
            msg += f"🔔 已設定提醒\n"
        
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
4. participants (聯絡人，必須以 @ 開頭，以 list 格式) - 例如：["@阿明", "@阿甘", "@小新"]

【非必要資訊】：
無

【今天日期】：{today_str}

【目前已知資訊 (JSON)】：
{json.dumps(current_context, ensure_ascii=False, indent=2)}

【使用者最新輸入】：
"{user_message}"

【任務】：
1. 將「使用者最新輸入」與「目前已知資訊」合併更新
2. 時間處理 (start_time) **[極度重要]**：
   - 如果用戶說「下星期一」、「明天」，請計算實際日期
   - 如果只說時間（早上10點）沒說日期，如果已有日期就用已知日期，否則假設是今天
   - **防呆檢查**：如果對話中【完全沒有】提到任何具體的時間點，【絕對不可以自己發明或假設時間】（也不要使用範例中的時間），你必須將 start_time 設為 null 或空字串，將 "start_time" 加入 missing_fields 清單，is_complete 設為 false，並在 reply 中親切詢問確切時間。
3. 地點處理 (location) **[極度重要]**：
   - 仔細尋找表示地點的關鍵字，如「在」、「去」、「到」後面的名詞
   - 例如：「去台北101吃飯」-> location: "台北101"
   - 例如：「明天台中出差」-> location: "台中"
   - **防呆檢查**：如果用戶提供的地點是連鎖品牌或模糊地名（例如只說「星巴克」、「麥當勞」、「7-11」、「路易莎」），**必須**將該地點視為「不完整」，並強制在 missing_fields 中放入 "location_branch"，且 is_complete 設為 false。
   - 然後在 reply 中親切詢問確切的分店，例如：「請問是哪一家星巴克呢？（例如：內湖店、文湖店）」
   - 如果用戶已經提供了確切分店或地址（例如「星巴克內湖店」、「復興北路的麥當勞」），則視為地點完整。
4. 聯絡人處理 (participants) **[極度重要]**：
   - 如果訊息中完全沒提到任何人，請設定為空列表 `[]`，絕對禁止使用範例中的名字（如阿明、阿甘、小新）！
   - 聯絡人名稱前面**必須要有 @ 符號**（例如：「和 @小明 開會」、「約 @Robert 吃飯」）
   - 如果用戶對話中提到人名但**沒有使用 @ 符號**，請將其視為無效，並設定為空列表 `[]`
5. 如果使用者修改了之前的資訊（例如改時間、改地點），請覆蓋舊資訊
6. 檢查「必要資訊」是否都齊全（包含檢查地點是否夠明確）
7. 如果不齊全：
   - reply 中用親切的語氣詢問缺少的資訊
   - 優先檢查並詢問 participants，提示用戶：「請使用 @ 符號指定聯絡人（例如：和 @小明 開會）」
   - 若是缺少具體分店，請明確詢問分店名稱
   - 一次最多問 1-2 個最重要的缺少項目
8. 如果齊全：
   - reply 請回傳確認訊息，格式如下：
     「已確認行程：
     目的：[title]
     時間：[start_time 的人類易讀格式，例如 2月17日 星期一 早上10:00]
     地點：[location]
     人員：[participants 用逗號分隔]」

請回傳純 JSON 格式，不要用 Markdown 包裝，格式如下：
{{
    "updated_data": {{
        "title": "打棒球",
        "start_time": "2026-02-17 10:00:00",
        "location": "河濱公園",
        "participants": ["@阿明", "@阿甘", "@小新"]
    }},
    "missing_fields": [],  // 缺少的欄位名稱清單，例如 ["location", "start_time"]
    "is_complete": true,   // 是否所有必要資訊都有了
    "reply": "已確認行程：\\n目的：打棒球\\n時間：2月17日 星期一 早上10:00\\n地點：河濱公園\\n人員：@阿明, @阿甘, @小新"
}}
"""

        try:
            # 呼叫 AI API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful JSON extraction assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
                timeout=15.0
            )
            
            clean_text = response.choices[0].message.content.strip()
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
            # JSON 解析失敗的 fallback
            return {
                "updated_data": current_context,
                "missing_fields": [],
                "is_complete": False,
                "reply": "抱歉，我沒有理解清楚。請問您想要安排什麼行程？（至少需要標題、時間和地點）"
            }
        except Exception as e:
            print(f"AI API Error: {e}")
            # 發生錯誤時的 fallback
            return {
                "updated_data": current_context,
                "missing_fields": [],
                "is_complete": False,
                "reply": f"抱歉，系統暫時無法處理。請稍後再試，或直接提供完整資訊（做什麼、什麼時候、在哪裡）。(診斷訊息：{str(e)})"
            }

ai_service = AIService()
