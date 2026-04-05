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
        self.model_name = 'qwen-3-235b-a22b-instruct-2507'
    
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
    
    
    def process_conversation(self, user_message: str, current_context: dict = None,
                             conversation_history: list = None) -> dict:
        """
        處理對話，判斷資訊是否完整，並回傳更新後的狀態與回應。
        支持多輪對話，完整對話歷史作為 messages[] 傳給 AI。
        """
        if current_context is None:
            current_context = {}
        if conversation_history is None:
            conversation_history = []

        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d %A")

        system_prompt = f"""你是行程助理，負責從對話中收集資訊並建立行程。
今天日期：{today_str}

# 必填欄位
- title：做什麼（例：打棒球、與客戶開會）
- start_time：YYYY-MM-DDTHH:MM:SS（必須有時分，不能省略）
- location：具體地點（例：信義威秀、星巴克內湖店）

# 選填欄位
- participants：有提到人名才填，格式 ["@名字"]，沒提到就填 []
- description：簡短備註

# 時間規則
- 只說時間沒說日期（「下午六點」「晚上八點」）→ 直接用今天日期補全，不追問
- 說了日期但沒說幾點（「明天」「星期五」）→ start_time 設 null，追問時間
- 早上=08:xx、中午=12:00、下午=14:xx、傍晚=17:xx、晚上=19:xx（取合理整點）

# 地點規則
- 連鎖品牌未指定分店（「星巴克」「麥當勞」）→ location 設 null，追問哪家分店
- 模糊描述（「附近」「公司旁邊」）→ 追問確切地點

# 完成條件
is_complete = true 的唯一條件：title、start_time、location 三者皆不為 null

# 輸出格式（純 JSON）
{{
  "_thought": "一句話說明目前缺少什麼",
  "updated_data": {{"title": null, "start_time": null, "location": null, "participants": [], "description": null}},
  "missing_fields": [],
  "is_complete": false,
  "reply": "給用戶的回覆"
}}

# 範例

輸入：「明天下午三點在台北車站跟阿明開會」
輸出：
{{
  "_thought": "title=開會、start_time=明天15:00、location=台北車站、participants=阿明，全部齊全",
  "updated_data": {{"title": "與阿明開會", "start_time": "TOMORROW_DATE_T15:00:00", "location": "台北車站", "participants": ["@阿明"], "description": null}},
  "missing_fields": [],
  "is_complete": true,
  "reply": "好的，已記錄明天下午三點在台北車站與阿明開會！"
}}

輸入：「下午兩點去剪頭髮」
輸出：
{{
  "_thought": "title=剪頭髮、start_time=今天14:00，但沒說哪間髮廊",
  "updated_data": {{"title": "剪頭髮", "start_time": "TODAY_DATE_T14:00:00", "location": null, "participants": [], "description": null}},
  "missing_fields": ["location"],
  "is_complete": false,
  "reply": "請問要去哪間髮廊呢？"
}}

輸入：「星期六想去星巴克喝咖啡」
輸出：
{{
  "_thought": "title=喝咖啡、日期可算出但沒說幾點、星巴克未指定分店",
  "updated_data": {{"title": "星巴克喝咖啡", "start_time": null, "location": null, "participants": [], "description": null}},
  "missing_fields": ["start_time", "location"],
  "is_complete": false,
  "reply": "請問星期六幾點去，以及是哪家星巴克分店呢？"
}}"""

        # 當前已知資訊注入為 system 訊息，讓 AI 有可靠的結構化錨點
        context_injection = {
            "role": "system",
            "content": f"【目前已收集的行程資訊】：\n{json.dumps(current_context, ensure_ascii=False, indent=2)}"
        }

        # 只保留最近 10 輪（避免 token 爆炸）
        trimmed_history = conversation_history[-20:] if len(conversation_history) > 20 else conversation_history

        messages = (
            [{"role": "system", "content": system_prompt}]
            + trimmed_history
            + [context_injection,
               {"role": "user", "content": user_message}]
        )

        try:
            # 呼叫 AI API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
                timeout=15.0
            )
            
            clean_text = response.choices[0].message.content.strip()
            # Strip markdown code fences that some models add despite json_object format
            if clean_text.startswith("```"):
                clean_text = clean_text.split("```")[1]
                if clean_text.startswith("json"):
                    clean_text = clean_text[4:]
                clean_text = clean_text.strip()
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
                
            # [新增] 實體防呆校驗層 Python Validation Layer
            updated_data = result["updated_data"]
            start_time = updated_data.get("start_time")
            location = updated_data.get("location")
            title = updated_data.get("title")
            
            # 檢查欄位是否有效 (如果是空字串、null、或者是像 'null' 的字串)
            is_start_time_missing = not start_time or str(start_time).lower() == 'null'
            is_location_missing = not location or str(location).lower() == 'null'
            is_title_missing = not title or str(title).lower() == 'null'
            
            missing_items = []
            
            if is_title_missing:
                missing_items.append("做什麼")
                if "title" not in result["missing_fields"]: result["missing_fields"].append("title")
            
            if is_start_time_missing:
                missing_items.append("幾點幾分")
                if "start_time" not in result["missing_fields"]: result["missing_fields"].append("start_time")
                    
            if is_location_missing:
                missing_items.append("哪裡")
                if "location" not in result["missing_fields"]: result["missing_fields"].append("location")
            
            # 如果發現有漏，但 AI 卻說 is_complete = True，我們強制覆寫阻止它建立行程
            if missing_items and result["is_complete"]:
                result["is_complete"] = False
                items_str = '、'.join(missing_items)
                
                # 如果 AI 的 reply 已經有在問問題了，就保留 AI 的 reply，否則幫它代打
                if "?" not in result["reply"] and "？" not in result["reply"]:
                    result["reply"] = f"好的！不過為了完成行程，還需要知道「{items_str}」喔！請問預計安排在什麼時候、哪裡呢？"

                
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
