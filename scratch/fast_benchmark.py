import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

from backend.rag.embeddings import get_embeddings
from backend.rag.retriever import get_retriever, get_vector_store
from backend.rag.generate import get_llm, generate_answer_stream
from backend.rag.contextualizer import is_follow_up_question
from backend.rag.pipeline import prepare_rag_context

def run_benchmarks():
    print("==================================================")
    print("      WARMING UP MODEL SINGLETON INSTANCES       ")
    print("==================================================")
    t_warmup = time.perf_counter()
    get_embeddings()
    get_vector_store()
    get_retriever(k=4)
    get_llm()
    print(f"[WARMUP FINISHED] Took {time.perf_counter() - t_warmup:.3f}s\n")

    test_cases = [
        {
            "name": "TEST 1: Standalone Question",
            "question": "Explain BFS",
            "history": []
        },
        {
            "name": "TEST 2: Follow-up Question",
            "question": "What are its advantages?",
            "history": [{"question": "Explain BFS", "answer": "BFS stands for Breadth First Search."}]
        },
        {
            "name": "TEST 3: Standalone Question",
            "question": "Explain normalization",
            "history": []
        },
        {
            "name": "TEST 4: Follow-up/Explicit Question",
            "question": "Give an example of this",
            "history": [{"question": "Explain normalization", "answer": "Database normalization reduces data redundancy."}]
        }
    ]

    print("==================================================")
    print("       OPTIMIZED LATENCY BENCHMARK RESULTS        ")
    print("==================================================\n")

    for tc in test_cases:
        t_start = time.perf_counter()
        
        # 1. Context Rewrite Step
        standalone_q, sources, context, t_rewrite, t_vector = prepare_rag_context(
            tc["question"], history=tc["history"]
        )

        # 2. Time-to-First-Token (TTFT) and Streaming
        t_first_token = None
        t_stream_start = time.perf_counter()

        for chunk in generate_answer_stream(standalone_q, context):
            if t_first_token is None:
                t_first_token = time.perf_counter() - t_start

        t_total = time.perf_counter() - t_start

        is_fu = is_follow_up_question(tc["question"])
        rewriter_status = "LLM Rewriter Used (Flash Lite)" if (tc["history"] and is_fu) else "Fast Path (Skipped LLM)"

        print(f"--- {tc['name']} ---")
        print(f"  Input Question    : {tc['question']}")
        print(f"  Rewritten Question: {standalone_q}")
        print(f"  Rewriter Mode     : {rewriter_status}")
        print(f"  Context Rewrite T : {t_rewrite:.3f}s")
        print(f"  Vector Search T   : {t_vector:.3f}s")
        print(f"  Time-To-1st-Token : {t_first_token if t_first_token is not None else 0:.3f}s")
        print(f"  Total Stream Time : {t_total:.3f}s\n")

if __name__ == "__main__":
    run_benchmarks()
