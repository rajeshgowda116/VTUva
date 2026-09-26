import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "backend"))

try:
    from backend.app.chat.intent import detect_intent
except ImportError:
    from app.chat.intent import detect_intent

messages = [
    "hii",
    "hiii",
    "heyy",
    "helloo",
    "good",
    "thank you",
    "okay",
    "what is BFS?",
    "explain BCS502?",
    "what are the advantages of BFS?"
]

for message in messages:
    print(f"{message} -> {detect_intent(message)}")
