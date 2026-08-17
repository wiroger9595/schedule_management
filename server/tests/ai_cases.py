"""
AI 行為 case 表 —— pytest 與 conformance harness 共用同一份。

每個 case 宣告它「要求」什麼：
    expect_intent    指定則 intent 必須相符；None = 不要求
    expect_complete  指定則 is_complete 必須相符；None = 不要求
    check            額外檢查，回傳錯誤字串代表不合格、None 代表通過

⚠️ 不要再寫成「if r['intent'] == 'edit': assert ...」那種條件式斷言。
   模型回別的 intent 就整段跳過 → 判定通過。單一模型看退步還行，但拿來排名
   多個模型時方向剛好相反：越爛的模型跳過越多、分數越高。
   要求什麼就寫進 expect_*，不要藏在 if 裡。
"""

# ── Shared fixture: a realistic schedule list ────────────────────────────────
SCHEDULES = [
    {
        "id": "se956cee1a02b74e479012fc523d067461",
        "title": "與文哥開會",
        "start_time": "2026-05-10T10:00:00",
        "location": "新竹巨城",
    },
    {
        "id": "seabc123def456abc123def456abc12345",
        "title": "打球",
        "start_time": "2026-05-12T15:00:00",
        "location": "新竹體育館",
    },
    {
        "id": "se999000111222333444555666777888ab",
        "title": "與Robert吃飯",
        "start_time": "2026-05-15T19:00:00",
        "location": "台北信義區",
    },
]

IDS = {s["id"] for s in SCHEDULES}


# ── check helpers ────────────────────────────────────────────────────────────

def _sid_in_list(r):
    sid = r.get("target_schedule_id")
    return None if sid in IDS else f"schedule_id={sid!r} 不在行程清單裡"


def _sid_null_or_in_list(r):
    sid = r.get("target_schedule_id")
    return None if (sid is None or sid in IDS) else f"schedule_id={sid!r} 是捏造的"


def _no_location_in_update(r):
    upd = r.get("updated_data") or {}
    return None if upd.get("location") in (None, "") else (
        f"只改時間卻夾帶 location={upd.get('location')!r}"
    )


def _has_reply(r):
    return None if (r.get("reply") or "").strip() else "沒有回覆內容"


def _sid_is(expected):
    def _f(r):
        sid = r.get("target_schedule_id")
        return None if sid == expected else f"應沿用 schedule_id={expected!r}，實得 {sid!r}"
    return _f


# ── Cases ────────────────────────────────────────────────────────────────────
# 每筆的來源都是 production log 裡真的壞過的情境。

CASES = [
    # ── schedule_id 必須來自清單 ─────────────────────────────────────────────
    {
        "id": "edit_id_from_list",
        "category": "schedule_id",
        "message": "把與文哥開會的時間改成下午三點",
        "expect_intent": "edit",
        "check": _sid_in_list,
    },
    {
        "id": "delete_id_from_list",
        "category": "schedule_id",
        "message": "刪掉打球的行程",
        "expect_intent": "delete",
        "check": _sid_in_list,
    },
    {
        "id": "empty_list_no_hallucination",
        "category": "schedule_id",
        "message": "把那個行程改掉",
        "schedules": [],
        "expect_complete": False,
    },
    {
        "id": "vague_edit_asks",
        "category": "schedule_id",
        "message": "改一下行程",
        "expect_complete": False,
        "check": _sid_null_or_in_list,
    },

    # ── edit 只能帶用戶真的要改的欄位 ────────────────────────────────────────
    {
        # is_complete 不設要求：要不要先確認日期算產品判斷，不是對錯。
        # 這個 case 保護的是「純度」—— 只改時間不准夾帶 location。
        "id": "time_only_edit_purity",
        "category": "edit_purity",
        "message": "下午三點",
        "context": {"_pending_edit_schedule_id": SCHEDULES[0]["id"]},
        "expect_intent": "edit",
        "check": _no_location_in_update,
    },
    {
        # 沒給新值就不該完成修改 —— 這條是 _validate_tool_call 的「至少一個欄位」
        "id": "empty_update_rejected",
        "category": "edit_purity",
        "message": "把與文哥開會的行程改一下",
        "expect_complete": False,
    },

    # ── 目標不明確 → 問，不要自己選 ──────────────────────────────────────────
    {
        # 「新竹」同時命中巨城和體育館兩筆
        "id": "ambiguous_target_asks",
        "category": "ambiguity",
        "message": "修改新竹的行程",
        "expect_complete": False,
    },
    {
        "id": "no_match_guides",
        "category": "ambiguity",
        "message": "修改跟小美的行程",
        "expect_complete": False,
        "check": _has_reply,
    },

    # ── create 必要欄位 ──────────────────────────────────────────────────────
    {
        "id": "missing_time_asks",
        "category": "create_required",
        "message": "跟Robert吃飯，在信義區",
        "expect_complete": False,
    },
    {
        "id": "missing_location_asks",
        "category": "create_required",
        "message": "明天下午三點跟小明吃飯",
        "expect_complete": False,
    },
    {
        # 資訊齊全。可能直接建立，也可能追問是哪家星巴克 —— 兩種都對，
        # 所以只要求 intent 判對且有回覆。
        "id": "full_info_creates",
        "category": "create_required",
        "message": "明天下午三點跟Robert在信義星巴克吃飯",
        "expect_intent": "create",
        "check": _has_reply,
    },

    # ── 上下文延續（pending edit）────────────────────────────────────────────
    {
        "id": "pending_edit_uses_id",
        "category": "continuity",
        "message": "改成下午五點",
        "context": {"_pending_edit_schedule_id": SCHEDULES[0]["id"]},
        "expect_intent": "edit",
        "check": _sid_is(SCHEDULES[0]["id"]),
    },
    {
        # 修改流程中用戶補了新地點 → 是改這筆，不是開一筆新的
        "id": "pending_edit_not_create",
        "category": "continuity",
        "message": "新竹關埔門市",
        "context": {"_pending_edit_schedule_id": SCHEDULES[1]["id"],
                    "location": "新竹體育館"},
        "expect_intent": "edit",
    },

    # ── 非行程訊息 ───────────────────────────────────────────────────────────
    {
        "id": "offtopic_redirect",
        "category": "offtopic",
        "message": "今天天氣怎樣",
        "expect_complete": False,
        "check": _has_reply,
    },
    {
        "id": "list_query",
        "category": "offtopic",
        "message": "我有什麼行程",
        "expect_complete": False,
        "check": _has_reply,
    },
]


def case_schedules(case: dict) -> list:
    """case 沒指定就用預設清單（[] 也算指定，不能用 or）。"""
    return case["schedules"] if "schedules" in case else SCHEDULES


def evaluate(case: dict, result: dict) -> tuple[bool, float, list]:
    """
    比對單筆結果。回傳 (passed, score, errors)。

    score = 滿足的期望項 / 總期望項。跨模型比較時二元 pass/fail 太粗 ——
    「intent 對但 id 錯」和「全錯」應該分得出來。
    """
    errors: list[str] = []

    if result.get("error"):
        return False, 0.0, [f"provider error: {result['error']}"]

    checks = 0
    hits = 0

    if case.get("expect_intent") is not None:
        checks += 1
        actual = result.get("intent")
        if actual == case["expect_intent"]:
            hits += 1
        else:
            errors.append(f"intent 應為 {case['expect_intent']!r}，實得 {actual!r}")

    if case.get("expect_complete") is not None:
        checks += 1
        actual = result.get("is_complete")
        if actual is case["expect_complete"]:
            hits += 1
        else:
            errors.append(f"is_complete 應為 {case['expect_complete']}，實得 {actual}")

    if case.get("check") is not None:
        checks += 1
        err = case["check"](result)
        if err is None:
            hits += 1
        else:
            errors.append(err)

    score = (hits / checks) if checks else 1.0
    return (not errors), score, errors
