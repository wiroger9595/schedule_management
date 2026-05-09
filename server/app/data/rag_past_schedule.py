"""
RAG 訓練資料：修改過期行程
場景：用戶要修改的行程時間已經過了，系統需要：
1. 偵測 schedule_list 中的目標行程時間是過去
2. 必須改到未來時間（不能保留過去日期）
3. 若用戶只說時間沒給日期 → 追問完整未來日期
"""

# 假設今天是 2026-05-09
TODAY = "2026-05-09"

RAG_PAST_SCHEDULE_ZH = [
    # ========================================================================
    # 場景 1：直接改過期行程的時間（用戶給的時間是過去）
    # ========================================================================
    {
        "scenario": "修改過期行程 - 用戶只說時間，需追問日期",
        "user_message": "把昨天的開會改成下午3點",
        "context": {
            "schedule_list": [
                {"id": "abc123", "title": "開會", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_action": "ask_user",
        "expected_question": "原行程已過去，請問您要改到哪一天的下午3點？",
        "rule": "原時間已過期 + 用戶只給時間 → 必須追問未來日期，不可保留昨天日期",
        "WRONG": "update_schedule(start_time='2026-05-08T15:00:00') 把過期時間又改成過期",
        "CORRECT": "ask_user 追問未來日期",
    },
    {
        "scenario": "修改過期行程 - 用戶給未來日期",
        "user_message": "把昨天的開會改到後天下午3點",
        "context": {
            "schedule_list": [
                {"id": "abc123", "title": "開會", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "expected_action": "update_schedule",
        "parsed_data": {"schedule_id": "abc123", "start_time": "2026-05-11T15:00:00"},
        "rule": "原時間已過期 + 用戶給完整未來時間 → 直接 update",
    },
    {
        "scenario": "修改過期行程 - 用戶說「下次/重新約」",
        "user_message": "上週的午餐改到下週吧",
        "context": {
            "schedule_list": [
                {"id": "xyz", "title": "午餐", "start_time": "2026-05-02T12:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_action": "ask_user",
        "expected_question": "下週哪一天、幾點？",
        "rule": "原時間已過期 + 模糊未來時間（下週、明天）→ 追問具體",
    },
    {
        "scenario": "修改過期行程 - 用戶想保留原始日期但其實該改",
        "user_message": "把昨天的會議改成下午",
        "context": {
            "schedule_list": [
                {"id": "m1", "title": "會議", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_action": "ask_user",
        "expected_question": "原會議已過期。您是要改到今天下午、明天下午，還是其他日期？",
        "rule": "過期行程不可保留原始日期 - 必須詢問未來日期",
    },

    # ========================================================================
    # 場景 2：相對時間引用（要求重新安排）
    # ========================================================================
    {
        "scenario": "重新安排過期行程 - 用相對時間",
        "user_message": "把上次取消的開會重新約到明天",
        "context": {
            "schedule_list": [
                {"id": "old", "title": "開會", "start_time": "2026-05-05T14:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_action": "ask_user",
        "expected_question": "明天幾點開會？",
        "rule": "重新安排 + 缺具體時間 → 追問",
    },

    # ========================================================================
    # 場景 3：今天已過時段（不是真的過期，但今天時間已過）
    # ========================================================================
    {
        "scenario": "改到今天已過的時間 - 應提示用戶確認",
        "user_message": "把今天下午3點的會議改到上午9點",
        "context": {
            "schedule_list": [
                {"id": "t1", "title": "會議", "start_time": "2026-05-09T15:00:00"}
            ],
            "current_time": "2026-05-09T14:00:00",
        },
        "intent": "edit",
        "is_complete": False,
        "expected_action": "ask_user",
        "expected_question": "今天上午9點已經過了，您是想改到明天上午9點嗎？",
        "rule": "改到的新時間若也是過去 → 提示用戶確認",
    },

    # ========================================================================
    # 場景 4：批次語意（一個行程 + 過期）
    # ========================================================================
    {
        "scenario": "用戶想複用過期行程設定",
        "user_message": "上次跟小明的午餐再約一次",
        "context": {
            "schedule_list": [
                {"id": "p1", "title": "與小明午餐", "start_time": "2026-05-02T12:00:00", "location": "鼎泰豐"}
            ]
        },
        "intent": "create",  # 重新建立，不是 edit
        "is_complete": False,
        "expected_action": "ask_user",
        "expected_question": "想約哪天的中午在鼎泰豐？",
        "rule": "「再約一次/再來一次」= 新建（複製過期設定），不是 edit",
        "WRONG": "edit + start_time=過去日期",
        "CORRECT": "create 並繼承 location/title，追問新日期",
    },

    # ========================================================================
    # 場景 5：刪除過期行程（這個 OK，沒有時間衝突）
    # ========================================================================
    {
        "scenario": "刪除過期行程",
        "user_message": "刪掉昨天的會議",
        "context": {
            "schedule_list": [
                {"id": "d1", "title": "會議", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "delete",
        "is_complete": True,
        "rule": "刪除過期行程沒有時間衝突問題 - 直接刪",
    },

    # ========================================================================
    # 場景 6：「改到原本時間」的悖論
    # ========================================================================
    {
        "scenario": "用戶要求改成過去具體時間 - 必須提示",
        "user_message": "把會議改到 2026-05-01 下午3點",
        "context": {
            "schedule_list": [
                {"id": "f1", "title": "會議", "start_time": "2026-05-15T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_action": "ask_user",
        "expected_question": "您指定的 2026-05-01 已經過了，請問您是說 2026-06-01 還是其他日期？",
        "rule": "用戶明確指定過去日期 → 提示確認，可能口誤",
    },

    # ========================================================================
    # 場景 7：修改過期行程的非時間欄位（地點/人員/標題）
    # ========================================================================
    {
        "scenario": "改過期行程的地點 - 同樣需要重新設未來時間",
        "user_message": "上周三的午餐改到新竹",
        "context": {
            "schedule_list": [
                {"id": "p7", "title": "午餐", "start_time": "2026-05-06T12:00:00", "location": "台北"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_action": "ask_user",
        "expected_question": "原午餐已過去。您是要新建一個未來在新竹的午餐，還是要把過期的記錄改成新竹？",
        "rule": "改過期行程的地點 → 多半用戶其實要新建（再來一次），要確認意圖",
    },
    {
        "scenario": "改過期行程的標題 - 純記錄維護，不需追問時間",
        "user_message": "把上週的會議改名為 Q2 季度檢討",
        "context": {
            "schedule_list": [
                {"id": "p8", "title": "會議", "start_time": "2026-05-02T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "expected_action": "update_schedule",
        "parsed_data": {"schedule_id": "p8", "title": "Q2 季度檢討"},
        "rule": "純改 title 是歷史記錄維護 → 直接 update，不需新時間",
    },
    {
        "scenario": "改過期行程的參與者 - 純記錄調整",
        "user_message": "把上禮拜的開會改為只有我參加",
        "context": {
            "schedule_list": [
                {"id": "p9", "title": "開會", "start_time": "2026-05-02T10:00:00",
                 "participants": ["@小明", "@小美"]}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "expected_action": "update_schedule",
        "parsed_data": {"schedule_id": "p9", "clear_participants": True},
        "rule": "純改 participants → 直接 update，過期記錄維護常見",
    },
    {
        "scenario": "刪除過期行程 - 直接刪",
        "user_message": "刪除昨天那個被取消的會議",
        "context": {
            "schedule_list": [
                {"id": "p10", "title": "會議", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "delete",
        "is_complete": True,
        "rule": "刪過期 = 安全動作，沒有時間衝突",
    },

    # ========================================================================
    # 場景 8：模糊未來時間表達（暑假、年底、下次）
    # ========================================================================
    {
        "scenario": "過期改到模糊未來",
        "user_message": "三月底的旅遊改到暑假",
        "context": {
            "schedule_list": [
                {"id": "p11", "title": "旅遊", "start_time": "2026-03-30T09:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_action": "ask_user",
        "expected_question": "暑假哪一天出發？大概幾天？",
        "rule": "「暑假/年底/下次」太模糊 → 追問具體日期",
    },

    # ========================================================================
    # 場景 9：「保留日期」的陷阱
    # ========================================================================
    {
        "scenario": "用戶想用過期日期+新時間（陷阱）",
        "user_message": "把三月十五的開會改成晚上八點",
        "context": {
            "schedule_list": [
                {"id": "p12", "title": "開會", "start_time": "2026-03-15T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_action": "ask_user",
        "expected_question": "三月十五已過。您是要把這條過期記錄改成 2026-03-15T20:00（保留歷史）還是要重新安排到未來某天晚上8點？",
        "rule": "用戶說「過期日期 + 新時間」可能是兩種意圖：(1) 修正歷史記錄 (2) 想重新安排但說錯日期 → 必須詢問",
        "WRONG": "直接 update_schedule(start_time='2026-03-15T20:00:00') 不確認意圖",
    },
    {
        "scenario": "明確說「改到未來」的過期行程",
        "user_message": "把三月十五的開會改到下禮拜五",
        "context": {
            "schedule_list": [
                {"id": "p13", "title": "開會", "start_time": "2026-03-15T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_action": "ask_user",
        "expected_question": "下禮拜五幾點？",
        "rule": "用戶明確說「改到 [未來時間]」→ 接受未來，但缺具體時間時追問",
    },
]

RAG_PAST_SCHEDULE_EN = [
    {
        "scenario": "Edit past schedule - user only says time, needs date",
        "user_message": "Change yesterday's meeting to 3pm",
        "context": {
            "schedule_list": [
                {"id": "abc", "title": "Meeting", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_action": "ask_user",
        "expected_question": "The original schedule has passed. Which day's 3pm do you want?",
        "rule": "Past schedule + only time → ask for future date, don't preserve past date",
    },
    {
        "scenario": "Edit past schedule - user provides full future time",
        "user_message": "Move yesterday's meeting to next Friday 3pm",
        "context": {
            "schedule_list": [
                {"id": "abc", "title": "Meeting", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": True,
        "expected_action": "update_schedule",
        "parsed_data": {"schedule_id": "abc", "start_time": "2026-05-15T15:00:00"},
    },
    {
        "scenario": "Reschedule past event with vague time",
        "user_message": "Reschedule last week's lunch to next week",
        "context": {
            "schedule_list": [
                {"id": "l1", "title": "Lunch", "start_time": "2026-05-02T12:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_question": "Which day next week and what time?",
    },
    {
        "scenario": "User says 'redo' past event - should be CREATE not EDIT",
        "user_message": "Let's do that lunch with Mike again",
        "context": {
            "schedule_list": [
                {"id": "p1", "title": "Lunch with Mike", "start_time": "2026-05-02T12:00:00", "location": "Din Tai Fung"}
            ]
        },
        "intent": "create",
        "is_complete": False,
        "expected_question": "When? Same place (Din Tai Fung)?",
        "rule": "'do again/redo' = new schedule copying old settings, NOT edit",
    },
    {
        "scenario": "Time would be in the past today",
        "user_message": "Change today's 3pm meeting to 9am",
        "context": {
            "current_time": "2026-05-09T14:00:00",
            "schedule_list": [
                {"id": "t1", "title": "Meeting", "start_time": "2026-05-09T15:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_question": "Today's 9am has already passed. Did you mean tomorrow 9am?",
        "rule": "If new time would also be past → confirm with user",
    },
    {
        "scenario": "Delete past schedule - safe to delete",
        "user_message": "Delete yesterday's meeting",
        "context": {
            "schedule_list": [
                {"id": "d1", "title": "Meeting", "start_time": "2026-05-08T10:00:00"}
            ]
        },
        "intent": "delete",
        "is_complete": True,
    },
    {
        "scenario": "User specifies past date as new time - likely typo",
        "user_message": "Move the meeting to May 1, 3pm",
        "context": {
            "schedule_list": [
                {"id": "f1", "title": "Meeting", "start_time": "2026-05-15T10:00:00"}
            ]
        },
        "intent": "edit",
        "is_complete": False,
        "expected_question": "May 1 has already passed. Did you mean June 1 or another date?",
        "rule": "User specifies explicit past date → confirm, may be typo",
    },
]


def stats():
    print(f"Past schedule examples: zh={len(RAG_PAST_SCHEDULE_ZH)}, en={len(RAG_PAST_SCHEDULE_EN)}")


if __name__ == "__main__":
    stats()
