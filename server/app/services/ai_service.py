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
                             conversation_history: list = None,
                             schedule_list: list = None) -> dict:
        """
        處理對話，支援建立、修改、刪除行程。
        intent: create | edit | delete
        """
        if current_context is None:
            current_context = {}
        if conversation_history is None:
            conversation_history = []

        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d %A")

        # Build schedule list section for AI context
        if schedule_list:
            lines = []
            pre_matched = []
            for s in schedule_list[:20]:
                sid = s.get("schedule_id") or s.get("id", "")
                title = s.get("title", "")
                st = s.get("meeting_start_time") or s.get("start_time", "")
                if st:
                    try:
                        st = datetime.fromisoformat(str(st).replace("Z", "+00:00")).strftime("%m/%d %H:%M")
                    except Exception:
                        pass
                loc = s.get("meeting_location") or s.get("location", "")
                is_match = s.get("_match", False)
                tag = "  ★【關鍵字匹配】" if is_match else "  "
                lines.append(f"{tag}- id={sid} | 標題={title} | 時間={st} | 地點={loc}")
                if is_match:
                    pre_matched.append(f"id={sid}（{title}）")

            schedule_section = "【用戶現有行程清單】\n" + "\n".join(lines)
            if pre_matched:
                schedule_section += f"\n\n⚠️ Python 關鍵字搜尋已找到匹配行程：{', '.join(pre_matched)}\n→ edit/delete 時請直接使用此 id，不需要再搜尋"
        else:
            schedule_section = "【用戶現有行程清單】（未提供）"

        system_prompt = f"""你是行程助理，能夠建立、修改和刪除行程。
現在時間：{today.strftime("%Y-%m-%d %H:%M")}（{today_str}）

{schedule_section}

# 意圖判斷（必須先確定 intent）
根據用戶最新訊息決定 intent：
- 包含「更改/修改/改/調整/延後/提早/換/推遲/改到」→ intent="edit"
- 包含「刪除/刪掉/移除/取消」（後面接行程名稱或「這個/行程/活動」）→ intent="delete"
- current_context 中有 schedule_id 欄位 → intent="edit"（繼續修改流程）
- 其他情況 → intent="create"

# Edit / Delete target_schedule_id 判斷規則
1. **優先**：若行程清單中有標示「★【關鍵字匹配】」或「Python 關鍵字搜尋已找到匹配行程」→ 直接使用那個 id
2. 若無預標記，自行用「關鍵字包含搜尋」比對（關鍵字可在標題任何位置）
3. 確實找不到才設 null，並在 reply 列出現有行程讓用戶確認

# Edit 規則（intent=edit 時）
- target_schedule_id：用上方關鍵字包含搜尋找出最匹配的行程 id
- updated_data：只包含用戶要修改的欄位
- is_complete=true：用戶已明確提供要修改的值
- 若 current_context 有 schedule_id，target_schedule_id 設為該值

# Delete 規則（intent=delete 時）
- target_schedule_id：用上方關鍵字包含搜尋找出最匹配的行程 id
- reply：找到時詢問確認（例：「確定要取消「XXX」（MM/DD HH:MM）嗎？」）
- is_complete=false（等待前端確認按鈕）

# Create 規則（intent=create 時）

## 必填欄位
- title：做什麼（例：打棒球、與客戶開會）
- start_time：YYYY-MM-DDTHH:MM:SS（必須有時分，不能省略）
- location：具體地點（例：信義威秀、星巴克內湖店）

## 選填欄位
- participants：有提到人名才填，格式 ["@名字"]，沒提到就填 []
- description：簡短備註

## 時間規則
- 相對時間（「X小時後」「X分鐘後」「半小時後」）→ 用現在時間直接計算
- 只說時間沒說日期（「下午六點」「晚上八點」）→ 直接用今天日期補全，不追問
- 說了日期但沒說幾點（「明天」「星期五」）→ start_time 設 null，追問時間
- 早上=08:xx、中午=12:00、下午=14:xx、傍晚=17:xx、晚上=19:xx（取合理整點）

## 地點規則
- 連鎖品牌未指定分店（「星巴克」「麥當勞」）→ location 設 null，追問哪家分店
- 模糊描述（「附近」「公司旁邊」）→ 追問確切地點

## Create is_complete 條件
title、start_time、location 三者皆不為 null

# 輸出格式（純 JSON）
{{
  "_thought": "一句話說明意圖和狀態",
  "intent": "create",
  "target_schedule_id": null,
  "updated_data": {{"title": null, "start_time": null, "location": null, "participants": [], "description": null}},
  "missing_fields": [],
  "is_complete": false,
  "reply": "給用戶的回覆"
}}

# 範例

輸入：「明天下午三點在台北車站跟阿明開會」
輸出：
{{
  "_thought": "title/time/location 齊全，intent=create",
  "intent": "create",
  "target_schedule_id": null,
  "updated_data": {{"title": "與阿明開會", "start_time": "TOMORROW_DATE_T15:00:00", "location": "台北車站", "participants": ["@阿明"], "description": null}},
  "missing_fields": [],
  "is_complete": true,
  "reply": "好的，已記錄明天下午三點在台北車站與阿明開會！"
}}

輸入：「把與文哥見面的時間改到下午五點」（行程清單有 id=abc, 標題=與文哥見面）
輸出：
{{
  "_thought": "intent=edit，目標=與文哥見面(id=abc)，修改 start_time",
  "intent": "edit",
  "target_schedule_id": "abc",
  "updated_data": {{"start_time": "SAME_DATE_T17:00:00"}},
  "missing_fields": [],
  "is_complete": true,
  "reply": "好的，我來幫您把與文哥的見面改到下午五點！"
}}

輸入：「取消爬大屯山行程」（行程清單有 id=abc, 標題=與阿糖、阿文、po-a爬大屯山）
輸出：
{{
  "_thought": "intent=delete，用戶說「爬大屯山」，搜尋標題是否包含「爬大屯山」→「與阿糖、阿文、po-a爬大屯山」包含，匹配 id=abc",
  "intent": "delete",
  "target_schedule_id": "abc",
  "updated_data": {{}},
  "missing_fields": [],
  "is_complete": false,
  "reply": "確定要取消「與阿糖、阿文、po-a爬大屯山」嗎？"
}}

輸入：「把文哥見面改到下午五點」（行程清單有 id=xyz, 標題=與文哥見面）
輸出：
{{
  "_thought": "intent=edit，用戶說「文哥見面」，搜尋標題是否包含「文哥」→「與文哥見面」包含，匹配 id=xyz",
  "intent": "edit",
  "target_schedule_id": "xyz",
  "updated_data": {{"start_time": "SAME_DATE_T17:00:00"}},
  "missing_fields": [],
  "is_complete": true,
  "reply": "好的，我來幫您把與文哥的見面改到下午五點！"
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
            if "intent" not in result:
                result["intent"] = "create"
            if "target_schedule_id" not in result:
                result["target_schedule_id"] = None
                
            # 實體防呆校驗層 — 只在 create intent 時強制檢查必填欄位
            intent = result.get("intent", "create")
            if intent == "create":
                updated_data = result["updated_data"]
                start_time = updated_data.get("start_time")
                location = updated_data.get("location")
                title = updated_data.get("title")

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

                if missing_items and result["is_complete"]:
                    result["is_complete"] = False
                    items_str = '、'.join(missing_items)
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
            import traceback
            print(f"AI API Error: {e}")
            traceback.print_exc()
            return {
                "updated_data": current_context,
                "missing_fields": [],
                "is_complete": False,
                "reply": "抱歉，系統暫時無法處理，請稍後再試。"
            }

ai_service = AIService()
