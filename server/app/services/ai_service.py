import os
import json
from datetime import datetime
from typing import Dict, Optional, Literal
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()


# ── Pydantic schema for instructor fallback ───────────────────────────────────
class ScheduleAction(BaseModel):
    intent: Literal["create", "edit", "delete"] = "create"
    target_schedule_id: Optional[str] = None
    updated_data: dict = Field(default_factory=dict)
    is_complete: bool = False
    reply: str = ""


class AIService:
    def __init__(self):
        # ── Provider cascade: rate-limit / auth error 時依序 fallback ──────────
        # 順序：Cerebras → Gemini → OpenRouter → Groq 70B → Together → Cloudflare → Groq 8B
        cerebras_key   = os.getenv("CEREBRAS_API_KEY")
        gemini_key     = os.getenv("GEMINI_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        groq_key       = os.getenv("GROQ_API_KEY")
        together_key   = os.getenv("TOGETHER_API_KEY")
        cf_account     = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        cf_token       = os.getenv("CLOUDFLARE_API_TOKEN")

        self._providers: list[tuple] = []  # (client, model_name, label)

        if cerebras_key:
            self._providers.append((
                OpenAI(api_key=cerebras_key, base_url="https://api.cerebras.ai/v1"),
                "qwen-3-235b-a22b-instruct-2507", "Cerebras/qwen-3-235b",
            ))
        if gemini_key:
            self._providers.append((
                OpenAI(api_key=gemini_key,
                       base_url="https://generativelanguage.googleapis.com/v1beta/openai/"),
                "gemini-2.0-flash", "Gemini/gemini-2.0-flash",
            ))
        if openrouter_key:
            _or_client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1",
                                default_headers={"HTTP-Referer": "https://schedule-app",
                                                 "X-Title": "ScheduleAI"})
            self._providers.append((_or_client, "meta-llama/llama-3.3-70b-instruct:free",
                                    "OpenRouter/llama-3.3-70b:free"))
        if groq_key:
            _groq = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            self._providers.append((_groq, "llama-3.3-70b-versatile", "Groq/llama-3.3-70b"))
        if together_key:
            self._providers.append((
                OpenAI(api_key=together_key, base_url="https://api.together.xyz/v1"),
                "meta-llama/Llama-3.3-70B-Instruct-Turbo", "Together/llama-3.3-70b",
            ))
        if cf_account and cf_token:
            self._providers.append((
                OpenAI(api_key=cf_token,
                       base_url=f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/v1"),
                "@cf/meta/llama-3.3-70b-instruct-fp8-fast", "Cloudflare/llama-3.3-70b",
            ))
        if groq_key:
            _groq = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            self._providers.append((_groq, "llama-3.1-8b-instant", "Groq/llama-3.1-8b"))

        if not self._providers:
            raise ValueError("需要設定至少一個 AI API Key")

        # Default client/model = first available provider
        self.client, self.model_name, _label = self._providers[0]
        self.api_key = self.client.api_key
        labels = " → ".join(p[2] for p in self._providers)
        print(f"[AIService] Cascade ({len(self._providers)}): {labels}")

        # instructor client（JSON mode，自動重試 + Pydantic 驗證）
        try:
            import instructor
            self.instructor_client = instructor.from_openai(
                self.client, mode=instructor.Mode.JSON
            )
        except ImportError:
            self.instructor_client = None
    
    def extract_schedule_info(self, user_message: str) -> Dict:
        """
        使用 Cerebras Inference 從用戶訊息中提取行程資訊
        """
        from datetime import timezone, timedelta
        TAIPEI_TZ = timezone(timedelta(hours=8))
        today = datetime.now(tz=TAIPEI_TZ)
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
    
    
    # ── Tool definitions ─────────────────────────────────────────────────────
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "ask_user",
                "description": "缺少必要資訊，或用戶說要改但沒說改成什麼時使用",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "問用戶的問題"},
                        "partial_data": {
                            "type": "object",
                            "description": "目前已知的欄位（可為空 {}）。若是修改流程的追問，必須帶入 schedule_id",
                            "properties": {
                                "schedule_id": {"type": "string", "description": "修改流程中目標行程的 id，確保下一輪回覆能繼續修改同一筆行程"},
                                "title": {"type": "string"},
                                "start_time": {"type": "string"},
                                "location": {"type": "string"},
                                "description": {"type": "string"},
                                "participants": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    },
                    "required": ["question"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_schedule",
                "description": "建立新行程。title/start_time/end_time/location/participants 都齊全才呼叫",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "start_time": {"type": "string", "description": "ISO 8601，如 2026-04-16T15:00:00"},
                        "end_time": {"type": "string", "description": "ISO 8601，預設 start_time + 2小時"},
                        "location": {"type": "string"},
                        "description": {"type": "string"},
                        "participants": {"type": "array", "items": {"type": "string"}},
                        "reply": {"type": "string", "description": "給用戶的確認訊息"}
                    },
                    "required": ["title", "start_time", "end_time", "location", "reply"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_schedule",
                "description": (
                    "修改現有行程。必須先從行程清單找到目標行程的 id，且用戶已明確說明要改成什麼值。"
                    "若更改地點且舊 title 含有舊地點名稱，一併更新 title（移除地點，只保留活動與對象）。"
                    "⚠️ 必須至少帶入一個修改欄位（title/start_time/location/description/participants），"
                    "若用戶尚未提供新值則改用 ask_user 追問，不可呼叫空的 update_schedule。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "schedule_id": {"type": "string"},
                        "title": {"type": "string"},
                        "start_time": {"type": "string", "description": "ISO 8601"},
                        "location": {"type": "string"},
                        "description": {"type": "string"},
                        "participants": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "新增參與者（加入到現有名單，格式 @名稱）"
                        },
                        "remove_participants": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "移除參與者（從現有名單刪除，格式 @名稱）"
                        },
                        "reply": {"type": "string", "description": "給用戶的確認訊息"}
                    },
                    "required": ["schedule_id", "reply"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_schedule",
                "description": "準備刪除行程（系統會向用戶確認，尚未真正刪除）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "schedule_id": {"type": "string"},
                        "schedule_title": {"type": "string", "description": "行程標題，用於確認訊息"}
                    },
                    "required": ["schedule_id", "schedule_title"]
                }
            }
        }
    ]

    def process_conversation(self, user_message: str, current_context: dict = None,
                             conversation_history: list = None,
                             schedule_list: list = None,
                             memory_snippets: list = None,
                             contact_hints: list = None) -> dict:
        """
        使用 Tool Use（Function Calling）處理對話，支援建立、修改、刪除行程。
        回傳格式與舊版相同，LangGraph / chat endpoint 無需改動。
        """
        if current_context is None:
            current_context = {}
        if conversation_history is None:
            conversation_history = []

        from datetime import timezone, timedelta
        TAIPEI_TZ = timezone(timedelta(hours=8))
        today = datetime.now(tz=TAIPEI_TZ)
        today_str = today.strftime("%Y-%m-%d %A")

        # ── 行程清單：保留 Python 關鍵字預標記機制 ───────────────────────────
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
                tag = "  ★" if is_match else "  "
                lines.append(f"{tag}id={sid} | {title} | {st} | {loc}")
                if is_match:
                    pre_matched.append(f"id={sid}（{title}）")
            schedule_section = "【行程清單】\n" + "\n".join(lines)
            if pre_matched:
                schedule_section += f"\n⚠️ 關鍵字匹配：{', '.join(pre_matched)} → edit/delete 直接用此 id"
        else:
            schedule_section = "【行程清單】（未提供）"

        # ── 用戶記憶 & 聯絡人提示 ──────────────────────────────────────────────
        # 從 current_context 或直接參數讀取（schedules.py 透過 current_data 傳入）
        _mem = memory_snippets or (current_context or {}).get("_memory_snippets") or []
        _contacts = contact_hints or (current_context or {}).get("_contact_hints") or []

        memory_section = ""
        if _mem:
            lines = [f"  • {m['content']}" for m in _mem[:4]]
            memory_section = "\n## 用戶個人偏好記憶（根據過去行程學習）\n" + "\n".join(lines)

        contact_section = ""
        if _contacts:
            lines = [f"  • @{c['nick_name']}（相似度 {c['similarity']}）{' — ' + c['comment'] if c.get('comment') else ''}"
                     for c in _contacts[:5]]
            contact_section = "\n## 語意匹配到的聯絡人\n" + "\n".join(lines) + "\n（以上是聯絡人名單，用於識別句子中的人名）"

        # 同名聯絡人警告
        _dup_keys = [k for k in (current_context or {}) if k.startswith("_dup_")]
        if _dup_keys:
            dup_lines = []
            for _dk in _dup_keys:
                _dname = _dk[5:]  # 去掉 _dup_ 前綴
                _dentries = current_context[_dk]
                _desc = "、".join(
                    f"{'備註:' + e['comment'] if e['comment'] else ''}{'末4碼:' + e['phone'] if e['phone'] else '（無備註）'}"
                    for e in _dentries
                )
                dup_lines.append(f"  ⚠️ @{_dname} 有 {len(_dentries)} 位同名聯絡人：{_desc}")
            contact_section += "\n## ⚠️ 同名聯絡人（必須先問清楚是哪一位）\n" + "\n".join(dup_lines) + \
                               "\n→ 遇到同名聯絡人時，呼叫 ask_user 讓用戶說明是哪一位（用備註或電話末4碼區分）"

        system_prompt = f"""你是行程助理，透過呼叫工具來建立/修改/刪除行程。請用與用戶相同的語言回覆（中文說中文、英文說英文）。



現在時間（台灣）：{today.strftime("%Y-%m-%d %H:%M")}（{today_str}）

{schedule_section}{memory_section}{contact_section}

## 句子解析規則（名字 / 時間 / 地點順序不固定）
- 句子中的人名、時間、地點**順序可能任意排列**，不可依位置假設詞性
- 人名判斷依據：出現在【語意匹配到的聯絡人】清單中，或在 跟/和/找/與/邀請/請/叫 之後
- 時間判斷依據：含有日期關鍵字（明天/後天/禮拜X/下週/X月X日）或時間詞（X點/早上/下午/晚上）
- 地點判斷依據：含有地標/店名/區域，或在 在/去/到 之後
- 範例：「星期五晚上小明台北101跟我吃飯」→ 時間=星期五晚上，人名=@小明，地點=台北101
- 範例：「跟文哥明天下午三點在星巴克開會」→ 人名=@文哥，時間=明天下午三點，地點=星巴克
- 若無法確定某詞是人名還是地點 → 優先查聯絡人清單，若在清單中就當人名

## 同名聯絡人處理規則
- 若同名聯絡人警告出現在上方，**必須先** ask_user 詢問是哪一位，不可假設
- 詢問方式：列出區分資訊（備註/電話末4碼）讓用戶選擇
- 例：「您說的 @小明 是哪一位？A（備註：同事）或 B（電話末4碼：1234）？」

## Title 規則（重要）
- title 只描述「做什麼 / 和誰」，**不包含地點與時間**
- 正確：「與jjlin談生意」「打棒球」「客戶開會」
- 錯誤：「跟jjlin去一蘭拉麵談生意」（含地點）「明天下午打棒球」（含時間）
- 建立或修改時，若用戶說的 title 含有地點/時間，請自動去除

## 更改地點時的 title 連動規則
- 若用戶更改地點，且現有 title 含有舊地點名稱 → update_schedule 同時帶入新 title（去除地點後的版本）
- 範例：title="跟jjlin去一蘭拉麵談生意"，地點改成星巴克 → 新 title="與jjlin談生意"

## 工具選擇規則
- 建立新行程 → create_schedule（**必須齊全**：title + start_time + end_time + location + participants，缺任何一項都必須先用 ask_user 詢問）
  - participants 不可為空陣列，至少要有一位參與者才能呼叫 create_schedule
  - end_time：用戶有說結束時間就用，沒說則預設 start_time + 2小時
- 修改行程 → update_schedule（從清單找到 schedule_id，只帶入**用戶說要改的欄位**即可，其他欄位不需要）
  - 只改時間 → update_schedule(schedule_id, start_time) ✅ 不需要 location
  - 只改地點 → update_schedule(schedule_id, location) ✅ 不需要 start_time
  - 新增參與者 → update_schedule(schedule_id, participants=["@名稱"]) ✅（加入現有名單）
  - 移除參與者 → update_schedule(schedule_id, remove_participants=["@名稱"]) ✅（從名單移除）
  - 換人（替換）→ update_schedule(schedule_id, participants=["@新人"], remove_participants=["@舊人"]) ✅
  - 用戶說「新增/換一位」但沒說名字 → ask_user(question="請問要新增哪位參與者？", partial_data={{"schedule_id":"..."}}) ✅
- 刪除行程 → delete_schedule（從清單找到 schedule_id）
- 用戶說「改 XX」但沒說改成什麼值，或還缺修改的目標行程 → ask_user
  ⚠️ ask_user 追問修改資訊時，partial_data **必須**帶入 schedule_id

## 行程搜尋驗證規則（嚴格遵守）
- update_schedule / delete_schedule 的 schedule_id **必須來自行程清單中的現有 id**，不可自行編造
- 呼叫 update_schedule 前，必須確認清單中有**符合用戶描述的人名或關鍵字**的行程
  - 用戶說「更改與文哥的行程」→ 清單中必須有 title 含「文哥」或參與者有「文哥」的行程
  - 若清單中**找不到**符合描述的行程 → ask_user(question="找不到與文哥相關的行程，請確認行程名稱是否正確？")
- **禁止**選擇描述不符的行程來更新（例如：用戶說「文哥」，不可去更新「Robert」的行程）

## 時間規則（建立新行程）
- 相對時間（X小時後/半小時後）→ 用現在時間計算
- 只說時間沒說日期（下午六點）→ 今天日期補全
- 說日期沒說時間（明天/星期五）→ ask_user 追問幾點，**並把已知日期存入 partial_data.start_time（例：2026-04-25T00:00:00），不可遺失日期**
- 時段預設中間值：早上=09:00 中午=12:00 下午=14:00 傍晚=17:00 晚上=19:00 深夜/凌晨=22:00
- end_time 預設 = start_time + 2小時（用戶有說結束時間則以用戶為準）

## 建立行程的追問流程（⚠️ 極重要）
- Context 有 title 但**沒有 _pending_edit_schedule_id** → 正在建立新行程中
- 此時用戶的任何回覆都是補充新行程資訊，**絕對不可呼叫 update_schedule** ❌
- 用戶回覆時間（如「晚上10點」）→ 取 context.start_time 中已儲存的日期，替換時間部分，組成完整 ISO datetime
- 不可重新詢問已知的日期 ❌

## 參與者命名規則（⚠️ 必須遵守）
- 所有參與者名稱**一律加上 @ 前綴**，一個人一個 @
- 正確：participants=["@小明", "@文哥", "@Robert"] ✅
- 錯誤：participants=["小明", "文哥"] ❌（沒有 @）
- 錯誤：participants=["@小明文哥"] ❌（兩人合在一起）
- 回覆訊息中提到參與者時也要用 @名稱 格式，例如「已為您建立與 @小明 的行程」

## ask_user partial_data 完整性規則（⚠️ 極重要）
- ask_user 的 partial_data **必須包含目前已知的所有欄位**（title、start_time、location、participants 等）
- **禁止只帶部分欄位** — 遺漏已知資訊等於讓用戶白說，下一輪又要重問 ❌
- 每次 ask_user 就是在「保存進度」，已知的全部存下來，只問缺少的那個
- 範例：用戶說「下禮拜五在信義星巴克吃飯」（有日期+地點，缺時間）
  → ask_user(question="請問幾點開始？", partial_data={{"title":"吃飯", "start_time":"<下禮拜五>T00:00:00", "location":"信義星巴克"}}) ✅
  → ask_user(question="請問幾點開始？", partial_data={{"title":"吃飯"}}) ❌ 漏掉 start_time 和 location
- 範例：context 已有 start_time + location，用戶補充了時間
  → ask_user(question="請問地點在哪？", partial_data={{"title":"...", "start_time":"<完整時間>", "participants":[...]}}) ✅ 保留所有已知欄位

## 時間規則（修改現有行程）
- 用戶只說時間（改成9點 / 改成下午3點）→ 必須從行程清單取得該行程的**原始日期**，只替換時間部分，組合成完整 ISO datetime。**禁止用今天日期覆蓋原始日期**
- 範例：行程原本是 2027-04-09T15:00，用戶說「改成9點」→ start_time="2027-04-09T09:00:00"
- 用戶說「改成明年4月」→ 保留原本時間，只替換日期部分

## update_schedule 完整性規則
- 用戶在同一條訊息裡提到多項修改（例如「時間改成9點，地點改到星巴克」），update_schedule **必須同時帶入所有修改欄位**，不可只改其中一項

## update_schedule 欄位純淨規則（⚠️ 最重要）
- update_schedule **只帶入用戶這次訊息裡明確說要改的欄位**
- Context 裡已有的欄位（例如上一輪的 location）**絕對不可複製**到 update_schedule
- 用戶說「改後天十一點」→ update_schedule(schedule_id, start_time) **只帶 start_time，不帶 location** ✅
- 用戶說「改後天十一點」→ update_schedule(schedule_id, start_time, location="...舊地點...") ❌ 禁止

## 地點規則
- 連鎖品牌未指定分店（星巴克/麥當勞）→ ask_user 追問哪家分店

## 典型對話範例（請嚴格遵守）

### 建立行程
用戶：「明天下午三點跟Robert吃飯，地點在信義區」
→ create_schedule(title="與Robert吃飯", start_time="<明天日期>T15:00:00", location="信義區") ✅
→ title 不可寫「跟Robert在信義區吃飯」（含地點）❌

用戶：「安排週五打球」
→ ask_user(question="請問幾點開始？", partial_data={{"title":"打球"}}) ✅
→ 不可自己假設時間建立行程 ❌

### 修改時間（只改時間，地點不動）⭐ 最重要規則
行程清單：★ id=abc | 與文哥見面 | 2026-04-20 10:00 | 台北
用戶：「我要更改與文哥見面的時間」
→ ask_user(question="請問要改成什麼時間？", partial_data={{"schedule_id":"abc"}}) ✅
   ↑ partial_data 必須帶 schedule_id，不可省略
→ ask_user 不可要求用戶提供地點（用戶說只改時間）❌

用戶回覆「明天下午三點」（context 有 _pending_edit_schedule_id="abc"）
→ update_schedule(schedule_id="abc", start_time="2026-04-17T15:00:00") ✅
   ↑ 只帶 start_time，不帶 location（地點沒有要改）
→ 不可再問地點 ❌
→ 不可呼叫 create_schedule ❌

### Context 有舊地點，用戶只改時間 ⭐
context: {{location: "建國高架旁籃球場", _pending_edit_schedule_id: "abc"}}
用戶：「改後天十一點」
→ update_schedule(schedule_id="abc", start_time="<後天>T11:00:00") ✅
   ↑ location 在 context 裡但用戶沒說要改 → **不帶 location**
→ update_schedule(schedule_id="abc", start_time=..., location="建國高架旁籃球場") ❌ 禁止複製舊值

### 修改時間（只說時間 → 保留原始日期）
行程清單：★ id=abc | 打球 | 2027-05-10 15:00 | 新竹體育館
用戶：「改成早上九點」
→ update_schedule(schedule_id="abc", start_time="2027-05-10T09:00:00") ✅
→ 不可用今天 {today.strftime("%Y-%m-%d")} 作為日期 ❌

### 多欄位同時修改
行程清單：★ id=abc | 與jjlin談生意 | 2027-05-10 15:00 | 一蘭拉麵
用戶：「改成下午五點，地點換到星巴克竹北店」
→ update_schedule(schedule_id="abc", start_time="2027-05-10T17:00:00", location="星巴克竹北店") ✅
→ 不可只改其中一項 ❌

### 地點更改連動 title
行程清單：★ id=abc | 跟jjlin去一蘭拉麵談生意 | ...
用戶：「地點改到星巴克」
→ ask_user(question="請問要去哪家星巴克分店？", partial_data={{"schedule_id":"abc"}}) ✅（連鎖品牌先追問）
用戶回覆：「新竹關埔門市」
→ update_schedule(schedule_id="abc", location="星巴克新竹關埔門市", title="與jjlin談生意") ✅
→ title 去除舊地點，不可保留「一蘭拉麵」❌

### 建立行程：多輪追問，逐步收集資訊 ⭐ 最常見錯誤
用戶：「下禮拜五跟小小哈找明明吃飯」（有日期+參與者，缺時間+地點）
→ ask_user(question="請問幾點開始？", partial_data={{"title":"與小小哈明明吃飯", "start_time":"<下禮拜五>T00:00:00", "participants":["@小小哈","@明明"]}}) ✅
   ↑ 日期+participants 全部存進 partial_data，只問時間

下一輪 context: {{"title":"與小小哈明明吃飯", "start_time":"2026-04-24T00:00:00", "participants":["@小小哈","@明明"]}}（無 _pending_edit_schedule_id）
用戶：「晚上10點」（補充時間）
→ CREATE 流程（context 有 title 無 _pending_edit_schedule_id），取日期 2026-04-24 + 晚上10點 → T22:00:00
→ ask_user(question="請問用餐地點在哪裡？", partial_data={{"title":"與小小哈明明吃飯", "start_time":"2026-04-24T22:00:00", "participants":["@小小哈","@明明"]}}) ✅
   ↑ 保留所有已知欄位（title + start_time + participants），只問地點
→ 絕對不可呼叫 update_schedule ❌
→ 不可再問「哪個日期」或「哪些參與者」❌

用戶：「信義區」（補充地點）
→ create_schedule(title="與小小哈明明吃飯", start_time="2026-04-24T22:00:00", location="信義區", participants=["@小小哈","@明明"]) ✅

### 追問流程：用戶的下一句是補充資訊（修改）
【目前已知資訊】中有 _pending_edit_schedule_id="abc"，用戶回覆「新竹關埔門市」
→ update_schedule(schedule_id="abc", location="新竹關埔門市") ✅
→ 不可呼叫 create_schedule ❌

### 換人（替換參與者）
行程清單：★ id=abc | 與小明吃飯 | 2026-04-20 19:00
用戶：「把小明換成小美」
→ update_schedule(schedule_id="abc", participants=["@小美"], remove_participants=["@小明"], reply="已將 @小明 換成 @小美") ✅
→ 不可只加 @小美 而不移除 @小明 ❌

### 修改地點和時間（兩個都缺）→ 一次問清楚
用戶：「更新談生意的地點和時間」
→ ask_user(question="請問要改成哪個新時間，以及新地點在哪裡？", partial_data={{"schedule_id":"abc"}}) ✅
→ 不可只問時間，分兩次追問 ❌

### 用戶重複說原始需求（沒有回答追問）
context 有 _pending_edit_schedule_id="abc"，用戶說「更新談生意的地點和時間」
→ 識別為用戶沒有提供新值，再次詢問：ask_user(question="請直接告訴我新的時間和地點？", partial_data={{"schedule_id":"abc"}}) ✅
→ 不可呼叫 create_schedule 或空的 update_schedule ❌"""

        # 過濾內部 key（_pre_intent 等）再注入，但保留 hint
        pre_intent = current_context.pop("_pre_intent", None) if current_context else None
        pending_edit_id = current_context.get("_pending_edit_schedule_id") if current_context else None
        clean_context = {k: v for k, v in current_context.items() if not k.startswith("_")}

        hint_note = f"\n⚡ 語意路由預判 intent={pre_intent}（請優先採用，除非明顯不符）" if pre_intent else ""
        pending_note = (f"\n🔧 正在修改行程 id={pending_edit_id}，"
                        f"用戶的回覆是補充修改內容，請直接呼叫 update_schedule(schedule_id='{pending_edit_id}', ...)"
                        if pending_edit_id else "")
        context_note = (
            f"【目前已知資訊】：{json.dumps(clean_context, ensure_ascii=False)}{hint_note}{pending_note}"
            if clean_context or pre_intent or pending_edit_id else ""
        )
        trimmed_history = conversation_history[-20:]

        messages = (
            [{"role": "system", "content": system_prompt}]
            + trimmed_history
            + ([{"role": "system", "content": context_note}] if context_note else [])
            + [{"role": "user", "content": user_message}]
        )

        import time as _time

        def _should_skip_provider(err: Exception) -> bool:
            """Return True if we should abandon this provider and try the next one."""
            s = str(err)
            # Rate / capacity limits
            if any(k in s for k in ("429", "queue_exceeded", "too_many_requests",
                                    "high traffic", "rate_limit", "rate limit",
                                    "overloaded", "503", "529")):
                return True
            # Auth / key errors — key invalid or missing for this provider
            if any(k in s for k in ("401", "API_KEY_INVALID", "API Key not found",
                                    "invalid_api_key", "invalid api key",
                                    "Permission denied", "PERMISSION_DENIED",
                                    "Unauthorized", "authentication")):
                return True
            return False

        def _is_tool_unsupported(err: Exception) -> bool:
            s = str(err).lower()
            return any(k in s for k in ("tool", "function_call", "tool_choice"))

        last_exception = None
        response = None

        for _p_idx, (_cli, _model, _label) in enumerate(self._providers):
            use_tool_calling = True
            for _attempt in range(2):  # max 2 attempts per provider
                try:
                    if _attempt > 0:
                        _time.sleep(1)
                    if use_tool_calling:
                        response = _cli.chat.completions.create(
                            model=_model,
                            messages=messages,
                            tools=self.TOOLS,
                            tool_choice="required",
                            temperature=0.1,
                            timeout=20.0,
                        )
                    else:
                        response = _cli.chat.completions.create(
                            model=_model,
                            messages=messages + [{
                                "role": "system",
                                "content": (
                                    '請以 JSON 回應，格式：{"intent":"create|edit|delete",'
                                    '"target_schedule_id":null,"updated_data":{},'
                                    '"is_complete":false,"reply":"回覆內容"}'
                                )
                            }],
                            temperature=0.1,
                            response_format={"type": "json_object"},
                            timeout=20.0,
                        )
                    print(f"[AIService] Using {_label}")
                    break  # success
                except Exception as _e:
                    last_exception = _e
                    if _should_skip_provider(_e):
                        print(f"[AIService] {_label} skipped ({type(_e).__name__}): {str(_e)[:120]}")
                        break  # move to next provider
                    if use_tool_calling and _is_tool_unsupported(_e):
                        print(f"[AIService] {_label} no tool support → JSON mode")
                        use_tool_calling = False
                        continue
                    # Unknown error — skip provider rather than crash everything
                    print(f"[AIService] {_label} unexpected error, skipping: {str(_e)[:120]}")
                    break
            else:
                continue  # inner exhausted without break (shouldn't happen) → next provider
            if response is not None:
                break  # got response — exit provider loop
        else:
            # All providers exhausted
            if last_exception and _should_skip_provider(last_exception):
                raise RuntimeError("AI_RATE_LIMITED") from last_exception
            raise last_exception

        try:
            msg = response.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None)

            # ── JSON fallback mode (tool calling not supported) ──────────────
            if not use_tool_calling or not tool_calls:
                # 優先用 instructor（自動重試 + Pydantic 驗證）
                if self.instructor_client:
                    try:
                        action: ScheduleAction = self.instructor_client.chat.completions.create(
                            model=self.model_name,
                            response_model=ScheduleAction,
                            messages=messages,
                            max_retries=2,
                        )
                        return {
                            "intent": action.intent,
                            "target_schedule_id": action.target_schedule_id,
                            "updated_data": action.updated_data or current_context,
                            "missing_fields": [],
                            "is_complete": action.is_complete,
                            "reply": action.reply,
                        }
                    except Exception as _inst_err:
                        print(f"[instructor] fallback failed: {_inst_err}")

                # 最終 fallback：手動解析 content
                content = getattr(msg, "content", "") or ""
                if content:
                    try:
                        if content.startswith("```"):
                            content = content.split("```")[1]
                            if content.startswith("json"):
                                content = content[4:]
                        result = json.loads(content.strip())
                        result.setdefault("intent", "create")
                        result.setdefault("target_schedule_id", None)
                        result.setdefault("updated_data", current_context)
                        result.setdefault("missing_fields", [])
                        result.setdefault("is_complete", False)
                        result.setdefault("reply", "好的，請繼續。")
                        return result
                    except Exception:
                        pass
                return {
                    "intent": "create", "target_schedule_id": None,
                    "updated_data": current_context, "missing_fields": [],
                    "is_complete": False, "reply": content or "好的，請問還有什麼需要調整嗎？",
                }

            tc = tool_calls[0]
            fn_name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except (json.JSONDecodeError, Exception) as _parse_err:
                print(f"[AI Tool] malformed arguments for {fn_name}: {tc.function.arguments!r} — {_parse_err}")
                return {
                    "intent": "create", "target_schedule_id": None,
                    "updated_data": current_context, "missing_fields": [],
                    "is_complete": False, "reply": "抱歉，我沒有理解清楚，可以再說一次嗎？",
                }
            print(f"[AI Tool] {fn_name}({args})")

            # ── ask_user ────────────────────────────────────────────────────
            if fn_name == "ask_user":
                partial = args.get("partial_data") or {}
                # 合併時排除 schedule_id（另外處理成 _pending_edit_schedule_id）
                merged = {**current_context,
                          **{k: v for k, v in partial.items() if v and k != "schedule_id"}}
                # 保留 edit 狀態：partial_data 帶 schedule_id 或 context 已有 _pending_edit
                pending_id = (partial.get("schedule_id")
                              or current_context.get("_pending_edit_schedule_id"))
                if pending_id:
                    merged["_pending_edit_schedule_id"] = pending_id
                return {
                    "intent": "edit" if pending_id else "create",
                    "target_schedule_id": pending_id,
                    "updated_data": merged, "missing_fields": [],
                    "is_complete": False,
                    "reply": args.get("question", "請問還有什麼需要補充的嗎？"),
                }

            # ── create_schedule ─────────────────────────────────────────────
            if fn_name == "create_schedule":
                updated_data = {
                    "title": args.get("title"),
                    "start_time": args.get("start_time"),
                    "end_time": args.get("end_time"),
                    "location": args.get("location"),
                    "description": args.get("description"),
                    "participants": args.get("participants", []),
                }
                return {
                    "intent": "create", "target_schedule_id": None,
                    "updated_data": updated_data, "missing_fields": [],
                    "is_complete": True, "reply": args.get("reply", "✅ 行程已準備好！"),
                }

            # ── update_schedule ─────────────────────────────────────────────
            if fn_name == "update_schedule":
                schedule_id = args.get("schedule_id")
                if not schedule_id:
                    print(f"[AI Tool] update_schedule missing schedule_id, args={args}")
                    return {
                        "intent": "create", "target_schedule_id": None,
                        "updated_data": current_context, "missing_fields": [],
                        "is_complete": False, "reply": "找不到要修改的行程，可以再描述一次嗎？",
                    }
                updated_data = {k: v for k, v in args.items()
                                if k not in ("schedule_id", "reply") and v is not None}
                return {
                    "intent": "edit",
                    "target_schedule_id": schedule_id,
                    "updated_data": updated_data, "missing_fields": [],
                    "is_complete": True, "reply": args.get("reply", "✅ 行程已更新！"),
                }

            # ── delete_schedule ─────────────────────────────────────────────
            if fn_name == "delete_schedule":
                schedule_id = args.get("schedule_id")
                if not schedule_id:
                    print(f"[AI Tool] delete_schedule missing schedule_id, args={args}")
                    return {
                        "intent": "create", "target_schedule_id": None,
                        "updated_data": current_context, "missing_fields": [],
                        "is_complete": False, "reply": "找不到要刪除的行程，可以再描述一次嗎？",
                    }
                title = args.get("schedule_title", "該行程")
                return {
                    "intent": "delete",
                    "target_schedule_id": schedule_id,
                    "updated_data": {}, "missing_fields": [],
                    "is_complete": False,
                    "reply": f"確定要取消「{title}」嗎？",
                }

            # Unknown tool
            return {
                "intent": "create", "target_schedule_id": None,
                "updated_data": current_context, "missing_fields": [],
                "is_complete": False, "reply": "我不太確定，可以再說一次嗎？",
            }

        except Exception as e:
            import traceback
            print(f"AI Tool Parse Error: {e}")
            traceback.print_exc()
            return {
                "updated_data": current_context, "missing_fields": [],
                "is_complete": False, "reply": "抱歉，系統暫時無法處理，請稍後再試。"
            }

ai_service = AIService()
