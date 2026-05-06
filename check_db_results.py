#!/usr/bin/env python3
"""Check what's in the ai_test_result table."""

import sys
sys.path.insert(0, '/Users/chenrobert/Documents/code_life/schedule_management/server')

from dotenv import load_dotenv
load_dotenv('/Users/chenrobert/Documents/code_life/schedule_management/server/.env-stage')

from sqlmodel import Session, select
from app.db.database import engine
from app.models.ai_test_result import AITestResult

session = Session(engine)

# Count total results
results = session.exec(select(AITestResult)).all()
print(f"Total test results in DB: {len(results)}")

if results:
    print("\nRecent results:")
    for r in results[-5:]:
        print(f"  [{r.test_case_id}] {r.category}: {r.passed} ({r.model_name})")

# Count by category
from sqlalchemy import func
from sqlmodel import SQLModel

categories = {}
for r in results:
    if r.category not in categories:
        categories[r.category] = {"passed": 0, "total": 0}
    categories[r.category]["total"] += 1
    if r.passed:
        categories[r.category]["passed"] += 1

print("\n📊 Results by category:")
for cat, stats in categories.items():
    pct = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
    print(f"  {cat:20s}: {stats['passed']:3d}/{stats['total']:3d} ({pct:5.1f}%)")

session.close()
