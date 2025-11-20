#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG 기반 유산상속 상담 챗봇
벡터 DB에서 관련 문서를 검색하고 GPT-4o mini로 답변 생성
"""

import os
from pathlib import Path
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# === 설정 ===
BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / "chroma_db"

# OpenAI 클라이언트 초기화
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ChromaDB 클라이언트 초기화
chroma_client = chromadb.PersistentClient(
    path=str(DB_DIR),
    settings=Settings(anonymized_telemetry=False)
)

# 컬렉션 가져오기
collection_name = "well_dying_legacy_data"
try:
    collection = chroma_client.get_collection(name=collection_name)
except:
    print(f"오류: '{collection_name}' 컬렉션을 찾을 수 없습니다.")
    print("먼저 'python index_data.py'를 실행하여 데이터를 인덱싱하세요.")
    exit(1)

def get_embedding(text: str, model: str = "text-embedding-3-small") -> list:
    """텍스트를 임베딩 벡터로 변환"""
    response = openai_client.embeddings.create(
        model=model,
        input=text
    )
    return response.data[0].embedding

def search_relevant_docs(query: str, n_results: int = 5) -> list:
    """쿼리와 관련된 문서 검색"""
    # 쿼리 임베딩 생성
    query_embedding = get_embedding(query)
    
    # 벡터 검색
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=['documents', 'metadatas', 'distances']
    )
    
    # 결과 정리
    relevant_docs = []
    if results['documents'] and len(results['documents'][0]) > 0:
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0]
        )):
            relevant_docs.append({
                'text': doc,
                'metadata': metadata,
                'distance': distance,
                'rank': i + 1
            })
    
    return relevant_docs

def format_context(docs: list) -> str:
    """검색된 문서들을 컨텍스트로 포맷팅"""
    if not docs:
        return "관련 문서를 찾을 수 없습니다."
    
    context_parts = []
    for doc in docs:
        metadata = doc['metadata']
        text = doc['text']
        
        # 메타데이터 정보 추가
        source_info = f"[출처: {metadata.get('source', '알 수 없음')}"
        if 'article_id' in metadata:
            source_info += f", {metadata['article_id']}"
        if 'article_title' in metadata:
            source_info += f" - {metadata['article_title']}"
        source_info += "]"
        
        context_parts.append(f"{source_info}\n{text}")
    
    return "\n\n---\n\n".join(context_parts)

def generate_response(query: str, context: str) -> str:
    """GPT-4o mini를 사용하여 답변 생성"""
    system_prompt = """당신은 'well-dying(존엄한 삶의 마무리)'을 주제로 사용자에게 정보와 정서적 안정감을 제공하는 챗봇입니다.
사용자의 질문에 대해 제공된 법률 문서와 안내 자료를 바탕으로 정확하고 친절하게 답변해주세요.

[핵심 원칙]
1. 과도한 감정 표현, 동정, 위로를 사용하지 않는다.
2. 사용자가 말하지 않은 감정이나 상태를 추측하거나 단정하지 않는다.
3. 말투는 따뜻하되 절제되어 있으며, 안정적이고 담백한 어조를 유지한다.
4. 해결책을 강요하지 않고, 선택권을 사용자에게 돌려준다.
5. 사용자가 편안함을 느낄 수 있도록, 필요한 만큼만 부드럽게 안내한다.
6. 전문 분야(법률, 의료 등)는 단정적인 조언 대신 일반적 정보와 안내 중심으로 설명한다.

[금지 표현 예시]
- "요즘 많이 힘드셨죠…"
- "괜찮아요. 다 잘될 거예요."
- "정말 많이 힘드셨겠네요."
- "걱정하지 마세요."
- 사용자의 감정을 추측하는 표현 전부

[지향 표현 스타일]
- 고요하고 차분한 말투
- 존중, 선택권 제공, 과장 없는 친절함
- "원하시면…", "필요하신 만큼…", "이런 방향으로도 살펴볼 수 있어요" 같은 방식의 옵션 제공
- 사용자가 말한 내용 안에서만 공감하거나 정리

[예시 말투]
- "말해줘서 고마워요. 천천히 필요한 부분부터 이야기해도 괜찮아요."
- "이 부분에서 어떤 정보를 알고 싶은지 편한 만큼 알려주세요."
- "원하신다면 ○○와 같은 정보부터 차분히 정리해드릴 수 있어요."
- "부담 없이, 알고 싶은 범위까지만 말씀해주세요."

위 모든 규칙은 모든 응답에서 반드시 적용한다.

[답변 가이드라인]
1. 먼저 제공된 문서 내용을 우선적으로 사용하여 답변하세요
2. 법률 조문이 있으면 조문 번호를 명시하세요
3. 출처를 명확히 표시하세요
4. 제공된 문서에 관련 정보가 없거나 부족한 경우, 당신의 일반 지식(유산상속, 재산관리, 노후자금 보호 등)을 활용하여 도움이 되는 답변을 제공하세요
5. 단, 일반 지식을 사용할 때는 "일반적으로", "보통", "일반적인 방법으로는" 등의 표현을 사용하여 문서 기반 정보와 구분하세요
6. 한국어로 답변하세요"""

    user_prompt = f"""다음은 유산상속 관련 문서들입니다:

{context}

사용자 질문: {query}

위 문서들을 우선적으로 참고하여 답변하되, 문서에 관련 정보가 없거나 부족한 경우에는 당신의 일반 지식을 활용하여 도움이 되는 답변을 제공해주세요. 
문서 기반 정보와 일반 지식을 구분하여 명확하게 답변해주세요."""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"오류가 발생했습니다: {e}"

def chat(query: str, n_results: int = 5) -> dict:
    """RAG 챗봇 메인 함수"""
    # 관련 문서 검색
    relevant_docs = search_relevant_docs(query, n_results)
    
    # 컨텍스트 생성
    context = format_context(relevant_docs)
    
    # 답변 생성
    answer = generate_response(query, context)
    
    return {
        'answer': answer,
        'sources': [doc['metadata'] for doc in relevant_docs],
        'num_sources': len(relevant_docs)
    }

def interactive_chat():
    """대화형 챗봇"""
    print("=" * 60)
    print("Well Dying 유산상속 상담 챗봇")
    print("=" * 60)
    print("질문을 입력하세요. 종료하려면 'quit' 또는 'exit'를 입력하세요.\n")
    
    while True:
        query = input("질문: ").strip()
        
        if query.lower() in ['quit', 'exit', '종료', 'q']:
            print("상담을 종료합니다. 감사합니다!")
            break
        
        if not query:
            continue
        
        print("\n검색 중...")
        result = chat(query)
        
        print("\n" + "-" * 60)
        print("답변:")
        print(result['answer'])
        print("\n참고 출처:")
        for i, source in enumerate(result['sources'], 1):
            source_info = f"{i}. {source.get('source', '알 수 없음')}"
            if 'article_id' in source:
                source_info += f" - {source['article_id']}"
            if 'title' in source:
                source_info += f" ({source['title']})"
            print(f"  {source_info}")
        print("-" * 60 + "\n")

if __name__ == "__main__":
    interactive_chat()

