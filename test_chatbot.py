#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
챗봇 테스트 스크립트
"""

from rag_chatbot import chat

# 테스트 질문들
test_questions = [
    "어머니의 노후 자금은 보호 받을 수 있어?",
    "상속세가 너무 많이 나올 것 같아서 걱정이에요.",
    "상속세 신고 기한은 언제인가요?",
    "유류분이 뭔가요?"
]

print("=" * 60)
print("챗봇 테스트 시작")
print("=" * 60)

for i, question in enumerate(test_questions, 1):
    print(f"\n[테스트 {i}/{len(test_questions)}]")
    print(f"질문: {question}")
    print("-" * 60)
    
    try:
        result = chat(question)
        print("답변:")
        print(result['answer'])
        print(f"\n참고 출처: {result['num_sources']}개")
        print("=" * 60)
    except Exception as e:
        print(f"오류 발생: {e}")
        print("=" * 60)

print("\n테스트 완료!")

