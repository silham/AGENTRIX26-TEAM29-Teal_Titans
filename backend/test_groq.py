"""Quick test: verify Groq API key works."""
import json
from app.llm.groq_client import chat

try:
    result = chat(
        [{"role": "user", "content": 'Respond with exactly: {"ok": true}'}],
        json_mode=True,
    )
    print("SUCCESS:", result)
except Exception as e:
    print("ERROR:", type(e).__name__, str(e))
