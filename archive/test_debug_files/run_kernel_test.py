#!/usr/bin/env python3
"""Run kernel validation test"""
import subprocess
import sys
import os

os.chdir('/Users/knight/Desktop/projects/mcp-testing/lorentzian_classifier')
result = subprocess.run([sys.executable, 'test_kernel_validation.py'], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
sys.exit(result.returncode)
