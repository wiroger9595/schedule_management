"""
RAG Training Dataset V3 - 针对真实失败案例的强化训练数据

基于实际测试失败模式：
1. is_complete 判断错误（不该追问的追问了）
2. intent 分类错误（edit 误判为 create）
3. query 意图识别（"在哪里X" 是查询不是创建）
4. 修改语句识别（"改成X" 必须是 edit）
"""

TODAY = "2026-05-08"

RAG_TRAINING_DATA_V3 = [

    # ========================================================================
    # FIX 1: is_complete=True 判断 - 个人行程不需要 participants
    # ========================================================================
    {
        "scenario": "FIX：完整个人行程不该问参与者",
        "user_message": "下禮拜五上午十點在台北101開會",
        "intent": "create",
        "is_complete": True,  # ⭐ 关键
        "parsed": {
            "title": "開會",
            "start_time": "2026-05-15T10:00:00",
            "end_time": "2026-05-15T11:00:00",
            "location": "台北101",
            "participants": []  # 没说明就是空
        },
        "WRONG_BEHAVIOR": "问「請問是跟誰開會？」",
        "CORRECT_BEHAVIOR": "直接 create_schedule，不问参与者",
        "rule": "用户没提到「跟谁」就是个人行程，participants=[]，不要追问"
    },
    {
        "scenario": "FIX：个人吃饭不需问跟谁",
        "user_message": "明天晚上7點在信義吃飯",
        "intent": "create",
        "is_complete": True,
        "parsed": {
            "title": "吃飯",
            "start_time": "2026-05-09T19:00:00",
            "end_time": "2026-05-09T20:00:00",
            "location": "信義",
            "participants": []
        },
        "rule": "无人名+完整时间地点 → 直接建立"
    },
    {
        "scenario": "FIX：完整资讯应该 is_complete=True",
        "user_message": "後天晚上七點跟朋友吃飯在信義區",
        "intent": "create",
        "is_complete": True,
        "parsed": {
            "title": "吃飯",
            "start_time": "2026-05-10T19:00:00",
            "end_time": "2026-05-10T21:00:00",
            "location": "信義區",
            "participants": []
        },
        "explanation": "「朋友」是泛称非具体联系人，不必加入 participants",
        "rule": "「朋友/同事/家人」非具体名→放 title，不放 participants"
    },

    # ========================================================================
    # FIX 2: edit 意图识别 - "改成"/"换成" 必须是 edit
    # ========================================================================
    {
        "scenario": "FIX：'改成' 必须识别为 edit",
        "user_message": "把開會改成下午四點",
        "intent": "edit",  # ⭐ 不是 create
        "is_complete": False,
        "WRONG_INTENT": "create",
        "CORRECT_INTENT": "edit",
        "rule": "动词「改/改成/改到/换成/调整」+ 既有行程类别 → edit"
    },
    {
        "scenario": "FIX：'改成明天' 必须是 edit",
        "user_message": "改成明天",
        "intent": "edit",  # ⭐
        "is_complete": False,
        "expected_action": "ask_user",
        "question": "您要修改哪個行程？",
        "rule": "「改成」开头 → edit 意图，缺对象需追问"
    },
    {
        "scenario": "FIX：'换地点' 是 edit",
        "user_message": "地點換星巴克",
        "intent": "edit",
        "is_complete": False,
        "rule": "「换/换成」也是 edit"
    },
    {
        "scenario": "FIX：'调整' 是 edit",
        "user_message": "把會議調整到下週",
        "intent": "edit",
        "is_complete": False
    },
    {
        "scenario": "FIX：'移到' 是 edit",
        "user_message": "把吃飯移到禮拜六",
        "intent": "edit",
        "is_complete": False
    },
    {
        "scenario": "FIX：'延後' 是 edit",
        "user_message": "開會延後一小時",
        "intent": "edit",
        "is_complete": False
    },
    {
        "scenario": "FIX：'提前' 是 edit",
        "user_message": "把面試提前到上午",
        "intent": "edit",
        "is_complete": False
    },
    {
        "scenario": "FIX：'取消' 是 delete",
        "user_message": "取消明天的開會",
        "intent": "delete",  # ⭐ 不是 edit
        "rule": "「取消/不要/cancel」→ delete"
    },

    # ========================================================================
    # FIX 3: query 意图识别 - "在哪里X" / "几点X" 是查询
    # ========================================================================
    {
        "scenario": "FIX：'在哪裡X' 是查询",
        "user_message": "在哪裡開會",
        "intent": "query",  # ⭐ 不是 create
        "is_complete": False,
        "WRONG_INTENT": "create",
        "rule": "疑问词「在哪里/什么时候/几点/谁」+ 既有活动 → query 不是 create"
    },
    {
        "scenario": "FIX：'幾點X' 是查询",
        "user_message": "幾點開會",
        "intent": "query",
        "is_complete": False
    },
    {
        "scenario": "FIX：'什麼時候X' 是查询",
        "user_message": "什麼時候吃飯",
        "intent": "query",
        "is_complete": False
    },
    {
        "scenario": "FIX：'跟誰X' 是查询",
        "user_message": "明天跟誰開會",
        "intent": "query",
        "is_complete": False
    },
    {
        "scenario": "FIX：'X 在哪' 是查询",
        "user_message": "今天的會議在哪",
        "intent": "query",
        "is_complete": False
    },
    {
        "scenario": "FIX：'有沒有X' 是查询",
        "user_message": "明天有沒有會議",
        "intent": "query",
        "is_complete": False
    },
    {
        "scenario": "FIX：'X 是几点' 是查询",
        "user_message": "面試是幾點",
        "intent": "query",
        "is_complete": False
    },

    # ========================================================================
    # FIX 4: query 的 is_complete 应该是 False
    # ========================================================================
    {
        "scenario": "FIX：query 的 is_complete=False",
        "user_message": "我有什麼行程",
        "intent": "query",
        "is_complete": False,  # ⭐ query 没有「完成」概念
        "WRONG_COMPLETE": True,
        "rule": "is_complete 仅对 create 意图有意义，query 永远 False"
    },
    {
        "scenario": "FIX：查询行程列表",
        "user_message": "我這禮拜有什麼安排",
        "intent": "query",
        "is_complete": False
    },
    {
        "scenario": "FIX：查询特定行程",
        "user_message": "明天的會議是什麼",
        "intent": "query",
        "is_complete": False
    },

    # ========================================================================
    # FIX 5: Intent 优先级判断
    # ========================================================================
    {
        "scenario": "歧义优先级：清单有匹配+修改词 → edit",
        "user_message": "把跟小明吃飯改晚一點",
        "context": {"schedule_list": [{"title": "與小明吃飯"}]},
        "intent": "edit",
        "rule": "(1) 清单有匹配+修改词 → edit"
    },
    {
        "scenario": "歧义优先级：清单无但有 create 词",
        "user_message": "下週五跟小明吃飯",
        "context": {"schedule_list": []},
        "intent": "create",
        "rule": "(2) 清单无+创建词 → create"
    },
    {
        "scenario": "歧义优先级：清单有匹配但用户想新建",
        "user_message": "再安排一個跟小明的吃飯",
        "context": {"schedule_list": [{"title": "與小明吃飯"}]},
        "intent": "create",
        "rule": "「再/又」明确表示新建，即使清单有匹配"
    },

    # ========================================================================
    # FIX 6: 时间默认值（活动类型推断）
    # ========================================================================
    {
        "user_message": "明天早餐",
        "default_time": "08:00:00",
        "rule": "早餐 → 08:00"
    },
    {
        "user_message": "明天午餐",
        "default_time": "12:00:00"
    },
    {
        "user_message": "明天下午茶",
        "default_time": "15:00:00"
    },
    {
        "user_message": "明天晚餐",
        "default_time": "19:00:00"
    },
    {
        "user_message": "明天宵夜",
        "default_time": "22:00:00"
    },
    {
        "user_message": "明天聚餐",
        "default_time": "19:00:00"
    },
    {
        "user_message": "明天開會",
        "default_time": "09:00:00"
    },
    {
        "user_message": "明天運動",
        "default_time": "15:00:00"
    },
    {
        "user_message": "明天看電影",
        "default_time": "19:00:00"
    },
    {
        "user_message": "明天上課",
        "default_time": "09:00:00"
    },

    # ========================================================================
    # FIX 7: 时段词默认时间
    # ========================================================================
    {"input": "早上", "time": "09:00:00"},
    {"input": "上午", "time": "10:00:00"},
    {"input": "中午", "time": "12:00:00"},
    {"input": "下午", "time": "14:00:00"},
    {"input": "傍晚", "time": "17:00:00"},
    {"input": "晚上", "time": "19:00:00"},
    {"input": "深夜", "time": "22:00:00"},
    {"input": "凌晨", "time": "02:00:00"},

    # ========================================================================
    # FIX 8: end_time 推断规则
    # ========================================================================
    {
        "scenario": "默认 end_time = start_time + 2h",
        "start": "2026-05-09T15:00:00",
        "end": "2026-05-09T17:00:00"
    },
    {
        "scenario": "用餐 1-1.5h",
        "title": "吃飯",
        "duration": "1.5h"
    },
    {
        "scenario": "会议默认 1h",
        "title": "開會",
        "duration": "1h"
    },
    {
        "scenario": "运动 1-2h",
        "title": "打球",
        "duration": "2h"
    },
    {
        "scenario": "看电影 ~2.5h",
        "title": "看電影",
        "duration": "2.5h"
    },

    # ========================================================================
    # FIX 9: 复杂意图链
    # ========================================================================
    {
        "scenario": "复合修改：时间+地点",
        "user_message": "把開會改到下週三下午3點，地點換到信義區",
        "intent": "edit",
        "expected_action": "update_schedule",
        "parsed": {
            "start_time": "2026-05-13T15:00:00",
            "location": "信義區"
        }
    },
    {
        "scenario": "复合修改：时间+人员",
        "user_message": "把吃飯改到5點，加上小美",
        "intent": "edit",
        "parsed": {
            "start_time": "...T17:00:00",
            "participants": ["@小美"]
        }
    },

    # ========================================================================
    # FIX 10: 不完整但能推断
    # ========================================================================
    {
        "scenario": "省略主语：直接建立",
        "user_message": "明天3點開會",
        "intent": "create",
        "is_complete": False,  # 缺地点
        "missing": ["location"]
    },
    {
        "scenario": "时间+地点+活动 但无人 → 完整",
        "user_message": "明天3點公司開會",
        "intent": "create",
        "is_complete": True,
        "rule": "公司=地点，开会=活动"
    },
    {
        "scenario": "线上会议无地点也算完整",
        "user_message": "明天3點線上會議",
        "intent": "create",
        "is_complete": True,
        "is_online": True
    },

    # ========================================================================
    # FIX 11: 多人会议判断
    # ========================================================================
    {
        "scenario": "明确多人 + 完整 = 完整",
        "user_message": "明天3點跟小明小美在台北101開會",
        "intent": "create",
        "is_complete": True,
        "participants": ["@小明", "@小美"]
    },
    {
        "scenario": "明确多人 缺地点 = 不完整",
        "user_message": "明天3點跟小明小美開會",
        "intent": "create",
        "is_complete": False,
        "missing": ["location"]
    },

    # ========================================================================
    # FIX 12: 常见错误模式纠正
    # ========================================================================
    {
        "scenario": "纠正：title 不该含「去」",
        "input": "去看電影",
        "WRONG_TITLE": "去看電影",
        "CORRECT_TITLE": "看電影"
    },
    {
        "scenario": "纠正：title 不该含「我」",
        "input": "我要開會",
        "WRONG_TITLE": "我要開會",
        "CORRECT_TITLE": "開會"
    },
    {
        "scenario": "纠正：title 不该含具体地点",
        "input": "在星巴克喝咖啡",
        "WRONG_TITLE": "在星巴克喝咖啡",
        "CORRECT_TITLE": "喝咖啡",
        "CORRECT_LOCATION": "星巴克"
    },
    {
        "scenario": "纠正：description 用法",
        "input": "明天3點開會討論預算",
        "title": "開會",
        "description": "討論預算",
        "rule": "「讨论X」放 description 不放 title"
    },

    # ========================================================================
    # FIX 13: 多轮 partial_data 累积
    # ========================================================================
    {
        "scenario": "多轮信息累积",
        "turns": [
            {
                "user": "明天有個重要會議",
                "ai_partial": {"title": "重要會議", "start_time": "2026-05-09T09:00:00"},
                "ai_question": "請問幾點？地點在哪？"
            },
            {
                "user": "下午3點",
                "ai_partial": {"title": "重要會議", "start_time": "2026-05-09T15:00:00"},
                "ai_question": "請問地點在哪？"
            },
            {
                "user": "信義區101",
                "ai_action": "create_schedule",
                "ai_data": {
                    "title": "重要會議",
                    "start_time": "2026-05-09T15:00:00",
                    "end_time": "2026-05-09T16:00:00",
                    "location": "信義區101",
                    "participants": []
                }
            }
        ],
        "rule": "每轮 partial_data 必须包含已知所有字段，不能丢失"
    },

    # ========================================================================
    # FIX 14: 用户口语回复理解
    # ========================================================================
    {"user": "好", "context": {"_pending_confirm": True}, "action": "execute"},
    {"user": "對", "context": {"_pending_confirm": True}, "action": "execute"},
    {"user": "可以", "context": {"_pending_confirm": True}, "action": "execute"},
    {"user": "OK", "context": {"_pending_confirm": True}, "action": "execute"},
    {"user": "確認", "context": {"_pending_confirm": True}, "action": "execute"},
    {"user": "不要", "context": {"_pending_confirm": True}, "action": "cancel"},
    {"user": "不對", "context": {"_pending_confirm": True}, "action": "cancel"},
    {"user": "算了", "context": {"_pending_confirm": True}, "action": "cancel"},
    {"user": "再想想", "context": {"_pending_confirm": True}, "action": "cancel"},
    {"user": "等等", "context": {"_pending_confirm": True}, "action": "wait"},

    # ========================================================================
    # FIX 15: 数字回答场景
    # ========================================================================
    {
        "user": "1",
        "context": {"_options_shown": ["A", "B", "C"]},
        "action": "select_option_1",
        "rule": "纯数字 + 之前显示选项 → 选择对应选项"
    },
    {
        "user": "2號",
        "context": {"_options_shown": ["A", "B"]},
        "action": "select_option_2"
    },
    {
        "user": "第一個",
        "action": "select_option_1"
    },

    # ========================================================================
    # FIX 16: 时间表达多样性 (vs 真实失败)
    # ========================================================================
    {"input": "後天", "today": "2026-05-08", "result": "2026-05-10"},
    {"input": "後天晚上七點", "result": "2026-05-10T19:00:00"},
    {"input": "下禮拜五", "today": "2026-05-08周五", "result": "2026-05-15", "explanation": "下周五=今天+7天"},
    {"input": "下禮拜五上午十點", "result": "2026-05-15T10:00:00"},
    {"input": "上禮拜三", "today": "2026-05-08周五", "result": "2026-05-06", "explanation": "上周三"},
    {"input": "下個月15號", "result": "2026-06-15"},
    {"input": "8/15", "result": "2026-08-15", "explanation": "默认今年"},
    {"input": "明年1月", "result": "2027-01-?"},

    # ========================================================================
    # FIX 17: 行程类型边界
    # ========================================================================
    {
        "scenario": "纯活动类型不算行程",
        "user_message": "我喜歡吃飯",
        "intent": "out_of_scope",
        "rule": "陈述句无时间/地点/动作意图 → 引导语"
    },
    {
        "scenario": "纯地点不算行程",
        "user_message": "台北101很好",
        "intent": "out_of_scope"
    },

    # ========================================================================
    # FIX 18: 隐含意图
    # ========================================================================
    {
        "scenario": "隐含创建：约会暗示",
        "user_message": "週末跟女友看電影",
        "intent": "create",
        "title": "與女友看電影",
        "is_complete": False,
        "missing": ["specific_date", "specific_time", "location"]
    },
    {
        "scenario": "隐含创建：邀请",
        "user_message": "邀請小明明天吃飯",
        "intent": "create",
        "title": "與小明吃飯",
        "is_complete": False,
        "missing": ["time_specific", "location"]
    },
    {
        "scenario": "隐含查询：暗示询问",
        "user_message": "好像有個會議",
        "intent": "query"
    },
]


def stats():
    print(f"V3 Total: {len(RAG_TRAINING_DATA_V3)} examples")
    print(f"\n重点修复：")
    fixes = {}
    for ex in RAG_TRAINING_DATA_V3:
        scenario = ex.get("scenario", "")
        if scenario.startswith("FIX"):
            fix_num = scenario.split("：")[0]
            fixes[fix_num] = fixes.get(fix_num, 0) + 1
    for k, v in sorted(fixes.items()):
        print(f"  {k}: {v} examples")


if __name__ == "__main__":
    stats()
