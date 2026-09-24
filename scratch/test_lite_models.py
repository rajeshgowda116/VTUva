import os
import time
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

models_to_test = [
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash",
]
test_prompt = "What is BFS? Give a 2-sentence summary."

for model in models_to_test:
    try:
        llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
        t0 = time.perf_counter()
        first_token_t = None
        full_text = ""
        for chunk in llm.stream(test_prompt):
            content = chunk.content
            if isinstance(content, list):
                content = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])
            if first_token_t is None and content:
                first_token_t = time.perf_counter() - t0
            full_text += content
        total_t = time.perf_counter() - t0
        print(f"Model: {model:28s} | TTFT: {first_token_t if first_token_t is not None else 0:.3f}s | Total: {total_t:.3f}s | Response len: {len(full_text)}")
    except Exception as e:
        print(f"Model: {model:28s} | ERROR: {e}")
