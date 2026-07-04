"""prompt_builder 純邏輯：行程清單 / 聯絡人 / 記憶 section 組裝。不需 DB。"""
from datetime import datetime

from app.services.prompt_builder import (
    build_context_sections,
    build_schedule_section,
    build_system_prompt,
)


def test_schedule_section_empty():
    assert "未提供" in build_schedule_section(None)
    assert "未提供" in build_schedule_section([])


def test_schedule_section_marks_keyword_match():
    schedules = [
        {"schedule_id": "s1", "title": "開會", "meeting_start_time": "2026-07-05T10:00:00",
         "meeting_location": "台北", "_match": True},
        {"schedule_id": "s2", "title": "打球", "meeting_start_time": "2026-07-06T18:00:00",
         "meeting_location": "板橋"},
    ]
    out = build_schedule_section(schedules)
    assert "★" in out                      # 匹配標記
    assert "id=s1" in out and "id=s2" in out
    assert "關鍵字匹配" in out              # 預匹配提示行
    assert "s1" in out.split("關鍵字匹配")[1]


def test_schedule_section_readonly_tag_for_non_owner():
    schedules = [{"schedule_id": "s1", "title": "會議", "is_owner": False,
                  "creator_name": "小明"}]
    out = build_schedule_section(schedules)
    assert "小明建立，唯讀" in out


def test_context_sections_duplicate_contacts_warning():
    context = {"_dup_小明": [
        {"comment": "同事", "phone": "1234"},
        {"comment": "", "phone": "5678"},
    ]}
    contact_section, _ = build_context_sections([], [], context)
    assert "同名聯絡人" in contact_section
    assert "ask_user" in contact_section


def test_system_prompt_has_time_and_fallback_rules():
    # session=None → 走 fallback 規則，仍需完整可用
    out = build_system_prompt(
        today=datetime(2026, 7, 4, 15, 30),
        schedule_section="【行程清單】（未提供）",
        memory_section="", contact_section="",
    )
    assert "2026-07-04 15:30" in out
    assert "create_schedule" in out   # fallback 工具規則
    assert "ask_user" in out
