import os
import json
from datetime import datetime
from typing import Dict, Optional, Literal, List
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
import logging
logger = logging.getLogger(__name__)

load_dotenv()


def _log_usage(response, label: str, pre_intent: Optional[str],
               n_tools: int, phase: str = "main") -> None:
    """
    記錄每次 AI 呼叫的 token 用量。

    prompt 瘦身要有基準才知道有沒有效，所以先量再改：
        grep '\\[TokenUsage\\]' server.log
    reasoning_chars 是為了確認 GLM/Qwen 有沒有偷吐 thinking —— 那段不在
    content 裡但一樣算 output token，是純浪費。
    """
    try:
        u = getattr(response, "usage", None)
        if u is None:
            return
        _msg = response.choices[0].message
        _reasoning = getattr(_msg, "reasoning_content", None) or ""
        _details = getattr(u, "prompt_tokens_details", None)
        logger.info("[TokenUsage] " + json.dumps({
            "phase": phase,
            "provider": label,
            "pre_intent": pre_intent,
            "tools": n_tools,
            "prompt": getattr(u, "prompt_tokens", None),
            "completion": getattr(u, "completion_tokens", None),
            "total": getattr(u, "total_tokens", None),
            "cached": getattr(_details, "cached_tokens", None),
            "reasoning_chars": len(_reasoning),
        }, ensure_ascii=False))
    except Exception:
        pass  # 記錄失敗絕不能影響對話

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
        # 順序：Cerebras → Gemini → HuggingFace（按中文品質）
        cerebras_key   = os.getenv("CEREBRAS_API_KEY")
        gemini_key     = os.getenv("GEMINI_API_KEY")

        self._providers: List[tuple] = []  # (client, model_name, label)

        # ── Provider cascade（按中文品質排序，避免「成中天」幻覺）─────────────
        # 1. Cerebras GLM-4.7：中文原生模型，主力
        #    （2026-07 更新：Cerebras 已下架全部 Qwen 模型，
        #      qwen-3-235b-a22b-instruct-2507 會 404，改用 zai-glm-4.7）
        # 2. Gemini Flash：中文好，備援
        # 3. HuggingFace Qwen-7B：中文還可以，但小模型偶爾亂碼，最終備援
        # ❌ 移除 Groq Llama 3.3：中文會幻覺亂碼（「英丽地區」「成中天」等）
        if cerebras_key:
            self._providers.append((
                OpenAI(api_key=cerebras_key, base_url="https://api.cerebras.ai/v1"),
                "zai-glm-4.7", "Cerebras/zai-glm-4.7",
            ))
        if gemini_key:
            self._providers.append((
                OpenAI(api_key=gemini_key,
                       base_url="https://generativelanguage.googleapis.com/v1beta/openai/"),
                "gemini-2.0-flash", "Gemini/gemini-2.0-flash",
            ))

        hf_key = os.getenv("HUGGINGFACE_API_KEY")
        if hf_key and InferenceClient:
            try:
                hf_client = InferenceClient(api_key=hf_key)
                self._providers.append((hf_client, "Qwen/Qwen2.5-7B-Instruct", "HuggingFace/Qwen2.5-7B"))
            except Exception as e:
                logger.info(f"[AIService] HuggingFace init failed: {e}")

        # Groq 留著但只做極端備援（純英文 query 才適合，會被 cascade 跳過）
        # 暫時不加，避免中文亂碼污染用戶體驗

        # ── 測試用 provider（baseline 比較用，不參與 prod cascade fallback）──────
        # 這些 provider 只在 run_test_v2.py 透過 --provider 明確指定時才會用到，
        # prod 環境因為 Cerebras 永遠是第一順位，不會 fallback 到這裡。
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            self._providers.append((
                OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1"),
                "llama-3.3-70b-versatile", "Groq/llama-3.3-70b",
            ))
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            self._providers.append((
                OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1"),
                "qwen/qwen-2.5-72b-instruct", "OpenRouter/qwen-2.5-72b",
            ))
            self._providers.append((
                OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1"),
                "deepseek/deepseek-chat", "OpenRouter/deepseek-chat",
            ))

        if not self._providers:
            raise ValueError("需要設定至少一個 AI API Key")

        # Default client/model = first available provider
        self.client, self.model_name, _ = self._providers[0]
        self.api_key = getattr(self.client, "api_key", None)  # HuggingFace doesn't have api_key attribute
        labels = " → ".join(p[2] for p in self._providers)
        logger.info(f"[AIService] Cascade ({len(self._providers)}): {labels}")

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
                logger.info(f"[AIService] {_label} extract_schedule_info failed: {str(e)[:80]}")
                continue
        logger.info(f"AI API Error: {last_err}")
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
                "description": (
                    "缺少必要資訊、目標行程不明確、或有多個/零個符合描述的行程時使用。"
                    "question 必須是簡短通用問句（例如「請問您要操作哪個行程呢？」「請問您想改到什麼時候呢？」）。"
                    "⚠️ 禁止在 question 裡自己列出行程名稱、時間、地點或任何從行程清單取得的資料——"
                    "後端會自動注入真實行程清單，你只需提供問句本身。"
                    "若是修改/刪除流程的追問，必須在 partial_data 帶入 schedule_id。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "簡短通用問句，禁止包含行程標題、時間或地點等具體資料"},
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
                "description": "建立新行程。title/start_time/end_time/location 齊全才呼叫。participants 可為空（個人行程）。⚠️ 每次只能建立一個行程；若用戶要求一次建立多個，改用 ask_user 告知「目前每次只能新增一個行程，請一個一個來」。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "start_time": {"type": "string", "description": "ISO 8601，如 2026-04-16T15:00:00"},
                        "end_time": {"type": "string", "description": "ISO 8601，預設 start_time + 2小時"},
                        "location": {"type": "string"},
                        "description": {"type": "string"},
                        "participants": {"type": "array", "items": {"type": "string"}},
                        "reply": {"type": "string", "description": "給用戶的一句確認訊息（例如「✅ 行程已建立！」），禁止在 reply 裡重複行程名稱或具體資料，禁止加引導語或建議"}
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
                    "⚠️ 每次只能修改一個行程；若用戶要求一次修改多個，改用 ask_user 告知「目前每次只能修改一個行程，請一個一個來」。"
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
                        "reply": {"type": "string", "description": "給用戶的一句確認訊息（例如「✅ 行程已更新！」），禁止在 reply 裡重複行程名稱或具體資料，禁止加引導語或建議"}
                    },
                    "required": ["schedule_id", "reply"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_schedule",
                "description": (
                    "準備刪除一或多個行程（系統會向用戶確認，尚未真正刪除）。"
                    "刪除單筆用 schedule_id + schedule_title；"
                    "刪除多筆用 schedule_ids（ID 陣列）+ schedule_titles（標題陣列，順序對應）。"
                    "若目標不明確，改用 ask_user 列出清單讓用戶選擇。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "schedule_id": {"type": "string", "description": "單筆刪除時使用"},
                        "schedule_title": {"type": "string", "description": "單筆刪除時的標題"},
                        "schedule_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "多筆刪除時使用，ID 陣列"
                        },
                        "schedule_titles": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "多筆刪除時的標題陣列，順序與 schedule_ids 對應"
                        }
                    }
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

    # ── Tool subsetting by routed intent ─────────────────────────────────────
    # 全部 5 個 tool schema 約 1,500 tokens，每則訊息都重送。語意路由已經判出
    # intent 時就只送用得到的那幾個。
    # ask_user / reply_to_user 一律保留（追問和純回覆是所有流程的逃生口）；
    # edit 與 delete 互相保留，因為「取消」這類詞兩邊都講得通，路由常互換。
    _TOOLS_BY_INTENT: Dict[str, tuple] = {
        "query":  ("reply_to_user", "ask_user"),
        "create": ("create_schedule", "ask_user", "reply_to_user"),
        "edit":   ("update_schedule", "delete_schedule", "ask_user", "reply_to_user"),
        "delete": ("delete_schedule", "update_schedule", "ask_user", "reply_to_user"),
    }

    @classmethod
    def _tools_for_intent(cls, intent: Optional[str]) -> List[dict]:
        names = cls._TOOLS_BY_INTENT.get(intent or "")
        if not names:
            return cls.TOOLS
        return [t for t in cls.TOOLS if t["function"]["name"] in names]

    # ── Output Validation ────────────────────────────────────────────────────
    @staticmethod
    def _validate_tool_call(fn_name: str, args: dict, schedule_list: Optional[List]) -> List[str]:
        """
        Return a list of error strings for the AI to self-correct.
        Empty list = valid output.
        """
        errors: List[str] = []
        valid_ids = {s.get("schedule_id") or s.get("id", "") for s in (schedule_list or [])}
        valid_ids.discard("")

        if fn_name == "update_schedule":
            sid = args.get("schedule_id", "")
            if not sid:
                errors.append("schedule_id 是必填欄位，不可省略")
            elif valid_ids and sid not in valid_ids:
                sample = ", ".join(list(valid_ids)[:3])
                errors.append(
                    f"schedule_id={sid!r} 不在行程清單中。"
                    f"有效的 id 範例：{sample}。請從清單中選擇正確的 id，不可自行編造。"
                )

        if fn_name == "delete_schedule":
            ids = args.get("schedule_ids") or ([args["schedule_id"]] if args.get("schedule_id") else [])
            if not ids:
                errors.append("delete_schedule 必須提供 schedule_id（單筆）或 schedule_ids（多筆）")
            elif valid_ids:
                bad = [sid for sid in ids if sid not in valid_ids]
                if bad:
                    sample = ", ".join(list(valid_ids)[:3])
                    errors.append(
                        f"schedule_id {bad} 不在行程清單中。"
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
                             contact_hints: list = None,
                             session = None,
                             language: str = "zh-TW",
                             query_embedding: list = None,
                             providers: list = None) -> dict:
        """
        使用 Tool Use（Function Calling）處理對話，支援建立、修改、刪除行程。
        回傳格式與舊版相同，LangGraph / chat endpoint 無需改動。

        providers: [(client, model, label)]，給 BYOK 用戶指定自己的端點。
                   刻意用參數傳而非改 self.client —— ai_service 是 singleton，
                   改 self 會讓同時進來的其他用戶打到別人的 key。
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

        # ── 語意路由預判：決定要送哪些 tool、行程清單要送幾筆 ──────────────────
        pre_intent = current_context.pop("_pre_intent", None) if current_context else None
        pre_conf = current_context.pop("_pre_intent_conf", 0.0) if current_context else 0.0
        pending_edit_id = current_context.get("_pending_edit_schedule_id") if current_context else None

        # 裁 tool 比注入 hint 不可逆得多（路由判錯就沒有那個工具可用），
        # 所以另外設一個比路由本身更高的門檻，判不準時退回送全部。
        _trim_intent = "edit" if pending_edit_id else pre_intent
        if _trim_intent and not pending_edit_id:
            try:
                from .config_service import config_get as _cfg_get
                if pre_conf < float(_cfg_get("ai_service.tool_trim_threshold", default=0.65)):
                    _trim_intent = None
            except Exception:
                _trim_intent = None
        _tools = self._tools_for_intent(_trim_intent)

        schedule_section = build_schedule_section(schedule_list, intent=_trim_intent)
        contact_section, memory_section = build_context_sections(_contacts, _mem, current_context or {})

        # ── 預先 embed user_message（給 RAG 和 prompt_rule 共用，省一次 API）──
        # 呼叫端（chat endpoint）已算好時直接重用，不再打 embedding API
        cached_query_embedding = query_embedding
        if cached_query_embedding is None and session:
            try:
                from .embedding_service import EmbeddingService
                cached_query_embedding = EmbeddingService.embed(user_message)
            except Exception as e:
                logger.info(f"[AIService] Pre-embed failed: {str(e)[:80]}")

        # ── RAG 相似案例注入 ──────────────────────────────────────────────────
        rag_section = ""
        if session:
            try:
                from .rag_service import get_rag_service
                rag_service = get_rag_service(session)
                if rag_service.should_use_rag(language):
                    # repo 端已有 max_distance 門檻擋低相關案例，這裡再壓 k：
                    # 5 條約 600~900 tokens，實測上前 2~3 條就決定了模型判斷。
                    try:
                        from .config_service import config_get as _cfg_get3
                        _rag_k = int(_cfg_get3("rag.retrieve_top_k", default=3))
                    except Exception:
                        _rag_k = 3
                    examples = rag_service.get_relevant_examples(
                        user_message=user_message,
                        language=language,
                        # 刻意不用 intent 過濾：RAG 的用途就是幫模型判 intent，
                        # 先按路由結果篩掉其他 intent 的案例會變成自我印證。
                        top_k=_rag_k,
                        query_embedding=cached_query_embedding,  # 重用 embedding
                    )
                    if examples:
                        rag_section = rag_service.format_examples_for_prompt(examples, language)
                        logger.info(f"[RAG] Injected {len(examples)} examples")
            except Exception as e:
                logger.info(f"[AIService] RAG retrieval failed: {str(e)[:80]}")

        system_prompt = build_system_prompt(
            today=today,
            schedule_section=schedule_section,
            memory_section=memory_section,
            contact_section=contact_section,
            rag_section=rag_section,
            user_message=user_message,
            session=session,
            query_embedding=cached_query_embedding,  # 重用 embedding
        )

        # 過濾內部 key（_pre_intent 等）再注入，但保留 hint
        clean_context = {k: v for k, v in current_context.items() if not k.startswith("_")}

        hint_note = f"\n⚡ 語意路由預判 intent={pre_intent}（請優先採用，除非明顯不符）" if pre_intent else ""
        pending_note = (f"\n🔧 正在修改行程 id={pending_edit_id}，"
                        f"用戶的回覆是補充修改內容，請直接呼叫 update_schedule(schedule_id='{pending_edit_id}', ...)"
                        if pending_edit_id else "")
        context_note = (
            f"【目前已知資訊】：{json.dumps(clean_context, ensure_ascii=False)}{hint_note}{pending_note}"
            if clean_context or pre_intent or pending_edit_id else ""
        )
        # 行程對話幾乎不超過 4 輪就結束，20 則是純浪費（一則就 30~100 tokens）
        try:
            from .config_service import config_get as _cfg_get2
            _hist_n = int(_cfg_get2("ai_service.conversation_history_limit", default=8))
        except Exception:
            _hist_n = 8
        trimmed_history = conversation_history[-_hist_n:]

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

            # HuggingFace model support issues (check first, specific)
            if any(k in s for k in ("doesn't support task", "does not support task")):
                return True

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
                # Other unsupported scenarios
                "unsupported", "Unsupported",
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

        def _is_model_unsupported(err: Exception) -> bool:
            """Check if error is due to model/task not being supported (immediate skip, don't retry)."""
            s = str(err)
            return any(k in s for k in ("doesn't support task", "does not support task"))

        last_exception = None
        response = None

        # BYOK 時只用用戶自己的端點，不 fallback 到我們的 key（否則等於免費幫他付錢）
        _providers = providers or self._providers

        for _cli, _model, _label in _providers:
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
                        _is_qwen3 = "qwen-3" in _model.lower()
                        # /no_think in the system message is a Qwen-3 chat-template
                        # directive that disables thinking mode at the tokenizer level,
                        # reliably across all providers (extra_body is provider-specific
                        # and Cerebras may silently ignore it).
                        _msgs = messages
                        if _is_qwen3 and _msgs and _msgs[0].get("role") == "system":
                            _msgs = [{"role": "system",
                                      "content": "/no_think\n" + _msgs[0]["content"]}
                                     ] + list(_msgs[1:])
                        _extra = ({"extra_body": {"thinking": {"type": "disabled", "budget_tokens": 0}}}
                                  if _is_qwen3 else {})
                        response = _cli.chat.completions.create(
                            model=_model,
                            messages=_msgs,
                            tools=_tools,
                            tool_choice="required",
                            temperature=0.1,
                            timeout=8.0,
                            **_extra,
                        )
                    else:
                        _is_qwen3 = "qwen-3" in _model.lower()
                        _msgs = messages
                        if _is_qwen3 and _msgs and _msgs[0].get("role") == "system":
                            _msgs = [{"role": "system",
                                      "content": "/no_think\n" + _msgs[0]["content"]}
                                     ] + list(_msgs[1:])
                        _extra = ({"extra_body": {"thinking": {"type": "disabled", "budget_tokens": 0}}}
                                  if _is_qwen3 else {})
                        response = _cli.chat.completions.create(
                            model=_model,
                            messages=_msgs + [{
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
                            **_extra,
                        )
                    logger.info(f"[AIService] Using {_label}")
                    _log_usage(response, _label, _trim_intent or pre_intent, len(_tools))
                    break  # success
                except Exception as _e:
                    last_exception = _e
                    if _should_skip_provider(_e):
                        # 模型不支持的錯誤：直接跳過，不重試
                        if _is_model_unsupported(_e):
                            logger.info(f"[AIService] {_label} model not supported, skipping: {str(_e)[:80]}")
                            break  # move to next provider
                        # 主力 model rate limited → 直接 fallback 到下一個 provider
                        if _label == _providers[0][2] and len(_providers) <= 1:
                            # 沒有備援 provider → 才報忙碌
                            logger.info(f"[AIService] Primary {_label} rate limited, no fallback → returning busy")
                            raise RuntimeError("AI_RATE_LIMITED") from _e
                        logger.info(f"[AIService] {_label} rate limited → fallback to next provider")
                        break  # move to next provider
                    if use_tool_calling and _is_tool_unsupported(_e):
                        logger.info(f"[AIService] {_label} no tool support → JSON mode")
                        use_tool_calling = False
                        continue
                    # Unknown error — skip provider rather than crash everything
                    logger.info(f"[AIService] {_label} unexpected error, skipping: {str(_e)[:120]}")
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
                _instructor_client = self.instructor_client
                _instructor_model = self.model_name
                if providers is not None:
                    # BYOK：instructor 也要走用戶自己的端點，否則 fallback 會偷打我們的 key
                    try:
                        import instructor
                        _instructor_client = instructor.from_openai(_cli, mode=instructor.Mode.JSON)
                        _instructor_model = _model
                    except Exception:
                        _instructor_client = None

                if _instructor_client:
                    try:
                        action: ScheduleAction = _instructor_client.chat.completions.create(
                            model=_instructor_model,
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
                        logger.info(f"[instructor] fallback failed: {_inst_err}")

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
                        # query 是純回答，永遠不觸發建立/修改流程。
                        # 模型回的 is_complete=true 意思是「我回答完了」，
                        # 但 endpoint 會解讀成「可以寫 DB」→ 正確回答被丟棄。
                        if result.get("intent") == "query":
                            result["is_complete"] = False
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
                logger.info(f"[AI Tool] malformed arguments for {fn_name}: {tc.function.arguments!r} — {_parse_err}")
                return {
                    "intent": "create", "target_schedule_id": None,
                    "updated_data": current_context, "missing_fields": [],
                    "is_complete": False, "reply": "抱歉，我沒有理解清楚，可以再說一次嗎？",
                }
            logger.info(f"[AI Tool] {fn_name}({args})")

            # ── Auto-retry: validate output, re-ask model if invalid ─────────
            _errors = self._validate_tool_call(fn_name, args, schedule_list)
            if _errors:
                _err_str = "\n".join(f"• {e}" for e in _errors)
                logger.info(f"[AI Validation] {fn_name} failed ({len(_errors)} errors), auto-retrying:\n{_err_str}")
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
                    logger.info(f"[constraint_store] record failed (non-critical): {_ce}")
                _retry_msgs = messages + [
                    {"role": "assistant", "content": None,
                     "tool_calls": [{"id": tc.id, "type": "function",
                                     "function": {"name": fn_name, "arguments": tc.function.arguments}}]},
                    {"role": "tool", "tool_call_id": tc.id, "content": "error"},
                    {"role": "system", "content":
                     f"❌ 上一個工具呼叫有以下錯誤，請重新呼叫正確的工具：\n{_err_str}"},
                ]
                try:
                    _is_qwen3_retry = "qwen-3" in _model.lower()
                    _retry_msgs_final = _retry_msgs
                    if _is_qwen3_retry and _retry_msgs_final and _retry_msgs_final[0].get("role") == "system":
                        _retry_msgs_final = [{"role": "system",
                                              "content": "/no_think\n" + _retry_msgs_final[0]["content"]}
                                             ] + list(_retry_msgs_final[1:])
                    _retry_extra = ({"extra_body": {"thinking": {"type": "disabled", "budget_tokens": 0}}}
                                    if _is_qwen3_retry else {})
                    _retry_resp = _cli.chat.completions.create(
                        model=_model, messages=_retry_msgs_final, tools=_tools,
                        tool_choice="required", temperature=0.1, timeout=8.0,
                        **_retry_extra,
                    )
                    _log_usage(_retry_resp, _label, _trim_intent or pre_intent,
                               len(_tools), phase="validation_retry")
                    _retry_tc = (_retry_resp.choices[0].message.tool_calls or [None])[0]
                    if _retry_tc:
                        _retry_args = json.loads(_retry_tc.function.arguments)
                        _retry_errors = self._validate_tool_call(_retry_tc.function.name, _retry_args, schedule_list)
                        if not _retry_errors:
                            logger.info(f"[AI Validation] retry succeeded → {_retry_tc.function.name}")
                            fn_name = _retry_tc.function.name
                            args = _retry_args
                            tc = _retry_tc
                        else:
                            logger.info(f"[AI Validation] retry still invalid: {_retry_errors}")
                except Exception as _retry_err:
                    logger.info(f"[AI Validation] retry call failed: {_retry_err}")

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
                    logger.info(f"[AI Force-List] {fn_name} bad id={_sid!r} → showing list")
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
                _original_question = args.get("question", "請問還有什麼需要補充的嗎？")
                question = _original_question

                # ── Priority fix: if AI gave a valid schedule_id, replace any
                # quoted title in the question with the REAL title from that schedule.
                # This handles thinking-mode hallucinations even when the regex
                # sanitization below can't run (e.g. sparse schedule_list).
                if pending_id and schedule_list:
                    _matched_sched = next(
                        (s for s in schedule_list
                         if (s.get("schedule_id") or s.get("id", "")) == pending_id),
                        None,
                    )
                    if _matched_sched and _matched_sched.get("title"):
                        _real_t = _matched_sched["title"]
                        _qts = _re.findall(r'[「【]([^」】\n]{1,40})[」】]', question)
                        if _qts and _qts[0] != _real_t:
                            question = _re.sub(
                                r'[「【][^」】\n]{1,40}[」】]',
                                f'「{_real_t}」',
                                question,
                                count=1,
                            )
                            logger.info(f"[AI ask_user] fixed hallucinated title {_qts[0]!r} → {_real_t!r}")

                # Guard: if AI quoted a title (「X」) that isn't in the real schedule
                # list, the model hallucinated it (thinking mode leak / garbled output).
                # Replace the whole question with the verified schedule list.
                _quoted_titles = _re.findall(r'[「【]([^」】\n]{1,40})[」】]', question)
                if _quoted_titles and schedule_list:
                    _real_titles = {(s.get("title") or "").strip() for s in schedule_list}
                    _real_titles.discard("")
                    if _real_titles and not any(
                        any(rt in qt or qt in rt for rt in _real_titles)
                        for qt in _quoted_titles
                    ):
                        logger.info(f"[AI ask_user] hallucinated title {_quoted_titles} not in real list → injecting list")
                        question = build_inline_list(schedule_list, verb="操作")
                elif needs_list_injection(question) and schedule_list:
                    question = build_inline_list(schedule_list, verb="操作")
                    logger.info(f"[AI ask_user] injected schedule list (original: {_original_question[:60]!r})")

                # Signal Flutter to show TimePickerMessage when AI is asking for a time.
                # Use _original_question so sanitization (which strips "什麼時候") doesn't
                # prevent the time picker from appearing.
                _TIME_ASK_KEYWORDS = (
                    "什麼時候", "什麼時間", "哪個時間", "哪天", "幾點",
                    "改到", "改成", "新的時間", "想改到", "幾月", "幾日",
                    "what time", "when",
                )
                _LOC_ASK_KEYWORDS = (
                    "哪裡", "哪個地點", "什麼地點", "在哪", "地點呢",
                    "什麼地址", "哪個地方", "地方呢", "地點是",
                    "where", "location", "address",
                )
                _needs_time = bool(
                    pending_id
                    and any(k in _original_question for k in _TIME_ASK_KEYWORDS)
                    and not any(k in _original_question for k in _LOC_ASK_KEYWORDS)
                )
                _needs_location = bool(
                    any(k in _original_question for k in _LOC_ASK_KEYWORDS)
                    and not any(k in _original_question for k in _TIME_ASK_KEYWORDS)
                )
                return {
                    "intent": "edit" if pending_id else "create",
                    "target_schedule_id": pending_id,
                    "updated_data": merged, "missing_fields": [],
                    "is_complete": False,
                    "needs_time_input": _needs_time,
                    "needs_location_input": _needs_location,
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
                    logger.info(f"[AI Tool] update_schedule missing schedule_id, args={args}")
                    _q = build_inline_list(schedule_list or [], verb="修改")
                    return {
                        "intent": "create", "target_schedule_id": None,
                        "updated_data": current_context, "missing_fields": [],
                        "is_complete": False, "reply": _q,
                    }
                updated_data = {k: v for k, v in args.items()
                                if k not in ("schedule_id", "reply") and v is not None}
                _upd_reply = args.get("reply", "✅ 行程已更新！")
                # Fix hallucinated title in reply text
                if schedule_list:
                    _upd_sched = next(
                        (s for s in schedule_list
                         if (s.get("schedule_id") or s.get("id", "")) == schedule_id),
                        None,
                    )
                    if _upd_sched and _upd_sched.get("title"):
                        _real_t2 = _upd_sched["title"]
                        _qts2 = _re.findall(r'[「【]([^」】\n]{1,40})[」】]', _upd_reply)
                        if _qts2 and _qts2[0] != _real_t2:
                            _upd_reply = _re.sub(
                                r'[「【][^」】\n]{1,40}[」】]',
                                f'「{_real_t2}」',
                                _upd_reply,
                                count=1,
                            )
                # Detect: AI called update_schedule asking for time/location but gave no actual fields.
                if not updated_data:
                    _time_kws = (
                        "什麼時候", "什麼時間", "幾點", "哪天", "改到",
                        "哪個時間", "新的時間", "想改到", "幾月", "幾日",
                    )
                    _loc_kws = (
                        "哪裡", "哪個地點", "什麼地點", "在哪", "地點呢",
                        "什麼地址", "哪個地方", "地方呢", "where", "location", "address",
                    )
                    _ctx = {**current_context, "_pending_edit_schedule_id": schedule_id}
                    if any(k in _upd_reply for k in _time_kws):
                        logger.info(f"[AI update_schedule] empty update + time-ask reply → needs_time_input")
                        return {
                            "intent": "edit", "target_schedule_id": schedule_id,
                            "updated_data": _ctx, "missing_fields": [],
                            "is_complete": False, "needs_time_input": True, "reply": _upd_reply,
                        }
                    if any(k in _upd_reply for k in _loc_kws):
                        logger.info(f"[AI update_schedule] empty update + location-ask reply → needs_location_input")
                        return {
                            "intent": "edit", "target_schedule_id": schedule_id,
                            "updated_data": _ctx, "missing_fields": [],
                            "is_complete": False, "needs_location_input": True, "reply": _upd_reply,
                        }
                    # Empty update, generic reply — show reply and keep context
                    return {
                        "intent": "edit", "target_schedule_id": schedule_id,
                        "updated_data": current_context, "missing_fields": [],
                        "is_complete": False, "reply": _upd_reply,
                    }
                return {
                    "intent": "edit",
                    "target_schedule_id": schedule_id,
                    "updated_data": updated_data, "missing_fields": [],
                    "is_complete": True, "reply": _upd_reply,
                }

            # ── delete_schedule ─────────────────────────────────────────────
            if fn_name == "delete_schedule":
                # Support both single (schedule_id) and multi (schedule_ids)
                ids = args.get("schedule_ids") or ([args["schedule_id"]] if args.get("schedule_id") else [])
                titles = args.get("schedule_titles") or ([args.get("schedule_title", "該行程")] if args.get("schedule_id") else [])
                if not ids:
                    logger.info(f"[AI Tool] delete_schedule missing id(s), args={args}")
                    _q = build_inline_list(schedule_list or [], verb="刪除")
                    return {
                        "intent": "create", "target_schedule_id": None,
                        "updated_data": current_context, "missing_fields": [],
                        "is_complete": False, "reply": _q,
                    }
                if len(ids) == 1:
                    reply = f"確定要取消「{titles[0]}」嗎？"
                else:
                    items = "、".join(f"「{t}」" for t in titles[:len(ids)])
                    reply = f"確定要取消以下 {len(ids)} 個行程嗎？\n{items}"
                return {
                    "intent": "delete",
                    "target_schedule_ids": ids,
                    "target_schedule_id": ids[0],
                    "updated_data": {}, "missing_fields": [],
                    "is_complete": False,
                    "reply": reply,
                }

            # ── reply_to_user ────────────────────────────────────────────────
            if fn_name == "reply_to_user":
                reply_text = _strip_thinking(args.get("reply", ""))
                if is_off_topic(user_message, reply_text):
                    logger.info(f"[AI Guard] off-topic reply intercepted. user={user_message[:60]!r}")
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
            logger.info(f"AI Tool Parse Error: {e}")
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
        session = None,
        language: str = "zh-TW",
    ) -> dict:
        """
        Process conversation using a specific provider (for model comparison).
        provider_index: 0=first provider, 1=second, etc.
        """
        if provider_index >= len(self._providers):
            return {"error": f"Provider index {provider_index} out of range"}

        _cli, _model, _label = self._providers[provider_index]
        logger.info(f"[compare] Using {_label} (index {provider_index})")

        # 只用指定的 provider，不 cascade。用 providers 參數傳而不是暫時改
        # self._providers / self.client —— ai_service 是 singleton，改 self
        # 會讓同時進來的其他請求打到這個 provider
        try:
            return self.process_conversation(
                user_message=user_message,
                current_context=current_context,
                conversation_history=conversation_history,
                schedule_list=schedule_list,
                memory_snippets=memory_snippets,
                contact_hints=contact_hints,
                session=session,
                language=language,
                providers=[(_cli, _model, _label)],
            )
        except Exception as e:
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
