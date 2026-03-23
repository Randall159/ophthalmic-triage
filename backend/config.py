"""
Silicon Flow API configuration — Qwen3.5-4B
"""
import os

DASHSCOPE_API_KEY = os.environ.get(
    "DASHSCOPE_API_KEY",
    "sk-sflcpctwfzrcpeyebbynvypltxohsqsqswcjqfuejmfsqsss"
)

DASHSCOPE_BASE_URL = "https://api.siliconflow.cn/v1"

MODEL = "Qwen/Qwen3.5-4B"
