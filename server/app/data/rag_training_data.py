"""
RAG Training Dataset for Schedule Assistant
完整情境覆盖：创建/修改/删除/查询/边界案例

每个样本包含：
- user_message: 用户输入
- intent: 意图分类
- expected_action: 预期动作
- parsed_data: 解析结果
- context: 上下文（可选）
- explanation: 决策理由
"""

from datetime import datetime, timedelta

# 假设 today = 2026-05-08 (周五)
TODAY = "2026-05-08"

RAG_TRAINING_DATA = [
    # ========================================================================
    # 类别 1: 创建行程 - 完整信息（is_complete=True）
    # ========================================================================
    {
        "category": "create_complete",
        "user_message": "明天下午3點在台北101跟小明開會",
        "intent": "create",
        "expected_action": "create_schedule",
        "parsed_data": {
            "title": "與小明開會",
            "start_time": "2026-05-09T15:00:00",
            "end_time": "2026-05-09T17:00:00",
            "location": "台北101",
            "participants": ["@小明"]
        },
        "is_complete": True,
        "explanation": "时间(明天15:00) + 地点(台北101) + 人员(@小明) + 活动(开会) 完整"
    },
    {
        "category": "create_complete",
        "user_message": "後天晚上7點跟朋友在信義區吃飯",
        "intent": "create",
        "expected_action": "create_schedule",
        "parsed_data": {
            "title": "與朋友吃飯",
            "start_time": "2026-05-10T19:00:00",
            "end_time": "2026-05-10T21:00:00",
            "location": "信義區",
            "participants": []
        },
        "is_complete": True,
        "explanation": "「朋友」非具体联系人不加 participants，仅放入 title"
    },
    {
        "category": "create_complete",
        "user_message": "下週一早上9點公司晨會",
        "intent": "create",
        "expected_action": "create_schedule",
        "parsed_data": {
            "title": "公司晨會",
            "start_time": "2026-05-11T09:00:00",
            "end_time": "2026-05-11T10:00:00",
            "location": "公司",
            "participants": []
        },
        "is_complete": True,
        "explanation": "公司是地点，晨会1小时"
    },
    {
        "category": "create_complete",
        "user_message": "今天下午4點打籃球",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {
            "title": "打籃球",
            "start_time": "2026-05-08T16:00:00",
            "end_time": "2026-05-08T18:00:00",
            "participants": []
        },
        "is_complete": False,
        "missing": ["location"],
        "explanation": "运动类必须有地点，缺地点要 ask_user"
    },
    {
        "category": "create_complete",
        "user_message": "明天中午跟同事吃午餐",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {
            "title": "與同事吃午餐",
            "start_time": "2026-05-09T12:00:00",
            "end_time": "2026-05-09T13:00:00",
            "participants": []
        },
        "is_complete": False,
        "missing": ["location"],
        "explanation": "中午→12:00，吃饭需要地点"
    },

    # ========================================================================
    # 类别 2: 创建行程 - 缺信息
    # ========================================================================
    {
        "category": "create_partial",
        "user_message": "明天開會",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {
            "title": "開會",
            "start_time": "2026-05-09T09:00:00"
        },
        "is_complete": False,
        "missing": ["location", "time_specific"],
        "question": "請問幾點開會？地點在哪？",
        "explanation": "开会推断默认09:00，需补地点"
    },
    {
        "category": "create_partial",
        "user_message": "下午跟阿明喝咖啡",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {
            "title": "與阿明喝咖啡",
            "start_time": "2026-05-08T14:00:00",
            "participants": ["@阿明"]
        },
        "is_complete": False,
        "missing": ["location"],
        "question": "請問在哪裡喝咖啡？",
        "explanation": "下午→14:00 默认，缺地点"
    },
    {
        "category": "create_partial",
        "user_message": "禮拜五跟家人聚餐",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {
            "title": "與家人聚餐",
            "start_time": "2026-05-15T19:00:00",
            "participants": []
        },
        "is_complete": False,
        "missing": ["location"],
        "explanation": "聚餐→19:00默认，下周五"
    },

    # ========================================================================
    # 类别 3: 时间表达解析
    # ========================================================================
    {
        "category": "time_parsing",
        "user_message": "明天",
        "parsed_time": "2026-05-09",
        "explanation": "今天+1天"
    },
    {
        "category": "time_parsing",
        "user_message": "後天",
        "parsed_time": "2026-05-10",
        "explanation": "今天+2天"
    },
    {
        "category": "time_parsing",
        "user_message": "大後天",
        "parsed_time": "2026-05-11",
        "explanation": "今天+3天"
    },
    {
        "category": "time_parsing",
        "user_message": "下禮拜一",
        "parsed_time": "2026-05-11",
        "explanation": "下周一（今天周五，下周一+3天）"
    },
    {
        "category": "time_parsing",
        "user_message": "這禮拜六",
        "parsed_time": "2026-05-09",
        "explanation": "本周六（今天周五，明天就是周六）"
    },
    {
        "category": "time_parsing",
        "user_message": "下週五",
        "parsed_time": "2026-05-15",
        "explanation": "下周五"
    },
    {
        "category": "time_parsing",
        "user_message": "三天後",
        "parsed_time": "2026-05-11",
        "explanation": "今天+3天"
    },
    {
        "category": "time_parsing",
        "user_message": "下午三點",
        "parsed_time": "T15:00:00",
        "explanation": "下午3点 = 15:00"
    },
    {
        "category": "time_parsing",
        "user_message": "晚上七點半",
        "parsed_time": "T19:30:00",
        "explanation": "晚上7点半 = 19:30"
    },
    {
        "category": "time_parsing",
        "user_message": "傍晚",
        "parsed_time": "T17:00:00",
        "explanation": "傍晚默认17:00"
    },
    {
        "category": "time_parsing",
        "user_message": "凌晨兩點",
        "parsed_time": "T02:00:00",
        "explanation": "凌晨2点 = 02:00"
    },
    {
        "category": "time_parsing",
        "user_message": "中午12點",
        "parsed_time": "T12:00:00",
        "explanation": "中午12点"
    },
    {
        "category": "time_parsing",
        "user_message": "5月20號下午4點",
        "parsed_time": "2026-05-20T16:00:00",
        "explanation": "明确日期+时间"
    },
    {
        "category": "time_parsing",
        "user_message": "兩小時後",
        "parsed_time": "now+2h",
        "explanation": "相对当前时间+2小时"
    },

    # ========================================================================
    # 类别 4: 修改行程 (edit)
    # ========================================================================
    {
        "category": "edit",
        "user_message": "把開會改到下午4點",
        "intent": "edit",
        "context": {
            "schedule_list": [
                {"id": "abc-123", "title": "開會", "start_time": "2026-05-09T09:00:00"}
            ]
        },
        "expected_action": "update_schedule",
        "parsed_data": {
            "schedule_id": "abc-123",
            "start_time": "2026-05-09T16:00:00"
        },
        "explanation": "明确指出要改的对象和新值，仅更新 start_time（保留原日期）"
    },
    {
        "category": "edit",
        "user_message": "跟小明吃飯改到星巴克",
        "intent": "edit",
        "context": {
            "schedule_list": [
                {"id": "xyz", "title": "與小明吃飯", "location": "麥當勞"}
            ]
        },
        "expected_action": "update_schedule",
        "parsed_data": {
            "schedule_id": "xyz",
            "location": "星巴克"
        },
        "explanation": "仅修改 location，不动其他字段"
    },
    {
        "category": "edit",
        "user_message": "加上 @小美",
        "intent": "edit",
        "context": {
            "_pending_edit_schedule_id": "abc",
            "schedule_list": [{"id": "abc", "title": "聚餐", "participants": ["@小明"]}]
        },
        "expected_action": "update_schedule",
        "parsed_data": {
            "schedule_id": "abc",
            "participants": ["@小美"]
        },
        "explanation": "添加新参与者，不替换现有列表"
    },
    {
        "category": "edit",
        "user_message": "移除 @小明",
        "intent": "edit",
        "context": {
            "schedule_list": [{"id": "abc", "title": "聚餐", "participants": ["@小明", "@小美"]}]
        },
        "expected_action": "update_schedule",
        "parsed_data": {
            "schedule_id": "abc",
            "remove_participants": ["@小明"]
        },
        "explanation": "用 remove_participants 而非 participants"
    },
    {
        "category": "edit",
        "user_message": "把所有人都移除",
        "intent": "edit",
        "expected_action": "update_schedule",
        "parsed_data": {
            "clear_participants": True
        },
        "explanation": "全清用 clear_participants=true"
    },
    {
        "category": "edit",
        "user_message": "改成晚一點",
        "intent": "edit",
        "expected_action": "ask_user",
        "question": "請問改到幾點？",
        "explanation": "「晚一点」太模糊，需追问具体时间"
    },
    {
        "category": "edit",
        "user_message": "改成9點",
        "intent": "edit",
        "context": {
            "schedule_list": [{"id": "abc", "title": "開會", "start_time": "2026-05-09T15:00:00"}]
        },
        "expected_action": "update_schedule",
        "parsed_data": {
            "schedule_id": "abc",
            "start_time": "2026-05-09T09:00:00"
        },
        "explanation": "保留原日期 2026-05-09，仅替换时间为 09:00"
    },

    # ========================================================================
    # 类别 5: 删除行程 (delete)
    # ========================================================================
    {
        "category": "delete",
        "user_message": "刪除開會",
        "intent": "delete",
        "context": {
            "schedule_list": [{"id": "abc", "title": "開會"}]
        },
        "expected_action": "delete_schedule",
        "parsed_data": {"schedule_id": "abc"},
        "explanation": "唯一匹配，直接删除"
    },
    {
        "category": "delete",
        "user_message": "取消明天的會議",
        "intent": "delete",
        "expected_action": "delete_schedule",
        "explanation": "「取消」也是 delete 意图"
    },
    {
        "category": "delete",
        "user_message": "我不去了",
        "intent": "delete",
        "expected_action": "ask_user",
        "question": "請問要取消哪個行程？",
        "explanation": "上下文不清，需追问"
    },
    {
        "category": "delete",
        "user_message": "刪除跟小明的所有行程",
        "intent": "delete",
        "context": {
            "schedule_list": [
                {"id": "a", "title": "與小明吃飯"},
                {"id": "b", "title": "與小明開會"}
            ]
        },
        "expected_action": "ask_user",
        "question": "您有 2 筆與小明相關的行程：\n1️⃣ 與小明吃飯\n2️⃣ 與小明開會\n\n要全部刪除還是某一筆？",
        "explanation": "多筆匹配，必须列出让用户选"
    },

    # ========================================================================
    # 类别 6: 查询行程 (query)
    # ========================================================================
    {
        "category": "query",
        "user_message": "我有什麼行程",
        "intent": "query",
        "expected_action": "reply_to_user",
        "explanation": "查询全部行程"
    },
    {
        "category": "query",
        "user_message": "明天有什麼安排",
        "intent": "query",
        "expected_action": "reply_to_user",
        "explanation": "查询特定日期"
    },
    {
        "category": "query",
        "user_message": "幾點開會",
        "intent": "query",
        "expected_action": "reply_to_user",
        "explanation": "查询特定行程时间"
    },

    # ========================================================================
    # 类别 7: 同名联系人处理
    # ========================================================================
    {
        "category": "duplicate_contact",
        "user_message": "明天跟小明吃飯",
        "context": {
            "duplicate_contacts": [
                {"name": "小明", "comment": "同事", "phone_last4": "1234"},
                {"name": "小明", "comment": "朋友", "phone_last4": "5678"}
            ]
        },
        "expected_action": "ask_user",
        "question": "您說的 @小明 是哪一位？\n1️⃣ 小明（同事）— 末4碼 1234\n2️⃣ 小明（朋友）— 末4碼 5678\n請回覆數字或備註區分。",
        "explanation": "同名必须先 ask_user，不可猜测"
    },
    {
        "category": "duplicate_contact",
        "user_message": "1",
        "context": {
            "_previous_question": "您說的 @小明 是哪一位？",
            "_pending_duplicate": "小明"
        },
        "expected_action": "continue_create",
        "explanation": "用户回数字选择，使用对应的联系人"
    },

    # ========================================================================
    # 类别 8: 在线会议
    # ========================================================================
    {
        "category": "online_meeting",
        "user_message": "明天下午3點線上會議",
        "intent": "create",
        "expected_action": "create_schedule",
        "parsed_data": {
            "title": "線上會議",
            "start_time": "2026-05-09T15:00:00",
            "is_online": True
        },
        "is_complete": True,
        "explanation": "is_online=True 不需 location"
    },
    {
        "category": "online_meeting",
        "user_message": "明天Zoom開會跟團隊",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {
            "title": "團隊Zoom開會",
            "is_online": True,
            "participants": []
        },
        "is_complete": False,
        "missing": ["start_time", "participants_specific"],
        "explanation": "线上会议但缺时间"
    },

    # ========================================================================
    # 类别 9: 服务范围外
    # ========================================================================
    {
        "category": "out_of_scope",
        "user_message": "今天天氣怎樣",
        "expected_action": "reply_to_user",
        "reply": "我是行程規劃助理，專門幫您安排、修改和管理行程 📅 請問您有什麼行程需要規劃嗎？",
        "explanation": "非行程相关，回复固定引导语"
    },
    {
        "category": "out_of_scope",
        "user_message": "推薦一首歌",
        "expected_action": "reply_to_user",
        "reply": "我是行程規劃助理，專門幫您安排、修改和管理行程 📅 請問您有什麼行程需要規劃嗎？",
        "explanation": "非行程相关"
    },
    {
        "category": "out_of_scope",
        "user_message": "你好",
        "expected_action": "reply_to_user",
        "reply": "您好！我是行程規劃助理，請問有什麼行程需要規劃嗎？",
        "explanation": "问候简短回应+引导语"
    },

    # ========================================================================
    # 类别 10: 复杂边界场景
    # ========================================================================
    {
        "category": "edge_case",
        "user_message": "明天跟小哈找明明吃飯下午五點在小哈家",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {
            "title": "與小哈、明明吃飯",
            "start_time": "2026-05-09T17:00:00",
            "participants": ["@小哈", "@明明"]
        },
        "is_complete": False,
        "missing": ["location"],
        "explanation": "「小哈家」不可作 location，需 ask_user 确认地址"
    },
    {
        "category": "edge_case",
        "user_message": "下個月15號要去機場",
        "intent": "create",
        "expected_action": "ask_user",
        "parsed_data": {
            "title": "去機場",
            "start_time": "2026-06-15T09:00:00"
        },
        "is_complete": False,
        "missing": ["location_specific", "time_specific"],
        "explanation": "需问哪个机场及时间"
    },
    {
        "category": "edge_case",
        "user_message": "改星巴克",
        "intent": "edit",
        "expected_action": "ask_user",
        "question": "您要修改哪個行程的地點？",
        "explanation": "缺修改对象，需追问"
    },
    {
        "category": "edge_case",
        "user_message": "再加一個",
        "expected_action": "ask_user",
        "question": "請問要新增什麼行程？",
        "explanation": "意图不清"
    },
    {
        "category": "edge_case",
        "user_message": "嗯",
        "expected_action": "reply_to_user",
        "explanation": "无意义输入，简短回应"
    },

    # ========================================================================
    # 类别 11: Title 推断规则
    # ========================================================================
    {
        "category": "title_inference",
        "user_message": "明天去吃飯",
        "title": "聚餐",
        "explanation": "无人名→「聚餐」"
    },
    {
        "category": "title_inference",
        "user_message": "明天跟小明吃飯",
        "title": "與小明吃飯",
        "explanation": "有人名→「與X吃飯」"
    },
    {
        "category": "title_inference",
        "user_message": "明天看電影",
        "title": "看電影",
        "explanation": "活动名直接用"
    },
    {
        "category": "title_inference",
        "user_message": "下午跑步",
        "title": "跑步",
        "explanation": "运动用活动名"
    },
    {
        "category": "title_inference",
        "user_message": "明天跟客戶在君悅酒店談生意",
        "title": "與客戶談生意",
        "location": "君悅酒店",
        "explanation": "title 不含地点"
    },
    {
        "category": "title_inference",
        "user_message": "明天去看醫生",
        "title": "看診",
        "explanation": "看医生→看诊"
    },

    # ========================================================================
    # 类别 12: 多欄位同時修改
    # ========================================================================
    {
        "category": "multi_edit",
        "user_message": "改成9點，地點換星巴克",
        "intent": "edit",
        "expected_action": "update_schedule",
        "parsed_data": {
            "start_time": "..T09:00:00",
            "location": "星巴克"
        },
        "explanation": "一次 update 带所有变更"
    },
    {
        "category": "multi_edit",
        "user_message": "把開會改到後天下午2點台北101",
        "intent": "edit",
        "expected_action": "update_schedule",
        "parsed_data": {
            "start_time": "2026-05-10T14:00:00",
            "location": "台北101"
        },
        "explanation": "时间+地点同时改"
    },

    # ========================================================================
    # 类别 13: 连锁品牌处理
    # ========================================================================
    {
        "category": "chain_store",
        "user_message": "明天3點在星巴克開會",
        "location": "星巴克",
        "explanation": "连锁品牌直接用品牌名，地点验证系统自动找最近分店"
    },
    {
        "category": "chain_store",
        "user_message": "下午去麥當勞",
        "location": "麥當勞",
        "explanation": "不可追问「哪家分店？」"
    },

    # ========================================================================
    # 类别 14: 上下文记忆
    # ========================================================================
    {
        "category": "context_memory",
        "user_message": "晚上7點",
        "context": {
            "_pending_question": "請問幾點開始？",
            "_collecting": {"title": "與小明吃飯", "location": "信義區"}
        },
        "expected_action": "create_schedule",
        "parsed_data": {
            "title": "與小明吃飯",
            "start_time": "..T19:00:00",
            "location": "信義區"
        },
        "explanation": "用户补全时间，结合已收集信息创建"
    },
    {
        "category": "context_memory",
        "user_message": "對",
        "context": {
            "_pending_confirmation": "確認在台北101開會？"
        },
        "expected_action": "create_schedule",
        "explanation": "肯定回应执行待定操作"
    },

    # ========================================================================
    # 类别 15: 否定/取消修改
    # ========================================================================
    {
        "category": "cancel_action",
        "user_message": "算了",
        "context": {"_pending_action": "create"},
        "expected_action": "reply_to_user",
        "reply": "好的，已取消。",
        "explanation": "用户放弃，不执行"
    },
    {
        "category": "cancel_action",
        "user_message": "不用了",
        "expected_action": "reply_to_user",
        "explanation": "类似「算了」"
    },

    # ========================================================================
    # 类别 16: 重复检测
    # ========================================================================
    {
        "category": "duplicate_check",
        "user_message": "明天下午3點開會",
        "context": {
            "schedule_list": [
                {"id": "abc", "title": "開會", "start_time": "2026-05-09T15:00:00"}
            ]
        },
        "expected_action": "ask_user",
        "question": "您明天下午3點已有「開會」行程，要建立新的還是修改原有的？",
        "explanation": "时间冲突需确认"
    },

    # ========================================================================
    # 类别 17: 跨日处理
    # ========================================================================
    {
        "category": "overnight",
        "user_message": "明天晚上11點半到後天凌晨2點 KTV",
        "intent": "create",
        "expected_action": "create_schedule",
        "parsed_data": {
            "title": "KTV",
            "start_time": "2026-05-09T23:30:00",
            "end_time": "2026-05-10T02:00:00",
            "location": "KTV"
        },
        "is_complete": True,
        "explanation": "跨日行程 end_time 转下一天"
    },

    # ========================================================================
    # 类别 18: 带描述/备注
    # ========================================================================
    {
        "category": "with_description",
        "user_message": "明天3點開會討論Q2業績",
        "intent": "create",
        "parsed_data": {
            "title": "開會",
            "description": "討論Q2業績",
            "start_time": "2026-05-09T15:00:00"
        },
        "explanation": "「讨论X」放 description，不放 title"
    },

    # ========================================================================
    # 类别 19: 提醒类
    # ========================================================================
    {
        "category": "reminder",
        "user_message": "提醒我明天3點要開會",
        "intent": "create",
        "expected_action": "create_schedule",
        "explanation": "「提醒我」也是创建行程"
    },

    # ========================================================================
    # 类别 20: 重复行程
    # ========================================================================
    {
        "category": "recurring",
        "user_message": "每週一早上9點開會",
        "intent": "create",
        "expected_action": "ask_user",
        "question": "目前不支持自動重複建立，要先建立下週一9點的開會嗎？",
        "explanation": "重复行程需特殊处理"
    },
]


def get_examples_by_category(category: str, limit: int = 5):
    """根据类别获取示例"""
    return [ex for ex in RAG_TRAINING_DATA if ex.get("category") == category][:limit]


def get_examples_by_intent(intent: str, limit: int = 5):
    """根据意图获取示例"""
    return [ex for ex in RAG_TRAINING_DATA if ex.get("intent") == intent][:limit]


def get_all_categories():
    """所有类别清单"""
    return list(set(ex.get("category", "unknown") for ex in RAG_TRAINING_DATA))


if __name__ == "__main__":
    print(f"Total examples: {len(RAG_TRAINING_DATA)}")
    print(f"\nCategories:")
    cats = {}
    for ex in RAG_TRAINING_DATA:
        cat = ex.get("category", "unknown")
        cats[cat] = cats.get(cat, 0) + 1
    for cat, count in sorted(cats.items()):
        print(f"  {cat:25s}: {count}")
