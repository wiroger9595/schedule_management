#!/usr/bin/env python3
"""Run full test suite and save results."""

import subprocess
import sys

# Run the optimize_ai_assistant test with HuggingFace (index 0)
print("🚀 Running full 90-test suite with HuggingFace...\n")

result = subprocess.run(
    [sys.executable, "optimize_ai_assistant.py", "--models", "0", "--report", "ai_test_report_hf.html"],
    cwd="/Users/chenrobert/Documents/code_life/schedule_management"
)

sys.exit(result.returncode)
