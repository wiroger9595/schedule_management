#!/usr/bin/env python3
"""
跨 provider conformance harness。

把 tests/ai_cases.py 的 case 跑過每一個 provider，結果寫進 ai_test_result 表，
再用 generate_baseline_report.py 出跨模型報表。

    python run_conformance.py --list              # 只列出 provider 名單，不打 API
    python run_conformance.py --limit 10          # smoke test，只打 10 次
    python run_conformance.py                     # 全部 provider × 全部 case
    python run_conformance.py --provider 0
    python run_conformance.py --case edit_id_from_list --no-db

--limit 走 round-robin（每個 provider 輪流打一個 case），用最少的呼叫數把
6 條 provider 路徑都碰過一次。順便也是天然的節流：同一家兩次呼叫中間
會隔著其他 5 家。

⚠️ 免費 tier 的限制（跑之前先算）：
    Cerebras   5 RPM  / 1M tokens per day
    OpenRouter 20 RPM / 50 requests per day（沒儲值過 $10）—— 佔了 2 個 provider
    Groq       30 RPM / 14,400 requests per day
"""
import argparse
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session

from app.db.database import engine
from app.models.ai_test_result import AITestResult
from app.services.ai_service import ai_service
from tests.ai_cases import CASES, case_schedules, evaluate


# 依各家免費 tier 的 RPM 換算，留安全邊際。key 比對 provider label 的前綴。
_MIN_INTERVAL_SEC = {
    "Cerebras":    12.5,   # 5 RPM —— 最緊的一家
    "Gemini":       6.0,
    "OpenRouter":   3.5,   # 20 RPM
    "Groq":         2.5,   # 30 RPM
    "HuggingFace":  3.0,
}
_DEFAULT_INTERVAL = 4.0


def _interval_for(label: str) -> float:
    for prefix, sec in _MIN_INTERVAL_SEC.items():
        if label.startswith(prefix):
            return sec
    return _DEFAULT_INTERVAL


def build_tasks(providers, cases, limit=None):
    """Round-robin：(p0,c0), (p1,c0), ... (p0,c1), ... 讓 limit 先橫向覆蓋全部 provider。"""
    tasks = []
    for case in cases:
        for idx, (_, _, label) in enumerate(providers):
            tasks.append((idx, label, case))
    return tasks[:limit] if limit else tasks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="最多打幾次 API（round-robin 分配）")
    ap.add_argument("--provider", type=int, help="只跑指定 provider index")
    ap.add_argument("--case", help="只跑指定 case id")
    ap.add_argument("--no-db", action="store_true", help="不寫 ai_test_result")
    ap.add_argument("--list", action="store_true", help="只列出 provider，不打 API")
    ap.add_argument("--json-path", action="store_true",
                    help="強制走 JSON path（跳過 tool calling），比對兩條路徑差異")
    args = ap.parse_args()

    providers = list(ai_service._providers)

    print(f"Providers ({len(providers)}):")
    for i, (_, model, label) in enumerate(providers):
        print(f"  [{i}] {label:32s} model={model:34s} 節流 {_interval_for(label):.1f}s/次")
    if args.list:
        return

    if args.provider is not None:
        providers = [providers[args.provider]]

    cases = CASES
    if args.case:
        cases = [c for c in CASES if c["id"] == args.case]
        if not cases:
            sys.exit(f"找不到 case id={args.case!r}")

    # provider index 在切過 --provider 之後會變，所以重建一份帶原始 index 的
    if args.provider is not None:
        tasks = [(args.provider, providers[0][2], c) for c in cases]
        tasks = tasks[:args.limit] if args.limit else tasks
    else:
        tasks = build_tasks(providers, cases, args.limit)

    print(f"\n共 {len(tasks)} 次呼叫\n" + "─" * 78)

    ai_session = Session(engine)      # 給 RAG / prompt_rule 讀
    db_session = None if args.no_db else Session(engine)

    last_call_at: dict[str, float] = {}
    rows = []
    stats = defaultdict(lambda: {"passed": 0, "scored": 0.0, "total": 0, "errors": 0})

    try:
        for n, (pidx, label, case) in enumerate(tasks, 1):
            wait = _interval_for(label) - (time.time() - last_call_at.get(label, 0))
            if wait > 0:
                time.sleep(wait)

            t0 = time.time()
            result = ai_service.process_conversation_with_provider(
                provider_index=pidx,
                user_message=case["message"],
                # context 要複製 —— process_conversation 會 pop 掉內部 key
                current_context=dict(case.get("context") or {}),
                conversation_history=[],
                schedule_list=case_schedules(case),
                session=ai_session,
                force_json=args.json_path,
            )
            dur_ms = (time.time() - t0) * 1000
            last_call_at[label] = time.time()

            passed, score, errors = evaluate(case, result)
            s = stats[label]
            s["total"] += 1
            s["scored"] += score
            if result.get("error"):
                s["errors"] += 1
            elif passed:
                s["passed"] += 1

            mark = "✅" if passed else ("💥" if result.get("error") else "❌")
            print(f"[{n:3d}/{len(tasks)}] {mark} {label:26s} {case['id']:28s} "
                  f"{score:.2f} {dur_ms:6.0f}ms")
            if errors:
                for e in errors:
                    print(f"          └─ {e}")

            # 跟 generate_baseline_report.py 一致：provider error 不入庫，
            # 否則 rate limit 造成的 0 分會被當成模型能力差。
            if db_session and not result.get("error"):
                rows.append(AITestResult(
                    test_case_id=case["id"],
                    category=case["category"],
                    user_message=case["message"],
                    expected_intent=case.get("expect_intent") or "*",
                    expected_complete=bool(case.get("expect_complete")),
                    model_name=f"{label}{'[json]' if args.json_path else ''}+RAG",
                    actual_intent=result.get("intent"),
                    actual_complete=result.get("is_complete"),
                    model_reply=(result.get("reply") or "")[:2000],
                    passed=passed,
                    quality_score=score,
                    duration_ms=dur_ms,
                    errors="\n".join(errors) if errors else None,
                ))

        if db_session and rows:
            for r in rows:
                db_session.add(r)
            db_session.commit()
            print(f"\n已寫入 ai_test_result：{len(rows)} 筆")
        elif db_session:
            print("\n沒有可寫入的結果（全部都是 provider error）")
    finally:
        ai_session.close()
        if db_session:
            db_session.close()

    print("\n" + "═" * 78)
    print(f"{'Provider':32s} {'通過':>8s} {'平均分':>8s} {'error':>7s}")
    print("─" * 78)
    for label, s in stats.items():
        rate = f"{s['passed']}/{s['total']}"
        avg = s["scored"] / s["total"] if s["total"] else 0.0
        print(f"{label:32s} {rate:>8s} {avg:>8.2f} {s['errors']:>7d}")


if __name__ == "__main__":
    main()
