import os
import json
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

async def test_keys():
    keys_to_test = [
        ("DEEPSEEK_API_KEY_1", os.getenv("DEEPSEEK_API_KEY_1")),
        ("DEEPSEEK_API_KEY_2", os.getenv("DEEPSEEK_API_KEY_2")),
        ("DEEPSEEK_V4_FLASH_KEY", os.getenv("DEEPSEEK_V4_FLASH_KEY")),
        ("DEEPSEEK_V4_PRO_KEY", os.getenv("DEEPSEEK_V4_PRO_KEY")),
        ("SMART_CHAT_KEY", os.getenv("SMART_CHAT_KEY")),
        ("GEMINI_API_KEY_1", os.getenv("GEMINI_API_KEY_1"))
    ]
    
    for name, key in keys_to_test:
        if not key: continue
        print(f"Testing {name} ({key[:10]}...)")
        client = AsyncOpenAI(api_key=key, base_url="https://api.deepseek.com/v1")
        try:
            resp = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            print(f"SUCCESS with {name}!")
            return
        except Exception as e:
            print(f"FAILED {name}: {e}")

asyncio.run(test_keys())
