import os
import json
from datetime import datetime
from typing import Dict, Optional, Literal
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

load_dotenv()

# HuggingFace Inference
try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None


# ── Pydantic schema for instructor fallback ───────────────────────────────────
class ScheduleAction(BaseModel):
    intent: Literal["create", "edit", "delete"] = "create"
    target_schedule_id: Optional[str] = None
    updated_data: dict = Field(default_factory=dict)
    is_complete: bool = False
    reply: str = ""


# ── Mock response classes for HuggingFace compatibility ──────────────────
class _MockMessage:
    def __init__(self, text: str):
        self.content = text
        self.tool_calls = None


class _MockChoice:
    def __init__(self, text: str):
        self.message = _MockMessage(text)


class _MockResponse:
    def __init__(self, text: str):
        self.choices = [_MockChoice(text)]


class AIService:
    def __init__(self):
        # ── Provider cascade: rate-limit / auth error 時依序 fallback ──────────
        # 順序：Cerebras → Groq 70B → Gemini → OpenRouter → Groq 8B → Together → Cloudflare
        cerebras_key   = os.getenv("CEREBRAS_API_KEY")
        gemini_key     = os.getenv("GEMINI_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        groq_key       = os.getenv("GROQ_API_KEY")
        together_key   = os.getenv("TOGETHER_API_KEY")
        cf_account     = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        cf_token       = os.getenv("CLOUDFLARE_API_TOKEN")

        self._providers: list[tuple] = []  # (client, model_name, label)

        # ── Provider cascade: HuggingFace 優先（無配額限制）──
        # HuggingFace (主力，免費無限) → Groq (備援) → Cerebras (備援) → Gemini (最終)
        hf_key = os.getenv("HUGGINGFACE_API_KEY")

        if hf_key and InferenceClient:
            try:
                hf_client = InferenceClient(api_key=hf_key)
                # 使用 Mistral-Large（HuggingFace 推薦的開源模型，自動選擇最適版本）
                self._providers.append((hf_client, "mistralai/Mistral-Large-Instruct-2407", "HuggingFace/Mistral-Large"))
            except Exception as e:
                print(f"[AIService] HuggingFace init failed: {e}")

        if groq_key:
            _groq = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            self._providers.append((_groq, "llama-3.3-70b-versatile", "Groq/llama-3.3-70b"))
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

        if not self._providers:
            raise ValueError("需要設定至少一個 AI API Key")

        # Default client/model = first available provider
        self.client, self.model_name, _ = self._providers[0]
        self.api_key = getattr(self.client, "api_key", None)  # HuggingFace doesn't have api_key attribute
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
        
        msgs = [
            {"role": "system", "content": "You are a helpful JSON extraction assistant."},
            {"role": "user", "content": prompt},
        ]
        last_err = None
        for _cli, _model, _label in self._providers:
            try:
                response = _cli.chat.completions.create(
                    model=_model,
                    messages=msgs,
                    temperature=0.1,
                    response_format={"type": "json_object"},
                    timeout=8.0,
                )
                text = response.choices[0].message.content.strip()
                return json.loads(text)
            except Exception as e:
                last_err = e
                print(f"[AIService] {_label} extract_schedule_info failed: {str(e)[:80]}")
                continue
        print(f"AI API Error: {last_err}")
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
                "description": "缺少必要資訊、目標行程不明確、或清單中有多個/零個符合描述的行程時使用。目標不明確時，question 中必須列出行程清單供用戶選擇（格式：1️⃣ 名稱 — 時間 — 地點）",
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
                "description": "建立新行程。title/start_time/end_time/location 齊全才呼叫。participants 可為空（個人行程）。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "start_time": {"type": "string", "description": "ISO 8601，如 2026-04-16T15:00:00"},
                        "end_time": {"type": "string", "description": "ISO 8601，預設 start_time + 2小時"},
                        "location": {"type": "string"},
                        "description": {"type": "string"},
                        "participants": {"type": "array", "items": {"type": "string"}},
                        "reply": {"type": "string", "description": "給用戶的一句確認訊息（只說建立了什麼，禁止加引導語或建議）"}
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
                    "若清單中有多個符合或找不到符合描述的行程，必須改用 ask_user 列出行程清單讓用戶選擇。"
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
                        "clear_participants": {
                            "type": "boolean",
                            "description": "true = 移除全部參與者，改為個人行程（不需指定名字）"
                        },
                        "reply": {"type": "string", "description": "給用戶的一句確認訊息（只說改了什麼，禁止加引導語或建議）"}
                    },
                    "required": ["schedule_id", "reply"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_schedule",
                "description": "準備刪除行程（系統會向用戶確認，尚未真正刪除）。若目標不明確或有多個符合，改用 ask_user 列出清單讓用戶選擇。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "schedule_id": {"type": "string"},
                        "schedule_title": {"type": "string", "description": "行程標題，用於確認訊息"}
                    },
                    "required": ["schedule_id", "schedule_title"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "reply_to_user",
                "description": (
                    "純文字回覆用戶，不做任何行程操作。適用於：\n"
                    "1. 查詢/列出行程（用戶說「全部」「今天」「這週」「有什麼行程」等）\n"
                    "2. 無法找到符合的行程（告知用戶）\n"
                    "3. 一般詢問、確認、問候等不需要操作的情境"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reply": {"type": "string", "description": "給用戶的完整回覆內容"}
                    },
                    "required": ["reply"]
                }
            }
        }
    ]

    # ── Output Validation ────────────────────────────────────────────────────
    @staticmethod
    def _validate_tool_call(fn_name: str, args: dict, schedule_list: list | None) -> list[str]:
        """
        Return a list of error strings for the AI to self-correct.
        Empty list = valid output.
        """
        errors: list[str] = []
        valid_ids = {s.get("schedule_id") or s.get("id", "") for s in (schedule_list or [])}
        valid_ids.discard("")

        if fn_name in ("update_schedule", "delete_schedule"):
            sid = args.get("schedule_id", "")
            if not sid:
                errors.append("schedule_id 是必填欄位，不可省略")
            elif valid_ids and sid not in valid_ids:
                sample = ", ".join(list(valid_ids)[:3])
                errors.append(
                    f"schedule_id={sid!r} 不在行程清單中。"
                    f"有效的 id 範例：{sample}。請從清單中選擇正確的 id，不可自行編造。"
                )

        if fn_name == "update_schedule":
            allowed = {"title", "start_time", "location", "description",
                       "participants", "remove_participants", "clear_participants"}
            changed = {k for k in args if k in allowed and args[k] is not None}
            if not changed:
                errors.append("update_schedule 必須至少帶入一個修改欄位（title/start_time/location 等），請先用 ask_user 詢問用戶要改成什麼")

        return errors

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

        from .prompt_builder import build_schedule_section, build_context_sections, build_system_prompt

        # ── 用戶記憶 & 聯絡人提示 ──────────────────────────────────────────────
        _mem = memory_snippets or (current_context or {}).get("_memory_snippets") or []
        _contacts = contact_hints or (current_context or {}).get("_contact_hints") or []

        schedule_section = build_schedule_section(schedule_list)
        contact_section, memory_section = build_context_sections(_contacts, _mem, current_context or {})
        system_prompt = build_system_prompt(today, schedule_section, memory_section, contact_section)

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
        import re as _re

        def _strip_thinking(text: str) -> str:
            """Strip <think>...</think> blocks from Qwen-3 thinking mode output."""
            return _re.sub(r'<think>[\s\S]*?</think>', '', text).strip()

        def _should_skip_provider(err: Exception) -> bool:
            """Return True if we should abandon this provider and try the next one."""
            s = str(err)
            # Rate / capacity / availability
            if any(k in s for k in (
                "429", "queue_exceeded", "too_many_requests",
                "high traffic", "rate_limit", "rate limit",
                "overloaded", "503", "529",
                # Cloudflare Workers AI loading / cold start
                "Service Unavailable", "service unavailable",
                "model loading", "Model Loading", "loading",
                "not available", "Not Available",
                # Generic connection / timeout
                "Connection error", "connection error",
                "timed out", "timeout", "Timeout",
                "RemoteProtocolError", "ReadTimeout",
            )):
                return True
            # Auth / key errors
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

        for _cli, _model, _label in self._providers:
            use_tool_calling = True
            for _attempt in range(2):  # max 2 attempts per provider
                try:
                    if _attempt > 0:
                        _time.sleep(1)

                    # ── HuggingFace special handling ──
                    if isinstance(_cli, InferenceClient) and InferenceClient:
                        # Use HuggingFace's chat_completion API (OpenAI-compatible)
                        try:
                            response_obj = _cli.chat_completion(
                                model=_model,
                                messages=messages + [{
                                    "role": "system",
                                    "content": '請以 JSON 回應，格式：{"intent":"create|edit|delete","target_schedule_id":null,"updated_data":{},"is_complete":false,"reply":"回覆內容"}'
                                }],
                                max_tokens=1024,
                                temperature=0.1,
                            )
                            # HuggingFace returns dict-like response
                            response_text = response_obj.choices[0].message.content
                            response = _MockResponse(response_text)
                            use_tool_calling = False
                        except Exception as _hf_err:
                            # Fallback: try text_generation with plain text prompt
                            text_prompt = ""
                            for msg in messages:
                                role = msg.get("role", "user")
                                content = msg.get("content", "")
                                if role == "system":
                                    text_prompt += f"{content}\n\n"
                                elif role == "user":
                                    text_prompt += f"用戶: {content}\n"
                                elif role == "assistant":
                                    text_prompt += f"助手: {content}\n"

                            text_prompt += "請以 JSON 回應，格式：{\"intent\":\"create|edit|delete\",\"target_schedule_id\":null,\"updated_data\":{},\"is_complete\":false,\"reply\":\"回覆內容\"}\n\n助手: "

                            response_text = _cli.text_generation(
                                text_prompt,
                                max_new_tokens=1024,
                                temperature=0.1,
                            )

                            response = _MockResponse(response_text)
                            use_tool_calling = False
                    elif use_tool_calling:
                        response = _cli.chat.completions.create(
                            model=_model,
                            messages=messages,
                            tools=self.TOOLS,
                            tool_choice="required",
                            temperature=0.1,
                            timeout=8.0,
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
                            timeout=8.0,
                        )
                    print(f"[AIService] Using {_label}")
                    break  # success
                except Exception as _e:
                    last_exception = _e
                    if _should_skip_provider(_e):
                        # 主力 model（第一順位）限速時：先 sleep 重試一次，仍失敗才報忙碌
                        if _label == self._providers[0][2]:
                            if _attempt == 0:
                                print(f"[AIService] Primary {_label} rate limited → sleep 15s & retry")
                                _time.sleep(15)
                                continue  # retry same provider
                            print(f"[AIService] Primary {_label} rate limited (after retry) → returning busy")
                            raise RuntimeError("AI_RATE_LIMITED") from _e
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
                content = _strip_thinking(getattr(msg, "content", "") or "")
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

            # ── Auto-retry: validate output, re-ask model if invalid ─────────
            _errors = self._validate_tool_call(fn_name, args, schedule_list)
            if _errors:
                _err_str = "\n".join(f"• {e}" for e in _errors)
                print(f"[AI Validation] {fn_name} failed ({len(_errors)} errors), auto-retrying:\n{_err_str}")
                # Record each error so it's injected into future prompts
                try:
                    from .constraint_store import record_error as _rec_err
                    sid = args.get("schedule_id", "")
                    for _e in _errors:
                        if "schedule_id" in _e and "不在行程清單" in _e:
                            _rec_err("wrong_schedule_id", example=f"AI returned schedule_id={sid!r}")
                        elif "至少帶入一個修改欄位" in _e:
                            _rec_err("empty_update_schedule", example=f"user_message={user_message[:60]!r}")
                        elif "schedule_id 是必填" in _e:
                            _rec_err("missing_schedule_id_in_update", example=f"fn={fn_name}")
                except Exception as _ce:
                    print(f"[constraint_store] record failed (non-critical): {_ce}")
                _retry_msgs = messages + [
                    {"role": "assistant", "content": None,
                     "tool_calls": [{"id": tc.id, "type": "function",
                                     "function": {"name": fn_name, "arguments": tc.function.arguments}}]},
                    {"role": "tool", "tool_call_id": tc.id, "content": "error"},
                    {"role": "system", "content":
                     f"❌ 上一個工具呼叫有以下錯誤，請重新呼叫正確的工具：\n{_err_str}"},
                ]
                try:
                    _retry_resp = _cli.chat.completions.create(
                        model=_model, messages=_retry_msgs, tools=self.TOOLS,
                        tool_choice="required", temperature=0.1, timeout=8.0,
                    )
                    _retry_tc = (_retry_resp.choices[0].message.tool_calls or [None])[0]
                    if _retry_tc:
                        _retry_args = json.loads(_retry_tc.function.arguments)
                        _retry_errors = self._validate_tool_call(_retry_tc.function.name, _retry_args, schedule_list)
                        if not _retry_errors:
                            print(f"[AI Validation] retry succeeded → {_retry_tc.function.name}")
                            fn_name = _retry_tc.function.name
                            args = _retry_args
                            tc = _retry_tc
                        else:
                            print(f"[AI Validation] retry still invalid: {_retry_errors}")
                except Exception as _retry_err:
                    print(f"[AI Validation] retry call failed: {_retry_err}")

            # ── Force list when wrong schedule_id survives retry ─────────────
            from .ai_policy import (
                build_inline_list, build_schedule_list_reply as _pol_list,
                needs_list_injection, is_off_topic, OFF_TOPIC_REDIRECT,
                CANT_FIND_EDIT, CANT_FIND_DELETE, CANT_FIND_GENERIC,
            )
            if fn_name in ("update_schedule", "delete_schedule"):
                _sid = args.get("schedule_id", "")
                _vids = {s.get("schedule_id") or s.get("id", "") for s in (schedule_list or [])}
                _vids.discard("")
                if _sid and _vids and _sid not in _vids:
                    _verb = "修改" if fn_name == "update_schedule" else "刪除"
                    _q = build_inline_list(schedule_list or [], verb=_verb)
                    print(f"[AI Force-List] {fn_name} bad id={_sid!r} → showing list")
                    return {
                        "intent": "create", "target_schedule_id": None,
                        "updated_data": current_context, "missing_fields": [],
                        "is_complete": False, "reply": _q,
                    }

            # ── ask_user ────────────────────────────────────────────────────
            if fn_name == "ask_user":
                partial = args.get("partial_data") or {}
                merged = {**current_context,
                          **{k: v for k, v in partial.items() if v and k != "schedule_id"}}
                pending_id = (partial.get("schedule_id")
                              or current_context.get("_pending_edit_schedule_id"))
                if pending_id:
                    merged["_pending_edit_schedule_id"] = pending_id
                question = args.get("question", "請問還有什麼需要補充的嗎？")
                if needs_list_injection(question) and schedule_list:
                    question = build_inline_list(schedule_list, verb="操作")
                    print(f"[AI ask_user] injected schedule list (original: {args.get('question','')[:60]!r})")
                return {
                    "intent": "edit" if pending_id else "create",
                    "target_schedule_id": pending_id,
                    "updated_data": merged, "missing_fields": [],
                    "is_complete": False,
                    "reply": question,
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
                    _q = build_inline_list(schedule_list or [], verb="修改")
                    return {
                        "intent": "create", "target_schedule_id": None,
                        "updated_data": current_context, "missing_fields": [],
                        "is_complete": False, "reply": _q,
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
                    _q = build_inline_list(schedule_list or [], verb="刪除")
                    return {
                        "intent": "create", "target_schedule_id": None,
                        "updated_data": current_context, "missing_fields": [],
                        "is_complete": False, "reply": _q,
                    }
                title = args.get("schedule_title", "該行程")
                return {
                    "intent": "delete",
                    "target_schedule_id": schedule_id,
                    "updated_data": {}, "missing_fields": [],
                    "is_complete": False,
                    "reply": f"確定要取消「{title}」嗎？",
                }

            # ── reply_to_user ────────────────────────────────────────────────
            if fn_name == "reply_to_user":
                reply_text = _strip_thinking(args.get("reply", ""))
                if is_off_topic(user_message, reply_text):
                    print(f"[AI Guard] off-topic reply intercepted. user={user_message[:60]!r}")
                    reply_text = OFF_TOPIC_REDIRECT
                return {
                    "intent": "query", "target_schedule_id": None,
                    "updated_data": current_context, "missing_fields": [],
                    "is_complete": False, "reply": reply_text,
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

    def process_conversation_with_provider(
        self,
        provider_index: int,
        user_message: str,
        current_context: dict = None,
        conversation_history: list = None,
        schedule_list: list = None,
        memory_snippets: list = None,
        contact_hints: list = None,
    ) -> dict:
        """
        Process conversation using a specific provider (for model comparison).
        provider_index: 0=first provider, 1=second, etc.
        """
        if provider_index >= len(self._providers):
            return {"error": f"Provider index {provider_index} out of range"}

        # Use the specified provider only, no cascade
        try:
            _cli, _model, _label = self._providers[provider_index]
            print(f"[compare] Using {_label} (index {provider_index})")

            # Reuse the same process_conversation logic but with single provider
            # by temporarily replacing _providers
            original_providers = self._providers
            self._providers = [(_cli, _model, _label)]
            self.client = _cli
            self.model_name = _model

            result = self.process_conversation(
                user_message=user_message,
                current_context=current_context,
                conversation_history=conversation_history,
                schedule_list=schedule_list,
                memory_snippets=memory_snippets,
                contact_hints=contact_hints,
            )

            # Restore original providers
            self._providers = original_providers
            self.client = original_providers[0][0]
            self.model_name = original_providers[0][1]

            return result
        except Exception as e:
            self._providers = original_providers
            self.client = original_providers[0][0]
            self.model_name = original_providers[0][1]
            err_msg = str(e)[:200]
            return {
                "error": err_msg,
                "intent": "ERROR",
                "target_schedule_id": None,
                "updated_data": current_context or {},
                "missing_fields": [],
                "is_complete": False,
                "reply": f"[ERROR] {err_msg}",
            }

ai_service = AIService()
