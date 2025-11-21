#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG 기반 유산상속 상담 챗봇 (LangGraph 버전)
벡터 DB에서 관련 문서를 검색하고 GPT-4o mini로 답변 생성
"""

import os
from pathlib import Path
from typing import TypedDict, List, Dict, Any
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage, AIMessage
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

# === 설정 ===
BASE_DIR = Path(__file__).parent
DB_DIR = BASE_DIR / "chroma_db"

# OpenAI 클라이언트 초기화
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# LangChain OpenAI 클라이언트
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=1000,
    api_key=os.getenv("OPENAI_API_KEY")
)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY")
)

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
    logger.error(f"오류: '{collection_name}' 컬렉션을 찾을 수 없습니다.")
    logger.error("먼저 'python index_data.py'를 실행하여 데이터를 인덱싱하세요.")
    exit(1)

# === LangGraph State 정의 ===
class GraphState(TypedDict):
    """그래프 상태"""
    query: str
    relevant_docs: List[Dict[str, Any]]
    context: str
    answer: str
    sources: List[Dict[str, Any]]
    num_sources: int
    messages: List[BaseMessage] # 대화 기록

# === 노드 함수들 ===
def search_node(state: GraphState) -> GraphState:
    """문서 검색 노드"""
    query = state["query"]
    n_results = 5
    
    # 쿼리 임베딩 생성
    query_embedding = embeddings.embed_query(query)
    
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
    
    return {
        **state,
        "relevant_docs": relevant_docs,
        "num_sources": len(relevant_docs)
    }

def format_context_node(state: GraphState) -> GraphState:
    """컨텍스트 포맷팅 노드"""
    docs = state["relevant_docs"]
    
    if not docs:
        context = "관련 문서를 찾을 수 없습니다."
    else:
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
        
        context = "\n\n---\n\n".join(context_parts)
    
    # sources 추출
    sources = [doc['metadata'] for doc in docs]
    
    return {
        **state,
        "context": context,
        "sources": sources
    }

def generate_node(state: GraphState) -> GraphState:
    """답변 생성 노드"""
    query = state["query"]
    context = state["context"]
    
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
        # 대화 기록이 있으면 포함
        messages = [SystemMessage(content=system_prompt)]
        
        # 이전 대화 기록 추가 (최근 5개만)
        if "messages" in state and state["messages"]:
            messages.extend(state["messages"][-5:])
            
        messages.append(HumanMessage(content=user_prompt))
        
        response = llm.invoke(messages)
        answer = response.content
    except Exception as e:
        logger.error(f"답변 생성 중 오류 발생: {e}")
        answer = f"오류가 발생했습니다: {e}"
    
    # 대화 기록 업데이트
    new_messages = []
    if "messages" in state and state["messages"]:
        new_messages.extend(state["messages"])
    
    new_messages.append(HumanMessage(content=query))
    new_messages.append(AIMessage(content=answer))
    
    return {
        **state,
        "answer": answer,
        "messages": new_messages
    }

# === 그래프 구성 ===
def create_rag_graph():
    """RAG 그래프 생성"""
    workflow = StateGraph(GraphState)
    
    # 노드 추가
    workflow.add_node("search", search_node)
    workflow.add_node("format_context", format_context_node)
    workflow.add_node("generate", generate_node)
    
    # 엣지 추가
    workflow.set_entry_point("search")
    workflow.add_edge("search", "format_context")
    workflow.add_edge("format_context", "generate")
    workflow.add_edge("generate", END)
    
    # 메모리 체크포인터 설정
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)

# 그래프 인스턴스 생성
rag_graph = create_rag_graph()

# === 호환성을 위한 함수 (기존 코드와 호환) ===
def chat(query: str, n_results: int = 5, thread_id: str = "default_thread") -> dict:
    """RAG 챗봇 메인 함수 (LangGraph 사용)"""
    
    # 설정
    config = {"configurable": {"thread_id": thread_id}}
    logger.info(f"Chat started with thread_id: {thread_id}")
    
    # 초기 상태 설정
    # messages는 LangGraph가 자동으로 관리하므로 초기화할 필요 없음 (또는 빈 리스트)
    # 하지만 사용자의 새 질문을 messages에 추가해야 함?
    # LangGraph의 checkpointer를 쓰면 state가 유지됨.
    # 여기서는 GraphState의 messages를 수동으로 관리하는 방식이 아니라,
    # LangGraph의 built-in message handling을 쓰거나, 아니면 우리가 직접 append 해야 함.
    # 간단하게 구현하기 위해, generate_node에서 answer를 생성한 후,
    # 다음 턴을 위해 messages에 (질문, 답변)을 추가하는 로직이 필요함.
    # 하지만 GraphState는 TypedDict라서 append가 안됨. 매번 새로운 리스트를 반환해야 함.
    
    # 현재 구조에서는 generate_node가 messages를 업데이트하지 않고 있음.
    # generate_node에서 messages를 업데이트하도록 수정해야 함.
    # 하지만 여기서는 invoke 호출 시 inputs만 전달함.
    
    initial_state = {
        "query": query,
        "relevant_docs": [],
        "context": "",
        "answer": "",
        "sources": [],
        "num_sources": 0,
        # messages는 checkpointer가 있으면 이전 상태에서 로드됨
        # 하지만 첫 실행이면 비어있음.
        # 여기서는 명시적으로 전달하지 않아도 됨 (checkpointer가 병합함)
    }
    
    # 그래프 실행
    # stream 대신 invoke 사용
    final_state = rag_graph.invoke(initial_state, config=config)
    
    # 대화 기록 업데이트 (수동으로)
    # LangGraph의 add_messages 기능을 쓰지 않고 TypedDict를 쓰므로,
    # 우리가 직접 messages를 업데이트해서 다음 state로 넘겨야 하는데,
    # invoke는 한 번의 실행으로 끝남.
    # checkpointer는 "마지막 상태"를 저장함.
    # 그래서 generate_node가 반환할 때 messages를 업데이트해서 반환해야 함.
    
    return {
        'answer': final_state['answer'],
        'sources': final_state['sources'],
        'num_sources': final_state['num_sources']
    }

def interactive_chat():
    """대화형 챗봇"""
    print("=" * 60)
    print("Well Dying 유산상속 상담 챗봇 (LangGraph)")
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

