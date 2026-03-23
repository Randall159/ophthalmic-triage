"""
Silicon Flow API configuration — Qwen3.5-4B
"""
import os

DASHSCOPE_API_KEY = os.environ.get(
    "DASHSCOPE_API_KEY",
    "sk-sflcpctwfzrcpeyebbynvypltxohsqsqswcjqfuejmfsqsss"
)

# Debug: print first/last 10 chars of API key
print(f"[CONFIG] API Key: {DASHSCOPE_API_KEY[:10]}...{DASHSCOPE_API_KEY[-10:]}")

DASHSCOPE_BASE_URL = "https://api.siliconflow.cn/v1"

MODEL = "Qwen/Qwen3-8B"
