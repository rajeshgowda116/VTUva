import os
import time
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

models_to_test = [
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-1.5-flash",
]
test_prompt = "What is BFS? Give a 2-sentence summary."

print(f"Testing Gemini Models speed with API Key present: {bool(api_key)}")

for model in models_to_test:
    try:
        llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=0)
        t0 = time.perf_counter()
        first_token_t = None
        full_text = ""
        for chunk in llm.stream(test_prompt):
            if first_token_t is None:
                first_token_t = time.perf_counter() - t0
            full_text += chunk.content
        total_t = time.perf_counter() - t0
        print(f"Model: {model:25s} | TTFT: {first_token_t:.3f}s | Total: {total_t:.3f}s | Response len: {len(full_text)}")
    except Exception as e:
        print(f"Model: {model:25s} | ERROR: {e}")
