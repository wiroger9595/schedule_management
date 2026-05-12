#!/usr/bin/env python3
"""
Generate multi-model baseline markdown report.

Pulls the latest N test results per (model, rag) combination and produces:
  - Per-model no-RAG vs RAG comparison
  - Cross-model comparison
  - Per-category breakdown
  - Top failing cases

Usage:
    cd server && python generate_baseline_report.py
    cd server && python generate_baseline_report.py --n 90 --out ../baseline_reports/baseline_2026-05-13.md
"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session, select
from app.db.database import engine
from app.models.ai_test_result import AITestResult


def parse_model_label(model_name: str) -> tuple[str, bool]:
    """Split 'Cerebras/qwen-3-235b+RAG' into ('Cerebras/qwen-3-235b', True)."""
    if "+RAG" in model_name:
        return model_name.replace("+RAG", ""), True
    return model_name, False


def fetch_grouped(session: Session, n: int):
    """Return {(base_model, with_rag): [results...]}, newest n per group."""
    stmt = select(AITestResult).order_by(AITestResult.created_at.desc())
    rows = session.exec(stmt).all()
    groups: dict[tuple[str, bool], list] = defaultdict(list)
    for r in rows:
        base, with_rag = parse_model_label(r.model_name)
        if len(groups[(base, with_rag)]) < n:
            groups[(base, with_rag)].append(r)
    # reverse to chronological order within each group
    return {k: list(reversed(v)) for k, v in groups.items()}


def pct(passed: int, total: int) -> float:
    return passed * 100 / total if total else 0.0


def summarize(results) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    return {"passed": passed, "total": total, "pct": pct(passed, total)}


def by_category(results) -> dict:
    cats = defaultdict(lambda: {"passed": 0, "total": 0})
    for r in results:
        cats[r.category]["total"] += 1
        if r.passed:
            cats[r.category]["passed"] += 1
    return cats


def render(groups: dict, n: int) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    models = sorted({base for (base, _) in groups.keys()})
    lines = [
        f"# Baseline Report — {today}",
        "",
        f"- Sample target: **{n}** per (model, RAG) combination",
        f"- Models tested: {', '.join(f'`{m}`' for m in models)}",
        "",
        "**Note**: ERRORs (rate limits, timeouts) are NOT stored in DB — "
        "only successful API responses are recorded. So sample sizes below "
        "may be < target if rate limits caused errors.",
        "",
        "## 1. Overall pass rate per model",
        "",
        "| Model | No-RAG | With RAG | Δ (RAG effect) |",
        "|-------|--------|----------|----------------|",
    ]

    summary_rows = []
    for m in models:
        no_rag = summarize(groups.get((m, False), []))
        rag = summarize(groups.get((m, True), []))
        delta = rag["pct"] - no_rag["pct"]
        summary_rows.append((m, no_rag, rag, delta))
        lines.append(
            f"| `{m}` "
            f"| {no_rag['passed']}/{no_rag['total']} ({no_rag['pct']:.0f}%) "
            f"| {rag['passed']}/{rag['total']} ({rag['pct']:.0f}%) "
            f"| **{delta:+.1f}%** |"
        )

    lines += ["", "## 2. Verdict", ""]
    for m, no_rag, rag, delta in summary_rows:
        if rag["total"] == 0:
            verdict = "尚未跑 RAG 版本"
        elif delta > 10:
            verdict = f"RAG 提升明顯（+{delta:.0f}%）→ 繼續補 RAG 範例最划算"
        elif delta < 5:
            verdict = f"RAG 提升很小（{delta:+.0f}%）→ RAG 已飽和，應該改 prompt 或 fine-tune"
        else:
            verdict = f"RAG 有效但有限（{delta:+.0f}%）→ 可繼續補強，也可同時微調 prompt"
        lines.append(f"- **{m}**: {verdict}")

    lines += ["", "## 3. Per-category pass rate (With RAG)", ""]
    if any(rag["total"] > 0 for _, _, rag, _ in summary_rows):
        header = "| Category " + "".join(f"| `{m.split('/')[-1]}` " for m in models) + "|"
        sep = "|---" * (len(models) + 1) + "|"
        lines += [header, sep]

        all_cats = set()
        for m in models:
            for c in by_category(groups.get((m, True), [])):
                all_cats.add(c)

        for cat in sorted(all_cats):
            row = [f"| {cat} "]
            for m in models:
                stats = by_category(groups.get((m, True), [])).get(cat, {"passed": 0, "total": 0})
                if stats["total"]:
                    row.append(f"| {stats['passed']}/{stats['total']} ({pct(stats['passed'], stats['total']):.0f}%) ")
                else:
                    row.append("| — ")
            row.append("|")
            lines.append("".join(row))
    else:
        lines.append("_(no RAG runs yet)_")

    lines += ["", "## 4. Worst categories per model (with RAG)", ""]
    for m in models:
        rag_results = groups.get((m, True), [])
        if not rag_results:
            continue
        lines.append(f"### `{m}`")
        cats = by_category(rag_results)
        worst = sorted(
            [(c, s) for c, s in cats.items() if s["total"] >= 2],
            key=lambda x: x[1]["passed"] / x[1]["total"],
        )[:5]
        for cat, s in worst:
            lines.append(f"- **{cat}** — {s['passed']}/{s['total']} ({pct(s['passed'], s['total']):.0f}%)")
        lines.append("")

    lines += ["## 5. Top 10 failing cases (Cerebras with RAG)", ""]
    cerebras_rag_key = next((k for k in groups if "Cerebras" in k[0] and k[1]), None)
    if cerebras_rag_key:
        lines += [
            "| # | Category | User message | Expected | Actual |",
            "|---|----------|--------------|----------|--------|",
        ]
        fails = [r for r in groups[cerebras_rag_key] if not r.passed][:10]
        for i, r in enumerate(fails, 1):
            msg = (r.user_message or "")[:50].replace("|", "\\|").replace("\n", " ")
            exp = f"{r.expected_intent}/{r.expected_complete}"
            act = f"{r.actual_intent}/{r.actual_complete}"
            lines.append(f"| {i} | {r.category} | {msg} | {exp} | {act} |")
    else:
        lines.append("_(no Cerebras RAG data)_")

    lines += [
        "",
        "## 6. Next-step priority",
        "",
    ]
    if cerebras_rag_key:
        cats = by_category(groups[cerebras_rag_key])
        worst = sorted(
            [(c, s) for c, s in cats.items() if s["total"] >= 2],
            key=lambda x: x[1]["passed"] / x[1]["total"],
        )
        if worst:
            top_cat, top_stat = worst[0]
            lines.append(
                f"優先補 **`{top_cat}`** 類別的 RAG 範例（Cerebras 通過率 "
                f"{top_stat['passed']}/{top_stat['total']} = {pct(top_stat['passed'], top_stat['total']):.0f}%）"
            )
            lines.append("")
            lines.append(f"參考 `server/RAG_TRAINING_GUIDE.md` step 3 建立 `server/app/data/rag_{top_cat}.py`。")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=90)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    session = Session(engine)
    groups = fetch_grouped(session, args.n)
    session.close()

    if not groups:
        print("⚠️  No test results found. Run: python run_test_v2.py first.")
        return

    report = render(groups, args.n)

    if args.out:
        out = Path(args.out)
    else:
        today = datetime.now().strftime("%Y-%m-%d")
        out_dir = Path(__file__).resolve().parent.parent / "baseline_reports"
        out_dir.mkdir(exist_ok=True)
        out = out_dir / f"baseline_{today}.md"

    out.write_text(report, encoding="utf-8")
    print(f"✓ Report written to: {out}")
    for (model, rag), rs in sorted(groups.items()):
        tag = "RAG" if rag else "no-RAG"
        passed = sum(1 for r in rs if r.passed)
        print(f"  [{tag:6}] {model}: {passed}/{len(rs)} ({pct(passed, len(rs)):.0f}%)")


if __name__ == "__main__":
    main()
