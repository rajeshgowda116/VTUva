import sys
import os

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))

from backend.rag.generate import build_prompt, generate_answer
from backend.rag.pipeline import ask_question, CASUAL_RESPONSES

print("=== Testing VTUva Rule Integration ===")

# Test 1: Empty context fallback
ans_empty = generate_answer("What is BFS?", "", subject="BCS501")
print("\nTest 1 (Empty context fallback):")
print(ans_empty)
assert ans_empty == "I couldn't find enough information in the available VTU knowledge base to answer this accurately."

# Test 2: Build prompt with system rules
prompt = build_prompt("Explain BFS", "BFS context data...", subject="BCS501")
print("\nTest 2 (Build prompt header check):")
assert "ABSOLUTE KNOWLEDGE & STRICT GROUNDING RULES" in prompt
print("SUCCESS: System prompt contains strict VTUva grounding rules!")

# Test 3: Out of scope intent response
print("\nTest 3 (Out of scope response check):")
print(CASUAL_RESPONSES["OUT_OF_SCOPE"])
assert "I can help with VTU-related subjects" in CASUAL_RESPONSES["OUT_OF_SCOPE"]

print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY! ✅")
