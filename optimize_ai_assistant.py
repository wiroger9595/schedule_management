#!/usr/bin/env python3
"""
Comprehensive test suite for optimizing the schedule planning AI assistant.
Tests cover: parsing, intent detection, location handling, past schedules, etc.
Generates detailed HTML report with improvement recommendations.
"""
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict

sys.path.insert(0, "server")

# DB imports
from sqlmodel import Session
from app.db.database import engine
from app.models.ai_test_result import AITestResult

from app.services.ai_service import ai_service
from app.services.prompt_builder import build_schedule_section


@dataclass
class TestCase:
    """Single test case for AI assistant"""
    id: str
    name: str
    user_message: str
    category: str  # "parsing", "intent", "location", "past_schedule", "participants", "edge_case"
    expected_intent: str  # "create", "edit", "delete", "query"
    expected_complete: bool
    schedule_list: list = None
    contact_hints: list = None
    notes: str = ""


@dataclass
class TestResult:
    """Result of a single test"""
    test_case: TestCase
    actual_intent: str
    actual_complete: bool
    reply: str
    updated_data: dict
    quality_score: float  # 0-100
    passed: bool
    errors: List[str]
    model_label: str
    duration_ms: float


class AIAssistantTester:
    """Test framework for schedule planning AI"""

    def __init__(self):
        self.test_cases = self._build_test_cases()
        self.results: Dict[str, List[TestResult]] = {}

    def _build_test_cases(self) -> List[TestCase]:
        """Build comprehensive test suite"""
        return [
            # ── Category: Parsing (時間、日期、地點解析)
            TestCase(
                id="parse_1",
                name="相對日期 - 明天",
                user_message="明天下午三點開會",
                category="parsing",
                expected_intent="create",
                expected_complete=False,  # 缺地點
                notes="應該識別明天下午三點",
            ),
            TestCase(
                id="parse_2",
                name="相對日期 - 後天",
                user_message="後天晚上七點跟朋友吃飯在信義區",
                category="parsing",
                expected_intent="create",
                expected_complete=True,
                notes="完整訊息，應該建立",
            ),
            TestCase(
                id="parse_3",
                name="週日期 - 下禮拜五",
                user_message="下禮拜五上午十點在台北101開會",
                category="parsing",
                expected_intent="create",
                expected_complete=True,
            ),
            TestCase(
                id="parse_4",
                name="時間段 - 下午",
                user_message="下午去運動",
                category="parsing",
                expected_intent="create",
                expected_complete=False,  # 缺日期和地點
                notes="下午應該解析為 14:00-17:00 範圍",
            ),

            # ── Category: Intent Detection (意圖辨識)
            TestCase(
                id="intent_1",
                name="建立 - 清楚的建立請求",
                user_message="幫我安排明天下午三點跟小明在星巴克喝咖啡",
                category="intent",
                expected_intent="create",
                expected_complete=True,
                contact_hints=[{"nick_name": "小明", "similarity": 0.95}],
            ),
            TestCase(
                id="intent_2",
                name="編輯 - 改時間",
                user_message="把明天的開會改成下午五點",
                category="intent",
                expected_intent="edit",
                expected_complete=False,
                schedule_list=[
                    {
                        "schedule_id": "s1",
                        "title": "開會",
                        "meeting_start_time": "2026-05-01T10:00:00",
                        "meeting_location": "台北",
                    }
                ],
            ),
            TestCase(
                id="intent_3",
                name="刪除 - 明確的刪除",
                user_message="刪除我下禮拜的健身房行程",
                category="intent",
                expected_intent="delete",
                expected_complete=False,
            ),
            TestCase(
                id="intent_4",
                name="查詢 - 列出行程",
                user_message="我有什麼行程",
                category="intent",
                expected_intent="query",
                expected_complete=False,
            ),

            # ── Category: Location Handling (地點處理)
            TestCase(
                id="location_1",
                name="明確地點",
                user_message="明天下午三點在信義星巴克開會",
                category="location",
                expected_intent="create",
                expected_complete=True,  # 完整！時間+地點都有，沒人員是個人行程
                notes="時間+地點完整，自動視為個人行程",
            ),
            TestCase(
                id="location_2",
                name="模糊地點 - 品牌",
                user_message="下禮拜五在星巴克見面",
                category="location",
                expected_intent="create",
                expected_complete=False,
                notes="星巴克應該被識別為地點，但缺分店信息",
            ),
            TestCase(
                id="location_3",
                name="線上會議",
                user_message="明天上午十點線上會議",
                category="location",
                expected_intent="create",
                expected_complete=False,
                notes="線上不需要物理地點",
            ),

            # ── Category: Past Schedules (過去行程)
            TestCase(
                id="past_1",
                name="修改過去行程 - 保留日期",
                user_message="把三月十五的開會改成晚上八點",
                category="past_schedule",
                expected_intent="edit",
                expected_complete=True,  # 完整！用戶已明確說改成晚上八點
                schedule_list=[
                    {
                        "schedule_id": "past1",
                        "title": "開會",
                        "meeting_start_time": "2026-03-15T14:00:00",
                    }
                ],
                notes="應該保留原始日期，只改時間",
            ),
            TestCase(
                id="past_2",
                name="修改過去行程 - 改到未來",
                user_message="把三月十五的開會改到下禮拜五",
                category="past_schedule",
                expected_intent="edit",
                expected_complete=True,  # 完整！用戶已明確說改到下禮拜五
                schedule_list=[
                    {
                        "schedule_id": "past2",
                        "title": "開會",
                        "meeting_start_time": "2026-03-15T14:00:00",
                    }
                ],
                notes="應該更新到未來日期",
            ),

            # ── Category: Participants (參與者處理)
            TestCase(
                id="part_1",
                name="單一參與者",
                user_message="明天下午三點跟小明吃飯",
                category="participants",
                expected_intent="create",
                expected_complete=False,  # 缺地點
                contact_hints=[{"nick_name": "小明", "similarity": 0.95}],
            ),
            TestCase(
                id="part_2",
                name="多個參與者",
                user_message="下禮拜五和小明、小美、Robert 開會",
                category="participants",
                expected_intent="create",
                expected_complete=False,  # 缺時間和地點
                contact_hints=[
                    {"nick_name": "小明", "similarity": 0.9},
                    {"nick_name": "小美", "similarity": 0.9},
                    {"nick_name": "Robert", "similarity": 0.95},
                ],
            ),
            TestCase(
                id="part_3",
                name="移除參與者",
                user_message="把小明從開會中移除",
                category="participants",
                expected_intent="edit",
                expected_complete=False,
                schedule_list=[
                    {
                        "schedule_id": "s3",
                        "title": "開會",
                        "meeting_start_time": "2026-05-05T10:00:00",
                    }
                ],
            ),

            # ── Category: Edge Cases (邊界情況)
            TestCase(
                id="edge_1",
                name="模糊的「那個」",
                user_message="改一下那個行程",
                category="edge_case",
                expected_intent="edit",  # 用戶說「改」= edit intent，應該 ask_user 列出清單
                expected_complete=False,
                schedule_list=[
                    {
                        "schedule_id": "e1",
                        "title": "開會",
                        "meeting_start_time": "2026-05-01T10:00:00",
                    }
                ],
                notes="應該列出清單讓用戶選擇要改哪個",
            ),
            TestCase(
                id="edge_2",
                name="同名聯絡人",
                user_message="和小明開會",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,
                contact_hints=[
                    {"nick_name": "小明", "similarity": 0.8, "comment": "同事 A"},
                    {"nick_name": "小明", "similarity": 0.8, "comment": "朋友 B"},
                ],
                notes="應該要求用戶選擇是哪一位小明",
            ),
            TestCase(
                id="edge_3",
                name="缺少關鍵信息",
                user_message="安排一個會議",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,
                notes="應該逐步詢問：時間、地點、人員",
            ),
            TestCase(
                id="edge_4",
                name="離題問題",
                user_message="今天天氣怎樣？",
                category="edge_case",
                expected_intent="query",  # reply_to_user → ai_service.py 硬編碼返回 "query"
                expected_complete=False,
                notes="應該拒絕回答並引導回行程功能，使用 reply_to_user",
            ),

            # ── 新增 50 個測試用例（進階場景）─────────────────────

            # ── 時間解析進階 (parse_5 ~ parse_14)
            TestCase(
                id="parse_5",
                name="相對時間 - 一小時後",
                user_message="一小時後和小明在星巴克喝咖啡",
                category="parsing",
                expected_intent="create",
                expected_complete=True,
                contact_hints=[{"nick_name": "小明", "similarity": 0.95}],
            ),
            TestCase(
                id="parse_6",
                name="時間範圍 - 整個下午",
                user_message="下午和小美一起去打球",
                category="parsing",
                expected_intent="create",
                expected_complete=False,  # 缺地點
                contact_hints=[{"nick_name": "小美", "similarity": 0.95}],
            ),
            TestCase(
                id="parse_7",
                name="時間修飾 - 大概中午",
                user_message="大概中午和Robert吃飯在新竹",
                category="parsing",
                expected_intent="create",
                expected_complete=True,
            ),
            TestCase(
                id="parse_8",
                name="農曆日期 - 初一",
                user_message="農曆初一要去廟裡拜拜",
                category="parsing",
                expected_intent="create",
                expected_complete=False,  # 缺時間
            ),
            TestCase(
                id="parse_9",
                name="時間 - 周末",
                user_message="周末和家人去台北101",
                category="parsing",
                expected_intent="create",
                expected_complete=False,  # 缺時間
            ),
            TestCase(
                id="parse_10",
                name="時間 - 傍晚5點到7點",
                user_message="傍晚5點到7點在健身房運動",
                category="parsing",
                expected_intent="create",
                expected_complete=True,
            ),
            TestCase(
                id="parse_11",
                name="時間 - 連續兩天",
                user_message="明天和後天都要開會",
                category="parsing",
                expected_intent="create",
                expected_complete=False,  # 缺地點和確切時間
            ),
            TestCase(
                id="parse_12",
                name="時間 - 月末",
                user_message="月底前要交報告",
                category="parsing",
                expected_intent="create",
                expected_complete=False,  # 缺時間和地點
            ),
            TestCase(
                id="parse_13",
                name="時間 - 季度末",
                user_message="季度末開季度檢討會議",
                category="parsing",
                expected_intent="create",
                expected_complete=False,  # 缺日期
            ),
            TestCase(
                id="parse_14",
                name="時間 - 假期",
                user_message="連假期間要回家見父母",
                category="parsing",
                expected_intent="create",
                expected_complete=False,  # 缺具體日期和時間
            ),

            # ── 意圖識別進階 (intent_5 ~ intent_14)
            TestCase(
                id="intent_5",
                name="建立 - 用請求語句",
                user_message="可以幫我約小明明天下午在咖啡廳嗎",
                category="intent",
                expected_intent="create",
                expected_complete=True,
                contact_hints=[{"nick_name": "小明", "similarity": 0.95}],
            ),
            TestCase(
                id="intent_6",
                name="編輯 - 更改",
                user_message="把下禮拜的會議更改為上午進行",
                category="intent",
                expected_intent="edit",
                expected_complete=True,  # 有具體時間（上午 = 09:00）
                schedule_list=[{
                    "schedule_id": "s6",
                    "title": "會議",
                    "meeting_start_time": "2026-05-05T14:00:00",
                }],
            ),
            TestCase(
                id="intent_7",
                name="編輯 - 換",
                user_message="把參加人從小明換成小美",
                category="intent",
                expected_intent="edit",
                expected_complete=False,
                schedule_list=[{
                    "schedule_id": "s7",
                    "title": "與小明開會",
                    "meeting_start_time": "2026-05-05T10:00:00",
                }],
            ),
            TestCase(
                id="intent_8",
                name="刪除 - 取消",
                user_message="取消明天的運動課程",
                category="intent",
                expected_intent="delete",
                expected_complete=False,
            ),
            TestCase(
                id="intent_9",
                name="刪除 - 去掉",
                user_message="把周五的吃飯約去掉",
                category="intent",
                expected_intent="delete",
                expected_complete=False,
            ),
            TestCase(
                id="intent_10",
                name="查詢 - 我今天幾點有行程",
                user_message="我今天幾點有行程",
                category="intent",
                expected_intent="query",
                expected_complete=False,
            ),
            TestCase(
                id="intent_11",
                name="查詢 - 列出",
                user_message="列出我這周的所有行程",
                category="intent",
                expected_intent="query",
                expected_complete=False,
            ),
            TestCase(
                id="intent_12",
                name="查詢 - 檢查",
                user_message="檢查一下明天有沒有重要的會議",
                category="intent",
                expected_intent="query",
                expected_complete=False,
            ),
            TestCase(
                id="intent_13",
                name="編輯 - 加入",
                user_message="把小華加入明天的開會",
                category="intent",
                expected_intent="edit",
                expected_complete=False,
                schedule_list=[{
                    "schedule_id": "s13",
                    "title": "開會",
                    "meeting_start_time": "2026-05-01T10:00:00",
                }],
            ),
            TestCase(
                id="intent_14",
                name="編輯 - 移除",
                user_message="把小明從下周三的行程中移除",
                category="intent",
                expected_intent="edit",
                expected_complete=False,
                schedule_list=[{
                    "schedule_id": "s14",
                    "title": "和小明開會",
                    "meeting_start_time": "2026-05-07T15:00:00",
                }],
            ),

            # ── 位置處理進階 (location_4 ~ location_12)
            TestCase(
                id="location_4",
                name="線上 + 地點混合",
                user_message="明天下午三點在新竹和台北同時開線上會議",
                category="location",
                expected_intent="create",
                expected_complete=False,  # 混合場景，缺參與者
            ),
            TestCase(
                id="location_5",
                name="連鎖店分店 - 全家",
                user_message="明天中午在中山路全家便利店集合",
                category="location",
                expected_intent="create",
                expected_complete=True,  # 中午=12:00，有地點，個人行程完整
            ),
            TestCase(
                id="location_6",
                name="地標 - 百貨公司",
                user_message="下禮拜五晚上在台北101見面",
                category="location",
                expected_intent="create",
                expected_complete=True,  # 晚上=19:00，有地點，個人行程完整
            ),
            TestCase(
                id="location_7",
                name="公共交通站點",
                user_message="明天下午三點在台北車站門口",
                category="location",
                expected_intent="create",
                expected_complete=False,  # 缺 title（只有地點，不知道做什麼）
            ),
            TestCase(
                id="location_8",
                name="家裡（地點）",
                user_message="周末在我家和小明打麻將",
                category="location",
                expected_intent="create",
                expected_complete=False,  # 缺具體日期
                contact_hints=[{"nick_name": "小明", "similarity": 0.95}],
            ),
            TestCase(
                id="location_9",
                name="辦公室",
                user_message="明天上午十點在辦公室開會",
                category="location",
                expected_intent="create",
                expected_complete=True,
            ),
            TestCase(
                id="location_10",
                name="戶外位置 - 公園",
                user_message="周末上午在大安森林公園慢跑",
                category="location",
                expected_intent="create",
                expected_complete=False,  # 缺具體時間
            ),
            TestCase(
                id="location_11",
                name="不確定的地點",
                user_message="下週二和小美去逛街，還沒決定在哪",
                category="location",
                expected_intent="create",
                expected_complete=False,  # 缺地點
                contact_hints=[{"nick_name": "小美", "similarity": 0.95}],
            ),
            TestCase(
                id="location_12",
                name="多個地點",
                user_message="先在信義區吃飯，然後去西門町看電影",
                category="location",
                expected_intent="create",
                expected_complete=False,  # 缺時間
            ),

            # ── 參與者處理進階 (part_4 ~ part_12)
            TestCase(
                id="part_4",
                name="多人同時邀請",
                user_message="明天下午和小明、小美、小王、David 一起吃飯在信義區",
                category="participants",
                expected_intent="create",
                expected_complete=True,
                contact_hints=[
                    {"nick_name": "小明", "similarity": 0.9},
                    {"nick_name": "小美", "similarity": 0.9},
                    {"nick_name": "小王", "similarity": 0.85},
                ],
            ),
            TestCase(
                id="part_5",
                name="移除特定人",
                user_message="把Robert從明天的會議中移除",
                category="participants",
                expected_intent="edit",
                expected_complete=False,
                schedule_list=[{
                    "schedule_id": "p5",
                    "title": "和Robert開會",
                    "meeting_start_time": "2026-05-01T10:00:00",
                }],
            ),
            TestCase(
                id="part_6",
                name="新增參與者（複數）",
                user_message="把小美和小王加入明天的會議",
                category="participants",
                expected_intent="edit",
                expected_complete=False,
                schedule_list=[{
                    "schedule_id": "p6",
                    "title": "會議",
                    "meeting_start_time": "2026-05-01T10:00:00",
                }],
            ),
            TestCase(
                id="part_7",
                name="臨時參與者",
                user_message="明天可以邀請 Jane 一起來開會嗎",
                category="participants",
                expected_intent="create",
                expected_complete=False,  # 缺地點和時間
            ),
            TestCase(
                id="part_8",
                name="移除所有人（個人行程）",
                user_message="取消邀請，就我一個人去",
                category="participants",
                expected_intent="edit",
                expected_complete=False,
                schedule_list=[{
                    "schedule_id": "p8",
                    "title": "和朋友出遊",
                    "meeting_start_time": "2026-05-05T14:00:00",
                }],
            ),
            TestCase(
                id="part_9",
                name="昵稱識別",
                user_message="明天和 JS（就是小傑）在咖啡廳見面",
                category="participants",
                expected_intent="create",
                expected_complete=False,  # 缺地點詳情和時間
            ),
            TestCase(
                id="part_10",
                name="公司團隊參與",
                user_message="明天下午和整個 PM 團隊開會",
                category="participants",
                expected_intent="create",
                expected_complete=False,  # 缺時間和地點
            ),
            TestCase(
                id="part_11",
                name="可選參與者",
                user_message="明天可以的話請 Robert 和 Sarah 也來",
                category="participants",
                expected_intent="create",
                expected_complete=False,  # 缺地點和時間
            ),
            TestCase(
                id="part_12",
                name="家庭成員",
                user_message="周末帶全家去新竹吃飯",
                category="participants",
                expected_intent="create",
                expected_complete=False,  # 缺具體時間
            ),

            # ── 修改過去行程進階 (past_3 ~ past_8)
            TestCase(
                id="past_3",
                name="過去行程改時間（同日）",
                user_message="昨天的會議改成上午 9 點",
                category="past_schedule",
                expected_intent="edit",
                expected_complete=True,
                schedule_list=[{
                    "schedule_id": "past3",
                    "title": "會議",
                    "meeting_start_time": "2026-04-29T14:00:00",
                }],
            ),
            TestCase(
                id="past_4",
                name="過去行程改時間（不同日期）",
                user_message="三月底的旅遊改到暑假",
                category="past_schedule",
                expected_intent="edit",
                expected_complete=False,  # "暑假" 不夠具體
                schedule_list=[{
                    "schedule_id": "past4",
                    "title": "旅遊",
                    "meeting_start_time": "2026-03-30T10:00:00",
                }],
            ),
            TestCase(
                id="past_5",
                name="過去行程改參與者",
                user_message="把上禮拜的開會改為只有我參加",
                category="past_schedule",
                expected_intent="edit",
                expected_complete=True,
                schedule_list=[{
                    "schedule_id": "past5",
                    "title": "和小明開會",
                    "meeting_start_time": "2026-04-22T10:00:00",
                }],
            ),
            TestCase(
                id="past_6",
                name="過去行程改地點",
                user_message="上周三的午餐改到新竹",
                category="past_schedule",
                expected_intent="edit",
                expected_complete=True,
                schedule_list=[{
                    "schedule_id": "past6",
                    "title": "午餐",
                    "meeting_start_time": "2026-04-23T12:00:00",
                }],
            ),
            TestCase(
                id="past_7",
                name="過去行程更名",
                user_message="把上週的會議改名為 Q2 季度檢討",
                category="past_schedule",
                expected_intent="edit",
                expected_complete=True,
                schedule_list=[{
                    "schedule_id": "past7",
                    "title": "會議",
                    "meeting_start_time": "2026-04-25T15:00:00",
                }],
            ),
            TestCase(
                id="past_8",
                name="過去行程刪除",
                user_message="刪除昨天那個被取消的會議",
                category="past_schedule",
                expected_intent="delete",
                expected_complete=False,
                schedule_list=[{
                    "schedule_id": "past8",
                    "title": "取消的會議",
                    "meeting_start_time": "2026-04-29T10:00:00",
                }],
            ),

            # ── 邊界情況進階 (edge_5 ~ edge_20)
            TestCase(
                id="edge_5",
                name="全小寫輸入",
                user_message="明天下午三點和john在星巴克喝咖啡",
                category="edge_case",
                expected_intent="create",
                expected_complete=True,
            ),
            TestCase(
                id="edge_6",
                name="使用數字日期",
                user_message="2026/5/15 下午三點開會在台北",
                category="edge_case",
                expected_intent="create",
                expected_complete=True,
            ),
            TestCase(
                id="edge_7",
                name="無空格連貫",
                user_message="明天下午三點跟小明在星巴克開會",
                category="edge_case",
                expected_intent="create",
                expected_complete=True,
                contact_hints=[{"nick_name": "小明", "similarity": 0.95}],
            ),
            TestCase(
                id="edge_8",
                name="繁簡混用",
                user_message="tomorrow下午三點在咖啡廳見面",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,  # "tomorrow" 是英文，可能解析有誤
            ),
            TestCase(
                id="edge_9",
                name="重複訊息",
                user_message="明天明天下午下午三點三點開會",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,  # 訊息混亂，缺地點
            ),
            TestCase(
                id="edge_10",
                name="過度詳細",
                user_message="明天下午三點到五點在信義區 101 棟 35 樓新竹銀行 會議室和小明、小美、小王、David、Robert 開 Q2 季度檢討會議",
                category="edge_case",
                expected_intent="create",
                expected_complete=True,
            ),
            TestCase(
                id="edge_11",
                name="反問式請求",
                user_message="我明天有空嗎？",
                category="edge_case",
                expected_intent="query",
                expected_complete=False,
            ),
            TestCase(
                id="edge_12",
                name="非常簡短",
                user_message="明天開會",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,  # 缺時間和地點
            ),
            TestCase(
                id="edge_13",
                name="只有人名",
                user_message="和小明",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,  # 缺所有詳細信息
                contact_hints=[{"nick_name": "小明", "similarity": 0.95}],
            ),
            TestCase(
                id="edge_14",
                name="不相關的後續",
                user_message="對了，有沒有好的餐廳推薦",
                category="edge_case",
                expected_intent="query",
                expected_complete=False,  # 離題
            ),
            TestCase(
                id="edge_15",
                name="時間戳記",
                user_message="5/15 15:00 星巴克 @小明 @小美",
                category="edge_case",
                expected_intent="create",
                expected_complete=True,
            ),
            TestCase(
                id="edge_16",
                name="自然語言混雜",
                user_message="嗨，明天下午 3 點在信義 starbucks 和小明見面可以嗎",
                category="edge_case",
                expected_intent="create",
                expected_complete=True,
                contact_hints=[{"nick_name": "小明", "similarity": 0.95}],
            ),
            TestCase(
                id="edge_17",
                name="長句子",
                user_message="我想明天下午在信義區星巴克和小明、小美一起開會討論 Q2 的季度目標，大概需要兩小時",
                category="edge_case",
                expected_intent="create",
                expected_complete=True,
                contact_hints=[
                    {"nick_name": "小明", "similarity": 0.9},
                    {"nick_name": "小美", "similarity": 0.9},
                ],
            ),
            TestCase(
                id="edge_18",
                name="缺少主語",
                user_message="下午三點在咖啡廳見面",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,  # 缺日期
            ),
            TestCase(
                id="edge_19",
                name="條件性要求",
                user_message="如果下禮拜五天氣好的話，我們去郊遊",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,  # 有條件，缺具體時間
            ),
            TestCase(
                id="edge_20",
                name="多語言混用",
                user_message="明天 3PM 在 Starbucks 和 John、小美開會，地點在 Taipei 信義區",
                category="edge_case",
                expected_intent="create",
                expected_complete=True,
            ),

            # ── 實境應用場景 (real_1 ~ real_10)
            TestCase(
                id="real_1",
                name="日常咖啡約",
                user_message="周末早上十點在我們常去的那間咖啡廳和小美一起喝咖啡",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,  # "我們常去的那間" 不夠具體
                contact_hints=[{"nick_name": "小美", "similarity": 0.95}],
            ),
            TestCase(
                id="real_2",
                name="工作會議",
                user_message="下周一到三每天上午 10 點開晨會",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,  # 連續多天，缺地點
            ),
            TestCase(
                id="real_3",
                name="健身房",
                user_message="每週三晚上七點在健身房健身課程",
                category="edge_case",
                expected_intent="create",
                expected_complete=True,
            ),
            TestCase(
                id="real_4",
                name="家務提醒",
                user_message="周六上午十點要洗衣服",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,  # 無地點
            ),
            TestCase(
                id="real_5",
                name="醫療預約",
                user_message="下個月 15 號下午兩點牙科診所檢查牙齒",
                category="edge_case",
                expected_intent="create",
                expected_complete=True,
            ),
            TestCase(
                id="real_6",
                name="交通運輸",
                user_message="明天上午八點要去機場坐飛機",
                category="edge_case",
                expected_intent="create",
                expected_complete=True,
            ),
            TestCase(
                id="real_7",
                name="家庭聚餐",
                user_message="農曆新年初二要回家和爸媽吃飯",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,  # 時間不具體
            ),
            TestCase(
                id="real_8",
                name="演唱會門票",
                user_message="五月二十號晚上七點在小巨蛋看演唱會",
                category="edge_case",
                expected_intent="create",
                expected_complete=True,  # 個人行程，有 time + location，不需參與者
            ),
            TestCase(
                id="real_9",
                name="提交截止日期",
                user_message="周五下午五點前要交企劃案給主管",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,  # 無地點，或可視為線上
            ),
            TestCase(
                id="real_10",
                name="旅遊行程",
                user_message="暑假要和家人去日本京都玩五天",
                category="edge_case",
                expected_intent="create",
                expected_complete=False,  # 缺具體日期
            ),
        ]

    def run_tests(self, models_to_test: List[int] = None) -> Dict[str, List[TestResult]]:
        """
        Run all test cases on specified models.
        models_to_test: list of provider indices (0=Cerebras, 1=Groq, 2=Gemini), None=all
        """
        if models_to_test is None:
            models_to_test = list(range(len(ai_service._providers)))

        for model_idx in models_to_test:
            if model_idx >= len(ai_service._providers):
                print(f"⚠️  Model index {model_idx} out of range")
                continue

            _cli, _model, _label = ai_service._providers[model_idx]
            self.results[_label] = []

            print(f"\n{'='*80}")
            print(f"Testing {_label}")
            print(f"{'='*80}")

            THROTTLE_SEC = 6.0
            BACKOFF_SEC = 60.0
            for i, test_case in enumerate(self.test_cases):
                result = self._run_single_test(model_idx, test_case)
                self.results[_label].append(result)

                status = "✓" if result.passed else "✗"
                print(
                    f"[{i+1:2d}/{len(self.test_cases)}] {status} {test_case.name:30s} "
                    f"(score: {result.quality_score:5.1f}) {result.duration_ms:6.1f}ms"
                )

                if i < len(self.test_cases) - 1:
                    # Detect rate limit from any source: errors list, reply prefix, or duration<1s
                    err_blob = " ".join(result.errors or []) + " " + (result.reply or "")
                    rate_limited = (
                        "AI_RATE_LIMITED" in err_blob
                        or "rate" in err_blob.lower()
                        or "429" in err_blob
                        or (result.duration_ms < 800 and not result.passed)
                    )
                    time.sleep(BACKOFF_SEC if rate_limited else THROTTLE_SEC)

            # Save results to DB for tracking
            self.save_results_to_db()

        return self.results

    def _run_single_test(self, model_idx: int, test_case: TestCase) -> TestResult:
        """Run single test case"""
        start = time.time()

        try:
            result = ai_service.process_conversation_with_provider(
                provider_index=model_idx,
                user_message=test_case.user_message,
                schedule_list=test_case.schedule_list,
                contact_hints=test_case.contact_hints,
            )

            duration_ms = (time.time() - start) * 1000
            _cli, _model, _label = ai_service._providers[model_idx]

            # Assess quality
            quality, errors = self._assess_test_result(result, test_case)
            # Surface ai_service "error" field so BACKOFF detection can see rate-limit signals
            if result.get("error"):
                errors.insert(0, f"[ai_service.error] {result['error']}")

            passed = (
                result.get("intent") == test_case.expected_intent
                and result.get("is_complete") == test_case.expected_complete
                and quality >= 60
            )

            return TestResult(
                test_case=test_case,
                actual_intent=result.get("intent", "?"),
                actual_complete=result.get("is_complete", False),
                reply=result.get("reply", "")[:100],
                updated_data=result.get("updated_data", {}),
                quality_score=quality,
                passed=passed,
                errors=errors,
                model_label=_label,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            _cli, _model, _label = ai_service._providers[model_idx]
            return TestResult(
                test_case=test_case,
                actual_intent="ERROR",
                actual_complete=False,
                reply=str(e)[:100],
                updated_data={},
                quality_score=0,
                passed=False,
                errors=[str(e)],
                model_label=_label,
                duration_ms=duration_ms,
            )

    def _assess_test_result(
        self, result: dict, test_case: TestCase
    ) -> Tuple[float, List[str]]:
        """Assess test result quality"""
        score = 50  # Base score
        errors = []

        # Intent match
        if result.get("intent") == test_case.expected_intent:
            score += 25
        else:
            errors.append(
                f"Intent mismatch: expected {test_case.expected_intent}, "
                f"got {result.get('intent')}"
            )

        # Completeness match
        if result.get("is_complete") == test_case.expected_complete:
            score += 15
        else:
            errors.append(
                f"Completeness mismatch: expected {test_case.expected_complete}, "
                f"got {result.get('is_complete')}"
            )

        # Reply quality
        if result.get("reply"):
            score += 10
        else:
            errors.append("No reply from AI")

        return max(0, min(100, score)), errors

    def save_results_to_db(self):
        """Save test results to database for tracking improvement"""
        try:
            session = Session(engine)
            for model_label, results in self.results.items():
                for result in results:
                    # Skip error cases (intent='ERROR' from cascade failure)
                    if result.actual_intent == "ERROR":
                        continue

                    db_result = AITestResult(
                        test_case_id=result.test_case.id,
                        category=result.test_case.category,
                        user_message=result.test_case.user_message,
                        expected_intent=result.test_case.expected_intent,
                        expected_complete=result.test_case.expected_complete,
                        model_name=model_label,
                        actual_intent=result.actual_intent,
                        actual_complete=result.actual_complete,
                        model_reply=result.reply,
                        passed=result.passed,
                        quality_score=result.quality_score,
                        duration_ms=result.duration_ms,
                        errors="|".join(result.errors) if result.errors else None,
                    )
                    session.add(db_result)
            session.commit()
            print(f"\n✅ 測試結果已存儲到 DB")
        except Exception as e:
            print(f"\n⚠️  DB 存儲失敗: {e}")
        finally:
            session.close()

    def generate_report(self, output_file: str = "ai_test_report.html"):
        """Generate HTML report"""
        html = self._build_html_report()
        Path(output_file).write_text(html, encoding="utf-8")
        print(f"📊 Report saved to {output_file}")

    def _build_html_report(self) -> str:
        """Build HTML report content"""
        # Summary statistics
        total_tests = len(self.test_cases)
        summary_by_model = {}

        for model_label, results in self.results.items():
            passed = sum(1 for r in results if r.passed)
            avg_score = sum(r.quality_score for r in results) / len(results)
            avg_time = sum(r.duration_ms for r in results) / len(results)

            summary_by_model[model_label] = {
                "passed": passed,
                "total": total_tests,
                "pass_rate": f"{passed/total_tests*100:.1f}%",
                "avg_score": f"{avg_score:.1f}",
                "avg_time_ms": f"{avg_time:.1f}",
            }

        # Category breakdown
        category_stats = self._get_category_stats()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>AI 行程助理優化報告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
                h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
                h2 {{ color: #555; margin-top: 30px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #4CAF50; color: white; }}
                tr:hover {{ background: #f5f5f5; }}
                .pass {{ background: #d4edda; color: #155724; }}
                .fail {{ background: #f8d7da; color: #721c24; }}
                .score-high {{ color: #28a745; font-weight: bold; }}
                .score-med {{ color: #ffc107; font-weight: bold; }}
                .score-low {{ color: #dc3545; font-weight: bold; }}
                .recommendation {{ background: #e7f3ff; border-left: 4px solid #2196F3; padding: 10px; margin: 10px 0; }}
                .error {{ color: #d32f2f; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 AI 行程助理優化報告</h1>
                <p>生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

                <h2>📊 整體概況</h2>
                <table>
                    <tr>
                        <th>模型</th>
                        <th>通過率</th>
                        <th>平均分數</th>
                        <th>平均時間</th>
                    </tr>
        """

        for model_label, stats in summary_by_model.items():
            html += f"""
                    <tr>
                        <td>{model_label}</td>
                        <td>{stats['pass_rate']} ({stats['passed']}/{stats['total']})</td>
                        <td><span class="score-high">{stats['avg_score']}</span></td>
                        <td>{stats['avg_time_ms']} ms</td>
                    </tr>
            """

        html += """
                </table>

                <h2>📈 按類別分析</h2>
                <table>
                    <tr>
                        <th>類別</th>
                        <th>通過率</th>
                        <th>常見問題</th>
                    </tr>
        """

        for category, stats in category_stats.items():
            html += f"""
                    <tr>
                        <td><strong>{category}</strong></td>
                        <td>{stats['pass_rate']} ({stats['passed']}/{stats['total']})</td>
                        <td>
        """
            for issue in stats["common_issues"][:3]:
                html += f"<div class='error'>• {issue}</div>"
            html += """
                        </td>
                    </tr>
            """

        html += """
                </table>

                <h2>🔍 詳細測試結果</h2>
        """

        for model_label, results in self.results.items():
            html += f"<h3>{model_label}</h3><table>"
            html += """
                <tr>
                    <th>測試名稱</th>
                    <th>類別</th>
                    <th>意圖</th>
                    <th>完整</th>
                    <th>分數</th>
                    <th>狀態</th>
                    <th>時間</th>
                </tr>
            """

            for result in results:
                status_class = "pass" if result.passed else "fail"
                status_text = "✓" if result.passed else "✗"
                score_class = (
                    "score-high"
                    if result.quality_score >= 80
                    else "score-med" if result.quality_score >= 60 else "score-low"
                )

                html += f"""
                <tr>
                    <td>{result.test_case.name}</td>
                    <td>{result.test_case.category}</td>
                    <td>{result.actual_intent}</td>
                    <td>{"✓" if result.actual_complete else "✗"}</td>
                    <td><span class="{score_class}">{result.quality_score:.0f}</span></td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{result.duration_ms:.1f}ms</td>
                </tr>
                """

                if result.errors:
                    html += f"<tr><td colspan='7' class='error'>錯誤: {', '.join(result.errors)}</td></tr>"

            html += "</table>"

        # Recommendations
        html += """
                <h2>💡 優化建議</h2>
        """

        recommendations = self._generate_recommendations()
        for rec in recommendations:
            html += f"""
                <div class="recommendation">
                    <strong>{rec['title']}</strong><br>
                    {rec['description']}<br>
                    <small>優先度: {rec['priority']}</small>
                </div>
            """

        html += """
            </div>
        </body>
        </html>
        """

        return html

    def _get_category_stats(self) -> Dict:
        """Get statistics by category"""
        stats = {}
        for category in set(tc.category for tc in self.test_cases):
            cases_in_category = [tc for tc in self.test_cases if tc.category == category]
            passed_in_category = sum(
                1
                for r in sum(self.results.values(), [])
                if r.test_case.category == category and r.passed
            )
            total_in_category = len(cases_in_category) * len(self.results)

            issues = []
            for r in sum(self.results.values(), []):
                if r.test_case.category == category and r.errors:
                    issues.extend(r.errors)

            stats[category] = {
                "passed": passed_in_category,
                "total": total_in_category,
                "pass_rate": f"{passed_in_category/total_in_category*100:.0f}%" if total_in_category > 0 else "N/A",
                "common_issues": list(set(issues))[:5],
            }

        return stats

    def _generate_recommendations(self) -> List[Dict]:
        """Generate optimization recommendations based on test results"""
        recommendations = []

        # Analyze failures
        all_results = sum(self.results.values(), [])
        failed_results = [r for r in all_results if not r.passed]

        if len(failed_results) / len(all_results) > 0.3:
            recommendations.append({
                "title": "🔴 整體識別率過低",
                "description": f"失敗率 {len(failed_results)/len(all_results)*100:.0f}%，需要重新審視 prompt 和約束。",
                "priority": "高",
            })

        # Category-specific issues
        for category, stats in self._get_category_stats().items():
            if stats["total"] > 0 and float(stats["pass_rate"].rstrip("%")) < 70:
                recommendations.append({
                    "title": f"⚠️ {category} 識別不佳",
                    "description": f"此類別通過率僅 {stats['pass_rate']}，常見問題: {', '.join(stats['common_issues'][:2])}",
                    "priority": "中",
                })

        # Performance issues
        avg_times = {}
        for model_label, results in self.results.items():
            avg_times[model_label] = sum(r.duration_ms for r in results) / len(results)

        slow_models = [m for m, t in avg_times.items() if t > 5000]
        if slow_models:
            recommendations.append({
                "title": "⏱️ 性能問題",
                "description": f"以下模型響應慢: {', '.join(slow_models)}，考慮調整超時或降級模型優先度。",
                "priority": "中",
            })

        # Model-specific recommendations
        for model_label, results in self.results.items():
            passed = sum(1 for r in results if r.passed)
            if passed / len(results) < 0.5:
                recommendations.append({
                    "title": f"🤖 {model_label} 表現差",
                    "description": f"此模型通過率僅 {passed/len(results)*100:.0f}%，建議降低優先度或考慮替換。",
                    "priority": "高",
                })

        if not recommendations:
            recommendations.append({
                "title": "✅ 表現良好",
                "description": "所有測試通過率都不錯，保持當前配置。",
                "priority": "低",
            })

        return recommendations

    def print_summary(self):
        """Print test summary to console"""
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)

        for model_label, results in self.results.items():
            passed = sum(1 for r in results if r.passed)
            avg_score = sum(r.quality_score for r in results) / len(results)
            print(
                f"\n{model_label}:"
                f"\n  通過率: {passed}/{len(results)} ({passed/len(results)*100:.0f}%)"
                f"\n  平均分數: {avg_score:.1f}/100"
            )

        # By category
        print("\n" + "-"*80)
        print("按類別分析:")
        for category, stats in self._get_category_stats().items():
            print(f"  {category:20s}: {stats['pass_rate']}")


def main():
    """Main test execution"""
    import argparse

    parser = argparse.ArgumentParser(description="Optimize schedule planning AI")
    parser.add_argument(
        "--models",
        type=int,
        nargs="+",
        help="Model indices to test (0=Cerebras, 1=Groq, 2=Gemini)",
    )
    parser.add_argument("--report", default="ai_test_report.html", help="Output report file")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print("🚀 Starting AI Assistant Optimization Tests...\n")

    tester = AIAssistantTester()
    tester.run_tests(models_to_test=args.models)
    tester.print_summary()
    tester.generate_report(args.report)

    print(f"\n✅ Done! Open {args.report} in a browser to view detailed results.")


if __name__ == "__main__":
    main()
