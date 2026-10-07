import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "backend"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_system():
    print("\n==================================================")
    print("       VTUva END-TO-END SYSTEM HEALTH CHECK       ")
    print("==================================================")

    # 1. Health check
    res1 = client.get("/api/health")
    print(f"1. Health Check status: {res1.status_code} | {res1.json()}")
    assert res1.status_code == 200

    # 2. RAG Debug Query
    res2 = client.post("/api/chat/debug", json={"question": "Explain Waterfall model", "subject_code": "BCS501"})
    print(f"2. RAG Debug Query status: {res2.status_code}")
    debug_data = res2.json()
    print(f"   - Standalone question: {debug_data.get('rewritten_standalone_question')}")
    print(f"   - Sources retrieved: {debug_data.get('sources_retrieved_count')}")
    assert res2.status_code == 200

    # 3. PYQ Analytics
    res3 = client.get("/api/pyq/analytics?subject_code=BCS501")
    print(f"3. PYQ Analytics status: {res3.status_code}")
    pyq_data = res3.json()
    print(f"   - Unique clusters: {pyq_data.get('unique_question_clusters')}")
    print(f"   - Top repeated count: {len(pyq_data.get('top_repeated_questions', []))}")
    assert res3.status_code == 200

    # 4. Updates check
    res4 = client.post("/api/updates/check")
    print(f"4. Updates check status: {res4.status_code} | {res4.json()}")
    assert res4.status_code == 200

    # 5. Auth Me
    res5 = client.get("/api/auth/me")
    print(f"5. Auth Me status: {res5.status_code} | User USN: {res5.json().get('usn')}")
    assert res5.status_code == 200

    print("==================================================")
    print("   ALL 5 NATIONAL EXPO PRIORITY TESTS PASSED!     ")
    print("==================================================\n")

if __name__ == "__main__":
    test_system()
