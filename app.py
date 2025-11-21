#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Well Dying 유산상속 상담 챗봇 웹 인터페이스
Streamlit을 사용한 간단한 웹 UI
"""

import streamlit as st
from rag_chatbot_langgraph import chat
import time

# 페이지 설정
st.set_page_config(
    page_title="Well Dying 유산 관련 상담 챗봇 테스트",
    page_icon="💬",
    layout="wide"
)

# 제목
st.title("💬 Well Dying 유산상속 상담 챗봇 (LangGraph)")
st.markdown("---")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 채팅 히스토리 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # 출처 정보 표시 (assistant 메시지인 경우)
        if message["role"] == "assistant" and "sources" in message:
            with st.expander("📚 참고 출처"):
                for i, source in enumerate(message["sources"], 1):
                    source_info = f"**{i}.** {source.get('source', '알 수 없음')}"
                    if 'article_id' in source:
                        source_info += f" - {source['article_id']}"
                    if 'title' in source:
                        source_info += f"\n   *{source['title']}*"
                    st.markdown(source_info)

# 사용자 입력
if prompt := st.chat_input("유산상속에 대해 궁금한 점을 물어보세요..."):
    # 사용자 메시지 추가 및 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 세션 ID 생성 (없으면)
    if "thread_id" not in st.session_state:
        import uuid
        st.session_state.thread_id = str(uuid.uuid4())

    # Assistant 답변 생성
    with st.chat_message("assistant"):
        with st.spinner("검색 중..."):
            try:
                result = chat(prompt, thread_id=st.session_state.thread_id)
                
                # 답변 표시
                st.markdown(result['answer'])
                
                # 출처 정보
                with st.expander("📚 참고 출처"):
                    for i, source in enumerate(result['sources'], 1):
                        source_info = f"**{i}.** {source.get('source', '알 수 없음')}"
                        if 'article_id' in source:
                            source_info += f" - {source['article_id']}"
                        if 'title' in source:
                            source_info += f"\n   *{source['title']}*"
                        st.markdown(source_info)
                
                # 세션 상태에 저장
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result['answer'],
                    "sources": result['sources']
                })
                
            except Exception as e:
                error_msg = f"오류가 발생했습니다: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# 사이드바
with st.sidebar:
    st.header("ℹ️ 안내")
    st.markdown("""
    **Well Dying 유산상속 상담 챗봇**에 오신 것을 환영합니다!
    
    이 챗봇은 다음 자료를 기반으로 답변합니다:
    - 민법 상속편
    - 상속·증여 세금상식
    - 상속세 및 증여세법
    - 재산조회 통합처리 안내
    
    **사용 방법:**
    1. 아래 입력창에 질문을 입력하세요
    2. 챗봇이 관련 법률 문서를 검색하여 답변합니다
    3. 참고 출처를 확인할 수 있습니다
    """)
    
    st.markdown("---")
    
    # 채팅 히스토리 초기화 버튼
    if st.button("🗑️ 대화 기록 지우기"):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("**💡 팁:** 구체적인 질문을 하면 더 정확한 답변을 받을 수 있습니다.")

