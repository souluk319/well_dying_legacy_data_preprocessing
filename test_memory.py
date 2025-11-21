import uuid
from rag_chatbot_langgraph import chat

def test_memory():
    thread_id = str(uuid.uuid4())
    print(f"Testing with thread_id: {thread_id}")
    
    # Question 1
    q1 = "상속세율이 얼마야?"
    print(f"\nQ1: {q1}")
    r1 = chat(q1, thread_id=thread_id)
    print(f"A1: {r1['answer']}")
    
    # Question 2 (Follow-up)
    q2 = "그걸 어떻게 신고해?" # "그걸" refers to inheritance tax
    print(f"\nQ2: {q2}")
    r2 = chat(q2, thread_id=thread_id)
    print(f"A2: {r2['answer']}")
    
    # Verification
    # The answer should mention "상속세" or reporting procedure
    if "상속세" in r2['answer'] or "신고" in r2['answer']:
        print("\n[PASS] Memory seems to be working (context maintained).")
    else:
        print("\n[FAIL] Memory might not be working.")

if __name__ == "__main__":
    test_memory()
