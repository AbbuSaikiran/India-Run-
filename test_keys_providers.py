import os
import json
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

async def test_keys():
    keys_to_test = [
        ("GEMINI_API_KEY_1", os.getenv("GEMINI_API_KEY_1")),
        ("GEMINI_API_KEY_2", os.getenv("GEMINI_API_KEY_2")),
        ("KIMI_API_KEY_1", os.getenv("KIMI_API_KEY_1")),
        ("GPT_CHAT_LATEST_KEY", os.getenv("GPT_CHAT_LATEST_KEY"))
    ]
    
    for base_url in ["https://api.openai.com/v1", "https://api.groq.com/openai/v1", "https://api.together.xyz/v1", "https://openrouter.ai/api/v1"]:
        print(f"\n--- Testing Base URL: {base_url} ---")
        for name, key in keys_to_test:
            if not key: continue
            print(f"Testing {name} on {base_url}...")
            client = AsyncOpenAI(api_key=key, base_url=base_url)
            try:
                resp = await client.chat.completions.create(
                    model="gpt-3.5-turbo", # Just a placeholder model
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                )
                print(f"SUCCESS with {name} on {base_url}!")
                return
            except Exception as e:
                pass

asyncio.run(test_keys())
