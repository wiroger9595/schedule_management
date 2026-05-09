"""
RAG Training Dataset V2 - Extended Examples
更多真实场景和口语表达变体

重点扩展：
- 真实用户口语
- 各种活动类型
- 复杂修改/删除场景
- 错误模式纠正
- 多轮对话
"""

TODAY = "2026-05-08"  # Friday

RAG_TRAINING_DATA_V2 = [

    # ========================================================================
    # A. 餐饮类 - 各种用语
    # ========================================================================
    {
        "scenario": "早餐场景",
        "user_message": "明天早上8點吃早餐",
        "title": "早餐", "start_time": "2026-05-09T08:00:00",
        "duration_default": "1h",
        "needs_location": True
    },
    {
        "scenario": "早午餐 (brunch)",
        "user_message": "禮拜六早午餐",
        "title": "早午餐", "start_time": "2026-05-09T11:00:00",
        "explanation": "早午餐默认11:00"
    },
    {
        "scenario": "下午茶",
        "user_message": "下午茶時間找小美",
        "title": "與小美下午茶", "start_time": "2026-05-08T15:00:00",
        "participants": ["@小美"]
    },
    {
        "scenario": "宵夜",
        "user_message": "今晚10點吃宵夜",
        "title": "宵夜", "start_time": "2026-05-08T22:00:00"
    },
    {
        "scenario": "跨年聚餐",
        "user_message": "12/31跨年聚餐",
        "title": "跨年聚餐", "start_time": "2026-12-31T19:00:00"
    },
    {
        "scenario": "尾牙",
        "user_message": "下個月公司尾牙",
        "title": "公司尾牙",
        "needs_specific_time": True
    },
    {
        "scenario": "婚禮",
        "user_message": "下個月15號小明結婚",
        "title": "小明婚禮", "start_time": "2026-06-15T12:00:00",
        "explanation": "婚礼默认中午"
    },

    # ========================================================================
    # B. 工作类
    # ========================================================================
    {
        "scenario": "面試",
        "user_message": "下午3點Google面試",
        "title": "Google面試", "start_time": "2026-05-08T15:00:00",
        "needs_location": True
    },
    {
        "scenario": "簡報",
        "user_message": "週三早上做簡報",
        "title": "簡報", "start_time": "2026-05-13T09:00:00"
    },
    {
        "scenario": "客戶拜訪",
        "user_message": "明天去拜訪客戶王董",
        "title": "拜訪客戶王董", "start_time": "2026-05-09T09:00:00",
        "needs_location": True
    },
    {
        "scenario": "電話會議",
        "user_message": "下午4點電話會議",
        "title": "電話會議", "start_time": "2026-05-08T16:00:00",
        "is_online": True
    },
    {
        "scenario": "出差",
        "user_message": "下週去高雄出差",
        "title": "高雄出差",
        "location": "高雄",
        "needs_specific_date": True
    },
    {
        "scenario": "1對1會議",
        "user_message": "明天跟主管1on1",
        "title": "與主管1on1",
        "participants": ["@主管"],
        "needs_specific_time": True
    },
    {
        "scenario": "週會",
        "user_message": "禮拜一週會",
        "title": "週會", "start_time": "2026-05-11T09:00:00",
        "is_recurring_hint": True
    },

    # ========================================================================
    # C. 运动健身
    # ========================================================================
    {
        "scenario": "瑜伽",
        "user_message": "明天早上7點瑜伽",
        "title": "瑜伽", "start_time": "2026-05-09T07:00:00",
        "needs_location": True
    },
    {
        "scenario": "跑步",
        "user_message": "下午6點河濱公園跑步",
        "title": "跑步", "location": "河濱公園",
        "start_time": "2026-05-08T18:00:00"
    },
    {
        "scenario": "健身房",
        "user_message": "晚上8點健身房",
        "title": "健身", "location": "健身房",
        "start_time": "2026-05-08T20:00:00"
    },
    {
        "scenario": "游泳",
        "user_message": "禮拜六中午游泳",
        "title": "游泳", "start_time": "2026-05-09T12:00:00",
        "needs_location": True
    },
    {
        "scenario": "羽毛球",
        "user_message": "明天下午跟同事打羽球",
        "title": "與同事打羽球",
        "start_time": "2026-05-09T15:00:00",
        "needs_location": True
    },

    # ========================================================================
    # D. 娛樂休閒
    # ========================================================================
    {
        "scenario": "看電影",
        "user_message": "今晚看電影",
        "title": "看電影", "start_time": "2026-05-08T19:00:00",
        "needs_location": True
    },
    {
        "scenario": "演唱會",
        "user_message": "5月20號周杰倫演唱會",
        "title": "周杰倫演唱會",
        "start_time": "2026-05-20T19:00:00",
        "needs_location": True
    },
    {
        "scenario": "逛街",
        "user_message": "明天去信義逛街",
        "title": "逛街", "location": "信義區",
        "start_time": "2026-05-09T14:00:00"
    },
    {
        "scenario": "KTV",
        "user_message": "晚上唱歌",
        "title": "KTV", "start_time": "2026-05-08T21:00:00",
        "needs_location": True
    },
    {
        "scenario": "爬山",
        "user_message": "禮拜天跟朋友爬象山",
        "title": "爬象山", "location": "象山",
        "start_time": "2026-05-10T09:00:00"
    },
    {
        "scenario": "看展",
        "user_message": "下週末看展覽",
        "title": "看展覽",
        "needs_specific_date": True
    },

    # ========================================================================
    # E. 醫療健康
    # ========================================================================
    {
        "scenario": "看牙醫",
        "user_message": "明天下午2點看牙醫",
        "title": "看牙醫", "start_time": "2026-05-09T14:00:00",
        "needs_location": True
    },
    {
        "scenario": "體檢",
        "user_message": "下週四早上體檢",
        "title": "體檢", "start_time": "2026-05-14T09:00:00",
        "needs_location": True
    },
    {
        "scenario": "預約掛號",
        "user_message": "禮拜五心臟內科掛號",
        "title": "心臟內科掛號",
        "start_time": "2026-05-15T09:00:00",
        "needs_location": True
    },

    # ========================================================================
    # F. 旅遊出行
    # ========================================================================
    {
        "scenario": "搭飛機",
        "user_message": "下週二早上8點桃園機場搭飛機",
        "title": "搭飛機", "location": "桃園機場",
        "start_time": "2026-05-12T08:00:00"
    },
    {
        "scenario": "高鐵",
        "user_message": "明天下午2點高鐵到台中",
        "title": "高鐵到台中",
        "start_time": "2026-05-09T14:00:00"
    },
    {
        "scenario": "出國",
        "user_message": "下個月去日本旅遊",
        "title": "日本旅遊",
        "needs_specific_date": True
    },

    # ========================================================================
    # G. 重要模糊场景 - 必须 ask_user
    # ========================================================================
    {
        "scenario": "缺所有信息",
        "user_message": "幫我安排個行程",
        "expected_action": "ask_user",
        "question": "請問要建立什麼行程？提供時間、地點和活動內容。"
    },
    {
        "scenario": "只有活动",
        "user_message": "想吃飯",
        "expected_action": "ask_user",
        "question": "請問什麼時候、跟誰、在哪裡吃飯？"
    },
    {
        "scenario": "只有时间",
        "user_message": "明天下午",
        "expected_action": "ask_user",
        "question": "請問明天下午要做什麼？"
    },
    {
        "scenario": "只有地点",
        "user_message": "在台北101",
        "expected_action": "ask_user",
        "question": "請問在台北101要做什麼？什麼時候？"
    },
    {
        "scenario": "歧义时间",
        "user_message": "晚一點開會",
        "expected_action": "ask_user",
        "question": "請問幾點開會？"
    },

    # ========================================================================
    # H. 多轮对话场景
    # ========================================================================
    {
        "scenario": "首轮缺时间",
        "turn1_user": "明天跟小明吃飯",
        "turn1_response": "請問幾點、在哪裡？",
        "turn1_partial": {"title": "與小明吃飯", "participants": ["@小明"]},
        "turn2_user": "晚上7點信義區",
        "expected_final": {
            "title": "與小明吃飯",
            "start_time": "2026-05-09T19:00:00",
            "location": "信義區",
            "participants": ["@小明"]
        }
    },
    {
        "scenario": "首轮缺地点",
        "turn1_user": "下週五晚上6點打球",
        "turn1_response": "請問去哪裡打球？",
        "turn1_partial": {
            "title": "打球",
            "start_time": "2026-05-15T18:00:00"
        },
        "turn2_user": "天母運動中心",
        "expected_final": {
            "title": "打球",
            "start_time": "2026-05-15T18:00:00",
            "location": "天母運動中心"
        }
    },
    {
        "scenario": "用户改变主意",
        "turn1_user": "明天3點開會",
        "turn1_response": "好的，請問地點？",
        "turn2_user": "改成4點吧",
        "expected_action": "update_partial_data",
        "explanation": "建立中途修改时间，更新 partial_data 而非 update_schedule"
    },

    # ========================================================================
    # I. 错误识别 - 不该做的
    # ========================================================================
    {
        "scenario": "禁止：复制旧 location 到 update",
        "context": {
            "_pending_edit_schedule_id": "abc",
            "_collecting": {"location": "建國高架籃球場"}
        },
        "user_message": "改成後天11點",
        "WRONG": {"start_time": "...", "location": "建國高架籃球場"},
        "CORRECT": {"schedule_id": "abc", "start_time": "..."},
        "explanation": "只更新明确提到的字段"
    },
    {
        "scenario": "禁止：建立中用 update_schedule",
        "context": {
            "_collecting": {"title": "與小哈吃飯"}
        },
        "user_message": "晚上10點",
        "WRONG": {"action": "update_schedule"},
        "CORRECT": {"action": "ask_user", "partial_data": {"title": "...", "start_time": "..T22:00"}},
        "explanation": "建立中只能用 ask_user 或 create_schedule"
    },
    {
        "scenario": "禁止：title 含地点",
        "user_message": "明天去星巴克喝咖啡",
        "WRONG": {"title": "去星巴克喝咖啡"},
        "CORRECT": {"title": "喝咖啡", "location": "星巴克"}
    },
    {
        "scenario": "禁止：用联络人当地点",
        "user_message": "明天去小明家",
        "WRONG": {"location": "小明家"},
        "CORRECT": {"action": "ask_user", "question": "請問小明家的地址？"}
    },
    {
        "scenario": "禁止：多筆符合时自行猜测",
        "user_message": "把跟小明的改成晚上8點",
        "context": {
            "schedule_list": [
                {"id": "a", "title": "與小明吃飯"},
                {"id": "b", "title": "與小明開會"}
            ]
        },
        "WRONG": {"action": "update_schedule", "schedule_id": "a"},
        "CORRECT": {"action": "ask_user", "options": ["1️⃣ 與小明吃飯", "2️⃣ 與小明開會"]}
    },

    # ========================================================================
    # J. 时间表达增强 (台语/口语)
    # ========================================================================
    {"expression": "明仔載", "meaning": "tomorrow", "parsed": "2026-05-09"},
    {"expression": "後日", "meaning": "day after tomorrow", "parsed": "2026-05-10"},
    {"expression": "頂禮拜", "meaning": "last week", "parsed": "previous week"},
    {"expression": "下禮拜", "meaning": "next week", "parsed": "next week"},
    {"expression": "今早", "meaning": "this morning", "parsed": "today T09:00"},
    {"expression": "今暝", "meaning": "tonight", "parsed": "today T19:00"},
    {"expression": "ㄉㄢ ㄉㄢ", "meaning": "等等 (later)", "parsed": "in 1-2 hours"},

    # ========================================================================
    # K. 数字时间格式
    # ========================================================================
    {"input": "15:00", "parsed": "T15:00:00"},
    {"input": "3:00pm", "parsed": "T15:00:00"},
    {"input": "下午三點", "parsed": "T15:00:00"},
    {"input": "下午15點", "parsed": "T15:00:00", "explanation": "口语「下午15点」≈下午3点"},
    {"input": "晚上8:30", "parsed": "T20:30:00"},
    {"input": "20:30", "parsed": "T20:30:00"},
    {"input": "晚上8點半", "parsed": "T20:30:00"},

    # ========================================================================
    # L. 持续时间
    # ========================================================================
    {
        "scenario": "明确持续时间",
        "user_message": "下午2點到4點開會",
        "start_time": "2026-05-08T14:00:00",
        "end_time": "2026-05-08T16:00:00"
    },
    {
        "scenario": "持续半天",
        "user_message": "週六上午健行",
        "start_time": "2026-05-09T09:00:00",
        "end_time": "2026-05-09T12:00:00"
    },
    {
        "scenario": "全天",
        "user_message": "下週一全天會議",
        "start_time": "2026-05-11T09:00:00",
        "end_time": "2026-05-11T18:00:00"
    },

    # ========================================================================
    # M. 修改时间 - 仅时间不动日期
    # ========================================================================
    {
        "scenario": "保留原日期",
        "context": {
            "schedule_list": [{"id": "abc", "start_time": "2027-04-09T15:00:00"}]
        },
        "user_message": "改成9點",
        "CORRECT": {"start_time": "2027-04-09T09:00:00"},
        "WRONG": {"start_time": f"{TODAY}T09:00:00"},
        "explanation": "保留原始日期，只换时间部分"
    },
    {
        "scenario": "保留原時間改日期",
        "context": {
            "schedule_list": [{"id": "abc", "start_time": "2027-04-09T15:00:00"}]
        },
        "user_message": "改成5月20號",
        "CORRECT": {"start_time": "2027-05-20T15:00:00"},
        "explanation": "保留原始时间 15:00，只换日期"
    },

    # ========================================================================
    # N. 完整对话流示例
    # ========================================================================
    {
        "dialogue_id": "complete_flow_1",
        "turns": [
            {"user": "明天有個會議", "ai_action": "ask_user", "ai_q": "請問幾點？跟誰？地點？"},
            {"user": "下午2點，跟客戶王先生", "ai_partial": {"title": "與客戶王先生會議", "start_time": "2026-05-09T14:00:00", "participants": ["@王先生"]}, "ai_q": "請問地點？"},
            {"user": "我們公司會議室", "ai_action": "create_schedule", "ai_data": {"title": "與客戶王先生會議", "start_time": "2026-05-09T14:00:00", "end_time": "2026-05-09T15:00:00", "location": "公司會議室", "participants": ["@王先生"]}}
        ]
    },
    {
        "dialogue_id": "edit_flow_1",
        "turns": [
            {"user": "我有什麼行程", "ai_action": "reply_to_user", "schedule_list_shown": True},
            {"user": "把開會改晚一點", "ai_action": "ask_user", "ai_q": "請問改到幾點？"},
            {"user": "下午4點", "ai_action": "update_schedule", "ai_data": {"start_time": "...T16:00:00"}}
        ]
    },

    # ========================================================================
    # O. 服务范围外测试 (扩展)
    # ========================================================================
    {"out_of_scope": "計算 100*200", "expected": "redirect"},
    {"out_of_scope": "翻譯這句話", "expected": "redirect"},
    {"out_of_scope": "推薦餐廳", "expected": "redirect"},
    {"out_of_scope": "你叫什麼名字", "expected": "polite_then_redirect"},
    {"out_of_scope": "謝謝", "expected": "polite_short"},
    {"out_of_scope": "再見", "expected": "polite_short"},
]


def stats():
    print(f"V2 Total: {len(RAG_TRAINING_DATA_V2)}")


if __name__ == "__main__":
    stats()
