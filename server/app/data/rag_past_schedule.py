"""
RAG 訓練資料：修改過期行程
場景：用戶要修改的行程時間已經過了，系統需要：
1. 只改時間（無日期）→ 保留原始日期，只更新時間
2. 明確說要重新安排到未來 → 追問具體未來日期
3. 用戶指定明確未來時間 → 直接 update
4. 模糊未來時段（暑假/下次）→ 追問具體日期
"""

RAG_PAST_SCHEDULE_ZH = [
    # ========================================================================
    # 場景 1：只改時間 → 保留原始日期
    # ========================================================================
    {
        "category": "past_schedule",
        "user_message": "把昨天的開會改成下午3點",
        "context": {
            "schedule_list": [
                {"id": "abc123", "title": "開會", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "abc123",
            "start_time": "2026-05-08T15:00:00",
            "_correction_note": "用戶只給新時間沒給新日期 → 保留原始日期 2026-05-08，只更新時間為 15:00；⚠️ 禁止追問「哪一天的3點？」"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "把昨天的開會改到後天下午3點",
        "context": {
            "schedule_list": [
                {"id": "abc123", "title": "開會", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "abc123",
            "start_time": "2026-05-11T15:00:00",
            "_correction_note": "用戶給完整未來時間 → 直接 update，不追問"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "上週的午餐改到下週吧",
        "context": {
            "schedule_list": [
                {"id": "xyz", "title": "午餐", "start_time": "2026-05-02T12:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "parsed_data": {
            "_correction_note": "原時間已過期 + 模糊未來時間（下週）→ 追問「下週哪一天、幾點？」"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "把昨天的會議改成下午",
        "context": {
            "schedule_list": [
                {"id": "m1", "title": "會議", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "parsed_data": {
            "_correction_note": "過期行程不可保留原始日期 → 追問「您是要改到今天下午、明天下午，還是其他日期？」"
        },
    },

    # ========================================================================
    # 場景 2：相對時間引用（要求重新安排）
    # ========================================================================
    {
        "category": "past_schedule",
        "user_message": "把上次取消的開會重新約到明天",
        "context": {
            "schedule_list": [
                {"id": "old", "title": "開會", "start_time": "2026-05-05T14:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "parsed_data": {
            "_correction_note": "重新安排 + 缺具體時間 → 追問「明天幾點開會？」"
        },
    },

    # ========================================================================
    # 場景 3：今天已過時段（不是真的過期，但今天時間已過）
    # ========================================================================
    {
        "category": "past_schedule",
        "user_message": "把今天下午3點的會議改到上午9點",
        "context": {
            "schedule_list": [
                {"id": "t1", "title": "會議", "start_time": "2026-05-09T15:00:00"}
            ],
            "current_time": "2026-05-09T14:00:00",
        },
        "intent": "edit",
        "is_complete": False,
        "parsed_data": {
            "_correction_note": "改到的新時間若也是過去 → 提示「今天上午9點已經過了，您是想改到明天上午9點嗎？」"
        },
    },

    # ========================================================================
    # 場景 4：「再約一次」= 新建，非 edit
    # ========================================================================
    {
        "category": "past_schedule",
        "user_message": "上次跟小明的午餐再約一次",
        "context": {
            "schedule_list": [
                {"id": "p1", "title": "與小明午餐", "start_time": "2026-05-02T12:00:00", "location": "鼎泰豐"}
            ]
        },
        "intent": "create",
        "is_complete": False,
        "parsed_data": {
            "title": "與小明午餐",
            "location": "鼎泰豐",
            "_correction_note": "⚠️ 「再約一次/再來一次」= 新建（複製過期設定），不是 edit；繼承 location/title，追問新日期"
        },
    },

    # ========================================================================
    # 場景 5：刪除過期行程 → 仍需確認
    # ========================================================================
    {
        "category": "past_schedule",
        "user_message": "刪掉昨天的會議",
        "context": {
            "schedule_list": [
                {"id": "d1", "title": "會議", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "delete",
        "is_complete": False,
        "parsed_data": {
            "_correction_note": "刪除任何行程（含過期）→ is_complete=False，先確認「確定要刪除昨天的『會議』嗎？」避免誤刪"
        },
    },

    # ========================================================================
    # 場景 6：用戶指定過去具體日期 → 可能口誤
    # ========================================================================
    {
        "category": "past_schedule",
        "user_message": "把會議改到 2026-05-01 下午3點",
        "context": {
            "schedule_list": [
                {"id": "f1", "title": "會議", "start_time": "2026-05-15T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "parsed_data": {
            "_correction_note": "用戶明確指定過去日期 → 可能口誤，提示「您指定的 2026-05-01 已經過了，請問您是說 2026-06-01 還是其他日期？」"
        },
    },

    # ========================================================================
    # 場景 7：改過期行程的非時間欄位
    # ========================================================================
    {
        "category": "past_schedule",
        "user_message": "把上週的會議改名為 Q2 季度檢討",
        "context": {
            "schedule_list": [
                {"id": "p8", "title": "會議", "start_time": "2026-05-02T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "p8",
            "title": "Q2 季度檢討",
            "_correction_note": "純改 title 是歷史記錄維護 → 直接 update，不需追問新時間"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "把上禮拜的開會改為只有我參加",
        "context": {
            "schedule_list": [
                {"id": "p9", "title": "開會", "start_time": "2026-05-02T10:00:00",
                 "participants": ["@小明", "@小美"]}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "p9",
            "clear_participants": True,
            "_correction_note": "純改 participants → 直接 update，過期記錄維護合法操作"
        },
    },
    # ========================================================================
    # 場景 8：模糊未來時間
    # ========================================================================
    {
        "category": "past_schedule",
        "user_message": "三月底的旅遊改到暑假",
        "context": {
            "schedule_list": [
                {"id": "p11", "title": "旅遊", "start_time": "2026-03-30T09:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "parsed_data": {
            "_correction_note": "⚠️ 「暑假/年底/下次」太模糊，無法解析 → 追問「暑假哪一天出發？」禁止假設「暑假 = 7/1」自動填入"
        },
    },

    # ========================================================================
    # 場景 9：「只改一個欄位」→ 沿用其他欄位
    # ========================================================================
    {
        "category": "past_schedule",
        "user_message": "把三月十五的開會改成晚上八點",
        "context": {
            "schedule_list": [
                {"id": "p12", "title": "開會", "start_time": "2026-03-15T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "p12",
            "start_time": "2026-03-15T20:00:00",
            "_correction_note": "用戶只改時間 → 沿用原日期 2026-03-15，只更新時間為 20:00；「修正歷史記錄」是合法操作，禁止過度追問"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "把三月十五的開會改到下禮拜五",
        "context": {
            "schedule_list": [
                {"id": "p13", "title": "開會", "start_time": "2026-03-15T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "p13",
            "start_time": "2026-05-15T10:00:00",
            "_correction_note": "用戶只改日期 → 沿用原時間 10:00；⚠️ 禁止追問「幾點？」"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "昨天的會議改成上午 9 點",
        "context": {
            "schedule_list": [
                {"id": "p14", "title": "會議", "start_time": "2026-04-29T14:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "p14",
            "start_time": "2026-04-29T09:00:00",
            "_correction_note": "「昨天的 X 改成 HH:MM」→ 保留昨天日期，只更新時間"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "上周三的午餐改到新竹",
        "context": {
            "schedule_list": [
                {"id": "p15", "title": "午餐", "start_time": "2026-04-23T12:00:00", "location": "台北"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "p15",
            "location": "新竹",
            "_correction_note": "用戶只說「改到 [地點]」→ 只更新 location，時間/標題/參與者不動；⚠️ 禁止過度確認「要新建還是修正歷史？」"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "上次的開會加上小華",
        "context": {
            "schedule_list": [
                {"id": "p16", "title": "開會", "start_time": "2026-04-25T10:00:00",
                 "participants": ["@小明"]}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "p16",
            "participants_add": ["@小華"],
            "_correction_note": "「加上某人」= 在原 participants 後追加，不需追問"
        },
    },

]

RAG_PAST_SCHEDULE_EN = [
    {
        "category": "past_schedule",
        "user_message": "Change yesterday's meeting to 3pm",
        "context": {
            "schedule_list": [
                {"id": "abc", "title": "Meeting", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "abc",
            "start_time": "2026-05-08T15:00:00",
            "_correction_note": "User only changes time → keep original date 2026-05-08, update time only; ⚠️ do NOT ask 'which day?' — user already implied yesterday"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "Move yesterday's meeting to next Friday 3pm",
        "context": {
            "schedule_list": [
                {"id": "abc", "title": "Meeting", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "abc",
            "start_time": "2026-05-15T15:00:00",
            "_correction_note": "User provides full future time → direct update, no follow-up needed"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "Reschedule last week's lunch to next week",
        "context": {
            "schedule_list": [
                {"id": "l1", "title": "Lunch", "start_time": "2026-05-02T12:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "parsed_data": {
            "_correction_note": "Vague future time (next week) → ask 'Which day next week and what time?'"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "Let's do that lunch with Mike again",
        "context": {
            "schedule_list": [
                {"id": "p1", "title": "Lunch with Mike", "start_time": "2026-05-02T12:00:00", "location": "Din Tai Fung"}
            ]
        },
        "intent": "create",
        "is_complete": False,
        "parsed_data": {
            "title": "Lunch with Mike",
            "location": "Din Tai Fung",
            "_correction_note": "⚠️ 'do again/redo' = NEW schedule copying old settings, NOT edit; inherit location/title, ask for new date"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "Change today's 3pm meeting to 9am",
        "context": {
            "current_time": "2026-05-09T14:00:00",
            "schedule_list": [
                {"id": "t1", "title": "Meeting", "start_time": "2026-05-09T15:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "parsed_data": {
            "_correction_note": "New time would also be in the past → confirm 'Today's 9am has already passed. Did you mean tomorrow 9am?'"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "Delete yesterday's meeting",
        "context": {
            "schedule_list": [
                {"id": "d1", "title": "Meeting", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "delete",
        "is_complete": False,
        "parsed_data": {
            "_correction_note": "Delete any schedule (incl. past) → is_complete=False, ask 'Delete Meeting from yesterday?' to avoid accidental deletion"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "Move last Wednesday's lunch to Hsinchu",
        "context": {
            "schedule_list": [
                {"id": "L1", "title": "Lunch", "start_time": "2026-04-23T12:00:00", "location": "Taipei"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "L1",
            "location": "Hsinchu",
            "_correction_note": "User specifies only location change → update location only, preserve time/title; ⚠️ do NOT ask 'new or historical fix?'"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "Move yesterday's meeting to next Friday",
        "context": {
            "schedule_list": [
                {"id": "M1", "title": "Meeting", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "M1",
            "start_time": "2026-05-15T10:00:00",
            "_correction_note": "User only changes date → preserve original time 10:00; ⚠️ do NOT ask 'what time?'"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "Move the meeting to May 1, 3pm",
        "context": {
            "schedule_list": [
                {"id": "f1", "title": "Meeting", "start_time": "2026-05-15T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "parsed_data": {
            "_correction_note": "User specifies explicit past date → likely typo, ask 'May 1 has passed. Did you mean June 1 or another date?'"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "Rename last week's meeting to Q2 Review",
        "context": {
            "schedule_list": [
                {"id": "p8", "title": "Meeting", "start_time": "2026-05-02T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "p8",
            "title": "Q2 Review",
            "_correction_note": "Renaming title is historical record maintenance → direct update, no need to ask for new date"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "Remove everyone from last week's meeting",
        "context": {
            "schedule_list": [
                {"id": "p9", "title": "Meeting", "start_time": "2026-05-02T10:00:00",
                 "participants": ["@Mike", "@Sarah"]}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "p9",
            "clear_participants": True,
            "_correction_note": "Clearing participants is historical record maintenance → direct update, no rescheduling needed"
        },
    },
    {
        "category": "past_schedule",
        "user_message": "Add @Tom to last Friday's meeting",
        "context": {
            "schedule_list": [
                {"id": "p16", "title": "Meeting", "start_time": "2026-05-08T10:00:00",
                 "participants": ["@Mike"]}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "parsed_data": {
            "schedule_id": "p16",
            "participants_add": ["@Tom"],
            "_correction_note": "Adding a participant to past record → append to existing participants list, no need to ask"
        },
    },
]


def stats():
    print(f"Past schedule examples: zh={len(RAG_PAST_SCHEDULE_ZH)}, en={len(RAG_PAST_SCHEDULE_EN)}")


if __name__ == "__main__":
    stats()
