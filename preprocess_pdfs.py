#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 파일들을 RAG 챗봇용 데이터베이스에 넣을 수 있도록 전처리하는 스크립트
"""

import os
import re
import json
from pathlib import Path
import fitz  # PyMuPDF

# === 경로 설정 ===
BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / "processed"
OUT_DIR.mkdir(exist_ok=True)

print("BASE_DIR:", BASE_DIR)
print("OUT_DIR:", OUT_DIR)

# === PDF → 텍스트 추출 ===
def extract_text_from_pdf(path: Path) -> str:
    """PDF 파일에서 텍스트를 추출합니다."""
    doc = fitz.open(str(path))
    texts = []
    for page in doc:
        texts.append(page.get_text("text") or "")
    doc.close()
    return "\n".join(texts)

# === 제어 문자 제거 ===
def remove_control_chars(text: str) -> str:
    """
    제어 문자를 제거합니다 (개행, 탭 제외).
    """
    # 개행(\n), 탭(\t), 캐리지 리턴(\r)은 유지하고 나머지 제어 문자 제거
    # 유니코드 제어 문자 범위: \x00-\x1f, \x7f-\x9f
    # 하지만 \n(0x0a), \t(0x09), \r(0x0d)는 유지
    result = []
    for char in text:
        code = ord(char)
        # 개행, 탭, 캐리지 리턴은 유지
        if char in '\n\t\r':
            result.append(char)
        # 나머지 제어 문자는 제거
        elif code < 32 or (127 <= code <= 159):
            continue
        # Private Use Area 제거 (U+E000~U+F8FF)
        elif 0xE000 <= code <= 0xF8FF:
            continue
        else:
            result.append(char)
    return ''.join(result)

# === 기본 텍스트 정리 ===
def clean_basic(text: str) -> str:
    """
    PDF에서 추출한 텍스트를 정리합니다.
    - 제어 문자 제거
    - 한글 단어 중간 개행 복원
    - 불필요한 공백/개행 정리
    """
    # 제어 문자 제거 (개행, 탭 제외)
    text = remove_control_chars(text)
    
    # CR, FF를 일반 개행으로 통일
    text = text.replace("\r", "\n").replace("\f", "\n")

    # (1) 한글 + 개행(1개 이상) + 한글 → 줄바꿈 제거 (단어 중간 개행 복원)
    #    예: "어느 하\n나에" 또는 "상속\n\n민법권" → "어느 하나에" 또는 "상속민법권"
    #    단, 문단 구분을 위해 "\n\n" 다음에 공백이나 다른 문자가 오는 경우는 제외
    text = re.sub(r'([가-힣])\n+([가-힣])', r'\1\2', text)
    
    # (1-1) 숫자 + 개행 + 숫자도 복원 (예: "제1\n\n2조" → "제12조")
    text = re.sub(r'(\d)\n+(\d)', r'\1\2', text)

    # (2) 3줄 이상 연속 개행 → 2줄로 축소 (문단 구분)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # (3) 문단이 아닌 단순 줄바꿈(한 줄짜리 개행)은 공백으로 변경
    #     즉, "\n\n"은 그대로 두고, 그 밖의 단일 "\n"만 공백으로 치환
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

    # (4) 다시 한 번 3줄 이상 개행 정리
    text = re.sub(r'\n{3,}', '\n\n', text)

    # (5) 탭/여러 공백 → 한 칸
    text = re.sub(r'[ \t]+', ' ', text)

    # (6) 앞뒤 공백/개행 정리
    return text.strip()

# === 최종 청크 정리 ===
def clean_chunk_text(text: str) -> str:
    """
    최종 청크 텍스트를 정리합니다.
    - 제어 문자 제거
    - 단어 중간 개행 복원 (추가)
    - 이상한 특수문자 정리
    - 연속된 공백 정리
    """
    # 제어 문자 제거
    text = remove_control_chars(text)
    
    # 한글 단어 중간 개행 복원 (추가 안전장치)
    text = re.sub(r'([가-힣])\n+([가-힣])', r'\1\2', text)
    text = re.sub(r'(\d)\n+(\d)', r'\1\2', text)
    
    # 이상한 특수문자 정리 (숫자 뒤의 ^, &, * 제거)
    # 예: "3^" → "3", "3&" → "3", "3*" → "3"
    text = re.sub(r'(\d+)[\^&\*]', r'\1', text)
    
    # 잘못 분리된 단어 복원
    # 예: "상속민법권" → "상속권" (PDF에서 "상속\n\n민법권"으로 잘못 추출된 경우)
    text = re.sub(r'상속민법권', '상속권', text)
    text = re.sub(r'상속민법', '상속', text)  # 다른 패턴도 처리
    
    # PDF 헤더/푸터 제거 (숫자나 한글 다음에 "민법" 단어가 나오는 경우)
    # 예: "2분의 1\n\n민법 3" → "2분의 1\n\n3"
    # 예: "단독상속인이 된다.\n\n민법 ②" → "단독상속인이 된다.\n\n②"
    text = re.sub(r'([가-힣\d])\n+민법\s+([①②③④⑤⑥⑦⑧⑨⑩]|\d)', r'\1\n\n\2', text)
    text = re.sub(r'([가-힣\d])\s+민법\s+([①②③④⑤⑥⑦⑧⑨⑩]|\d)', r'\1 \2', text)
    # "민법" 단독으로 남아있는 경우도 제거
    text = re.sub(r'\n+민법\s+([①②③④⑤⑥⑦⑧⑨⑩]|\d)', r'\n\n\1', text)
    
    # 잘못 붙은 숫자 분리 (예: "2분의 12." → "2분의 1\n\n2.")
    # 패턴: "분의 1" 다음에 바로 숫자가 오는 경우
    # 단, "100분의 10", "100분의 100" 같은 경우는 제외
    
    # 먼저 잘못된 패턴들을 복원
    # "0분의 10" → "100분의 10" (앞의 "1"이 빠진 경우)
    text = re.sub(r'0분의\s*10\b', '100분의 10', text)
    text = re.sub(r'0분의\s*100\b', '100분의 100', text)
    
    # "10100분의 10" 같은 잘못된 패턴은 "100분의 10"으로 복원
    text = re.sub(r'10100분의\s*10\b', '100분의 10', text)
    
    # 이제 "100분의 10", "100분의 100" 같은 정상 패턴을 보호
    text = re.sub(r'100\s*분의\s*10\b', '__PROTECT_100분의10__', text)
    text = re.sub(r'100\s*분의\s*100\b', '__PROTECT_100분의100__', text)
    text = re.sub(r'100분의\s*10\b', '__PROTECT_100분의10__', text)
    text = re.sub(r'100분의\s*100\b', '__PROTECT_100분의100__', text)
    
    # 이제 나머지 "분의 1" 다음 숫자 분리
    # 패턴: 숫자분의 1 + 숫자 (예: "2분의 12", "3분의 14")
    # 단, "100분의 1"로 시작하는 것은 제외하고, 보호 마커가 있는 부분도 제외
    # 검증 스크립트 패턴: r'\d분의\s*1\d+'
    # 이 패턴에 맞는 모든 경우를 처리하되, "100분의 10", "100분의 100"은 이미 보호됨
    
    # "분의 1" 다음에 바로 숫자가 오는 모든 경우 분리
    # 단, 보호 마커 내부는 제외
    def split_fraction(match):
        full_match = match.group(0)
        # 보호 마커가 포함되어 있으면 그대로 반환
        if '__PROTECT_' in full_match:
            return full_match
        # "100분의 1"로 시작하는 경우는 제외 (이미 보호됨)
        if full_match.startswith('100분의 1') or full_match.startswith('100분의1'):
            return full_match
        # 나머지는 분리
        return re.sub(r'(\d+분의\s*1)(\d+)', r'\1\n\n\2', full_match)
    
    # 모든 "분의 1" 다음 숫자 패턴 찾아서 처리
    text = re.sub(r'\d+분의\s*1\d+', split_fraction, text)
    
    # 보호된 패턴 복원
    text = text.replace('__PROTECT_100분의10__', '100분의 10')
    text = text.replace('__PROTECT_100분의100__', '100분의 100')
    
    # "100분의 1\n\n0" 같은 잘못된 분리 복원
    # "100분의 100"이 "100분의 1\n\n00"으로 잘못 분리된 경우
    text = re.sub(r'100분의\s*1\n+\s*00', '100분의 100', text)
    text = re.sub(r'100분의\s*1\s+00', '100분의 100', text)
    # "100분의 10"이 "100분의 1\n\n0"으로 잘못 분리된 경우 (다음에 숫자나 문자가 오는 경우)
    text = re.sub(r'100분의\s*1\n+\s*0([^\d]|$)', r'100분의 10\1', text)
    text = re.sub(r'100분의\s*1\s+0([^\d]|$)', r'100분의 10\1', text)
    # "100분의 10"이 "100분의 1\n\n0"으로 잘못 분리된 경우 (다음에 숫자가 오는 경우도)
    text = re.sub(r'100분의\s*1\n+\s*0(\d)', r'100분의 10\1', text)
    text = re.sub(r'100분의\s*1\s+0(\d)', r'100분의 10\1', text)
    
    # "100분의 201)" → "100분의 20\n\n1)" (100분의 20 다음에 1)이 오는 경우)
    text = re.sub(r'100분의\s*20(\d+)', r'100분의 20\n\n\1', text)
    
    # "및" 뒤 공백 추가
    # 예: "및제" → "및 제", "및증" → "및 증"
    text = re.sub(r'및([가-힣])', r'및 \1', text)
    
    # 연속된 공백 정리 (3개 이상 → 2개)
    text = re.sub(r' {3,}', '  ', text)
    
    # 앞뒤 공백 정리
    return text.strip()

# === 법령 본문 전용 추가 클리닝 ===
def clean_law_body(body: str, article_id: str) -> str:
    """
    법령 본문의 꼬리 부분을 정리합니다.
    - 국가법령정보센터 스타일의 푸터 제거
    - [시행일: ...] 뒤의 불필요한 꼬리 제거
    """
    # 1) 국가법령정보센터 푸터 제거
    body = re.sub(r'법제처\s+\d+\s+국가법령정보센터', '', body)

    # 2) [시행일: ...] 뒤에 이번 조문 번호가 나오면서 절/관 제목 등이 붙는 패턴 제거
    pattern_tail = (
        r'(\[본조신설[^]]*]\s*)?'  # [본조신설 ...] (있을 수도 있고, 없을 수도 있고)
        r'(\[시행일:[^]]*])'       # [시행일: ...]
        r'\s*' + re.escape(article_id) + r'.*$'  # 그 뒤에 같은 조문번호 + 나머지 꼬리
    )
    body = re.sub(pattern_tail, r'\1\2', body).strip()

    return body

# === 법령형(제000조) 청킹 ===
def chunk_law(text: str, source_file: str, category: str, id_prefix: str, max_chunk_size: int = 1200):
    """
    법령 문서를 "제000조" 형식 기준으로 청킹합니다.
    너무 긴 조문은 추가로 문단 단위로 분할합니다.
    
    Args:
        max_chunk_size: 조문이 이 길이를 초과하면 추가 분할 (기본 1500자)
    """
    # 국가법령정보센터 푸터 제거
    text = re.sub(r'법제처\s+\d+\s+국가법령정보센터', '', text)

    # "제000조(조문제목)" 형식 기준 분리
    pattern = r'(제\d+조(?:의\d+)?\s*\([^\)]*\))'
    parts = re.split(pattern, text)

    chunks = []
    current_title = None

    for part in parts:
        if not part.strip():
            continue

        # 새 조문 헤더
        if re.match(r'^제\d+조', part.strip()):
            current_title = part.strip()
        else:
            if current_title is None:
                continue

            header = current_title
            article_id = header.split('(')[0].strip()   # 예: "제1004조의2"
            m = re.search(r'\(([^\)]+)\)', header)
            article_title = m.group(1).strip() if m else ""

            body = part.strip()
            if not body:
                continue

            # 조문 본문 전용 클리닝
            body = clean_law_body(body, article_id)
            
            # 긴 각주가 있으면 본문과 분리
            # 패턴: [헌법불합치...], [본조신설...] 등 긴 각주 (80자 이상)
            long_footnote_pattern = r'(\[[^\]]{80,}\])'
            long_footnotes = re.findall(long_footnote_pattern, body)
            
            if long_footnotes:
                # 본문에서 긴 각주 제거
                main_body = body
                for footnote in long_footnotes:
                    main_body = main_body.replace(footnote, '', 1)
                main_body = main_body.strip()
                
                # 본문과 각주를 별도로 처리
                # 본문이 있으면 먼저 추가
                if main_body and len(main_body) >= 20:
                    body = main_body
                else:
                    # 본문이 너무 짧으면 각주 포함
                    body = body.strip()
            
            # 조문이 너무 길면 추가 분할
            # 단, 각주/부칙이 긴 경우도 고려하여 더 작게 분할
            # 500자 이상이면 무조건 분할
            if len(body) > 500:
                # 문단 단위로 분할 (2줄 이상 연속 개행 기준)
                paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
                
                sub_chunks = []
                buf = ""
                
                for para in paragraphs:
                    # 문단 자체가 너무 길면 문장 단위로도 분할
                    # 500자 이상이면 무조건 분할
                    if len(para) > 500:
                        # 먼저 현재 버퍼 저장
                        if buf:
                            sub_chunks.append(buf)
                            buf = ""
                        
                        # 문장 단위로 분할 (한글 마침표, 숫자 마침표 등)
                        # 단, 날짜 형식(예: "2017. 12. 19.")이나 태그(예: "<개정 ...>")는 보호
                        
                        # 먼저 보호할 패턴을 임시 마커로 치환 (역순으로 처리하여 인덱스 문제 방지)
                        protected = {}
                        counter = 0
                        
                        # 태그 패턴 보호 (예: "<개정 ...>" 또는 "[본조신설 ...]")
                        tag_pattern = r'<[^>]+>|\[[^\]]+\]'
                        tag_matches = list(re.finditer(tag_pattern, para))
                        for match in reversed(tag_matches):  # 역순으로 처리
                            marker = f"__TAG_{counter}__"
                            protected[marker] = match.group(0)
                            para = para[:match.start()] + marker + para[match.end():]
                            counter += 1
                        
                        # 날짜 패턴 보호 (예: "2017. 12. 19." 또는 "2020. 12. 22.")
                        # 태그 보호 후에 처리
                        date_pattern = r'\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.'
                        date_matches = list(re.finditer(date_pattern, para))
                        for match in reversed(date_matches):  # 역순으로 처리
                            marker = f"__DATE_{counter}__"
                            protected[marker] = match.group(0)
                            para = para[:match.start()] + marker + para[match.end():]
                            counter += 1
                        
                        # 이제 문장 단위로 분할
                        sentences = re.split(r'([.!?。]\s+|\.\s+)', para)
                        sentence_parts = []
                        for i in range(0, len(sentences), 2):
                            if i < len(sentences):
                                sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
                                sentence_parts.append(sentence.strip())
                        
                        # 보호된 패턴 복원 (전체 문장 리스트에 대해)
                        for j, sent in enumerate(sentence_parts):
                            for marker, original in protected.items():
                                sent = sent.replace(marker, original)
                            sentence_parts[j] = sent
                        
                        # 문장들을 합치면서 청크 생성 (최대 500자)
                        # 단일 문장이 500자 초과면 더 세밀하게 분할
                        for sent in sentence_parts:
                            # 단일 문장이 500자 초과면 쉼표나 연결어 기준으로 분할
                            if len(sent) > 500:
                                # 쉼표, 그리고, 또는 등으로 분할
                                parts = re.split(r'([,，]\s+|그리고|또는|및)', sent)
                                for part in parts:
                                    if part.strip():
                                        if len(buf) + len(part) + 1 <= 500:
                                            buf = (buf + " " + part).strip() if buf else part
                                        else:
                                            if buf:
                                                sub_chunks.append(buf)
                                            buf = part
                            elif len(buf) + len(sent) + 1 <= 500:
                                buf = (buf + " " + sent).strip() if buf else sent
                            else:
                                if buf:
                                    sub_chunks.append(buf)
                                buf = sent
                    elif len(buf) + len(para) + 2 <= 500:
                        buf = (buf + "\n\n" + para).strip() if buf else para
                    else:
                        # 버퍼가 있으면 저장하고 새로 시작
                        if buf:
                            sub_chunks.append(buf)
                        # 문단 자체가 500자 초과면 문장 단위로 분할
                        if len(para) > 500:
                            sentences = re.split(r'([.!?。]\s+|\.\s+)', para)
                            sentence_parts = []
                            for i in range(0, len(sentences), 2):
                                if i < len(sentences):
                                    sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
                                    sentence_parts.append(sentence.strip())
                            
                            for sent in sentence_parts:
                                if len(sent) > 500:
                                    parts = re.split(r'([,，]\s+|그리고|또는|및)', sent)
                                    for part in parts:
                                        if part.strip():
                                            if len(part) > 500:
                                                sub_chunks.append(part[:500])
                                                if len(part) > 500:
                                                    sub_chunks.append(part[500:])
                                            else:
                                                sub_chunks.append(part)
                                else:
                                    sub_chunks.append(sent)
                        else:
                            buf = para
                
                if buf:
                    # 버퍼가 500자 초과면 분할
                    if len(buf) > 500:
                        # 문장 단위로 분할
                        sentences = re.split(r'([.!?。]\s+|\.\s+)', buf)
                        sentence_parts = []
                        for i in range(0, len(sentences), 2):
                            if i < len(sentences):
                                sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
                                sentence_parts.append(sentence.strip())
                        
                        temp_buf = ""
                        for sent in sentence_parts:
                            if len(temp_buf) + len(sent) + 1 <= 500:
                                temp_buf = (temp_buf + " " + sent).strip() if temp_buf else sent
                            else:
                                if temp_buf:
                                    sub_chunks.append(temp_buf)
                                temp_buf = sent
                        if temp_buf:
                            sub_chunks.append(temp_buf)
                    else:
                        sub_chunks.append(buf)
                
                # 분할된 청크들을 추가
                for i, sub_body in enumerate(sub_chunks):
                    cleaned_text = clean_chunk_text(sub_body)
                    # 너무 짧은 청크는 제외 (20자 미만)
                    # 500자 초과면 다시 분할
                    if len(cleaned_text) > 500:
                        # 문장 단위로 다시 분할
                        sentences = re.split(r'([.!?。]\s+|\.\s+)', cleaned_text)
                        sentence_parts = []
                        for j in range(0, len(sentences), 2):
                            if j < len(sentences):
                                sentence = sentences[j] + (sentences[j+1] if j+1 < len(sentences) else "")
                                sentence_parts.append(sentence.strip())
                        
                        temp_buf = ""
                        for sent in sentence_parts:
                            if len(temp_buf) + len(sent) + 1 <= 500:
                                temp_buf = (temp_buf + " " + sent).strip() if temp_buf else sent
                            else:
                                if temp_buf and len(temp_buf) >= 20:
                                    # 기존 청크 추가 로직
                                    chunk_num = len(chunks) + 1
                                    chunk_record = {
                                        "id": f"{id_prefix}_{chunk_num:04d}",
                                        "title": f"{remove_control_chars(article_title).strip()} {article_id}" if article_title else article_id,
                                        "text": temp_buf,
                                        "source": source_file,
                                        "category": category
                                    }
                                    if article_id:
                                        chunk_record["article_id"] = article_id
                                    if article_title:
                                        chunk_record["article_title"] = remove_control_chars(article_title).strip()
                                    if len(sub_chunks) > 1:
                                        chunk_record["sub_chunk"] = i + 1
                                    chunks.append(chunk_record)
                                temp_buf = sent
                        if temp_buf and len(temp_buf) >= 20:
                            chunk_num = len(chunks) + 1
                            chunk_record = {
                                "id": f"{id_prefix}_{chunk_num:04d}",
                                "title": f"{remove_control_chars(article_title).strip()} {article_id}" if article_title else article_id,
                                "text": temp_buf,
                                "source": source_file,
                                "category": category
                            }
                            if article_id:
                                chunk_record["article_id"] = article_id
                            if article_title:
                                chunk_record["article_title"] = remove_control_chars(article_title).strip()
                            if len(sub_chunks) > 1:
                                chunk_record["sub_chunk"] = i + 1
                            chunks.append(chunk_record)
                    elif len(cleaned_text) >= 20:
                        # law 모드 - 필수 필드 + 선택적 필드 (값이 있을 때만 포함)
                        chunk_num = len(chunks) + 1
                        chunk_record = {
                            "id": f"{id_prefix}_{chunk_num:04d}",
                            "title": f"{remove_control_chars(article_title).strip()} {article_id}" if article_title else article_id,
                            "text": cleaned_text,
                            "source": source_file,
                            "category": category
                        }
                        
                        # 선택적 필드는 값이 있을 때만 추가
                        if article_id:
                            chunk_record["article_id"] = article_id
                        if article_title:
                            chunk_record["article_title"] = remove_control_chars(article_title).strip()
                        if len(sub_chunks) > 1:
                            chunk_record["sub_chunk"] = i + 1
                        
                        chunks.append(chunk_record)
            else:
                cleaned_text = clean_chunk_text(body)
                # 너무 짧은 청크는 제외 (20자 미만)
                if len(cleaned_text) >= 20:
                    # law 모드 - 필수 필드 + 선택적 필드 (값이 있을 때만 포함)
                    chunk_num = len(chunks) + 1
                    chunk_record = {
                        "id": f"{id_prefix}_{chunk_num:04d}",
                        "title": f"{remove_control_chars(article_title).strip()} {article_id}" if article_title else article_id,
                        "text": cleaned_text,
                        "source": source_file,
                        "category": category
                    }
                    
                    # 선택적 필드는 값이 있을 때만 추가
                    if article_id:
                        chunk_record["article_id"] = article_id
                    if article_title:
                        chunk_record["article_title"] = remove_control_chars(article_title).strip()
                    
                    chunks.append(chunk_record)

    return chunks

# === 심플 문단+길이 청킹 ===
def chunk_simple(text: str, source_file: str, category: str, id_prefix: str):
    """
    일반 문서를 문단 기준으로 청킹합니다.
    - 최소 길이: 300자
    - 최대 길이: 900자
    """
    # 문단 기준 분리
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    buf = ""
    min_len = 300
    max_len = 500  # law 모드와 일관성 유지

    for p in paragraphs:
        # 문단 자체가 너무 길면 문장 단위로 분할
        if len(p) > max_len:
            # 먼저 현재 버퍼 저장
            if buf and len(buf) >= min_len:
                chunks.append(buf)
            buf = ""
            
            # 문장 단위로 분할
            sentences = re.split(r'([.!?。]\s+|\.\s+)', p)
            sentence_parts = []
            for i in range(0, len(sentences), 2):
                if i < len(sentences):
                    sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
                    sentence_parts.append(sentence.strip())
            
            # 문장들을 합치면서 청크 생성 (최대 500자)
            # 단일 문장이 500자 초과면 더 세밀하게 분할
            for sent in sentence_parts:
                # 단일 문장이 500자 초과면 쉼표나 연결어 기준으로 분할
                if len(sent) > 500:
                    # 쉼표, 그리고, 또는 등으로 분할
                    parts = re.split(r'([,，]\s+|그리고|또는|및)', sent)
                    for part in parts:
                        if part.strip():
                            if len(buf) + len(part) + 1 <= 500:
                                buf = (buf + " " + part).strip() if buf else part
                            else:
                                if buf and len(buf) >= min_len:
                                    chunks.append(buf)
                                buf = part
                elif len(buf) + len(sent) + 1 <= 500:
                    buf = (buf + " " + sent).strip() if buf else sent
                else:
                    if buf and len(buf) >= min_len:
                        chunks.append(buf)
                    buf = sent
        elif len(buf) + len(p) + 1 <= 500:
            buf = (buf + " " + p).strip()
        else:
            if len(buf) >= min_len:
                chunks.append(buf)
            buf = p

    if buf and len(buf) >= min_len:
        chunks.append(buf)

    records = []
    for i, c in enumerate(chunks, start=1):
        cleaned_text = clean_chunk_text(c)
        # 너무 짧은 청크는 제외 (20자 미만)
        if len(cleaned_text) >= 20:
            # 제목 생성 (제어 문자 제거)
            title = cleaned_text[:50].replace("\n", " ").replace("\t", " ")
            
            # simple 모드는 기본 필드만 포함
            records.append({
                "id": f"{id_prefix}_{i:04d}",
                "title": remove_control_chars(title).strip(),
                "text": cleaned_text,
                "source": source_file,
                "category": category
            })
    return records

# === 파일별 설정 ===
files_config = [
    {
        "raw_name": "1. 민법 상속편.pdf",
        "out_name": "1_minbeob_sangsok_chunks.jsonl",
        "mode": "law",
        "id_prefix": "minlaw",
        "category": "법령_민법_상속"
    },
    {
        "raw_name": "2. 국세청-상속·증여 세금상식1.pdf",
        "out_name": "2_segeumsangsik_I_simple.jsonl",
        "mode": "simple",
        "id_prefix": "tax1",
        "category": "세금_안내"
    },
    {
        "raw_name": "3. 국세청-상속·증여 세금상식Ⅱ.pdf",
        "out_name": "3_segeumsangsik_II_simple.jsonl",
        "mode": "simple",
        "id_prefix": "tax2",
        "category": "세금_안내"
    },
    {
        "raw_name": "4. 사망자 및 피후견인 등 재산조회 통합처리 신청(안심상속)웹스크래핑.pdf",
        "out_name": "4_ansimsangsok_web_simple.jsonl",
        "mode": "simple",
        "id_prefix": "ansim",
        "category": "안심상속_안내"
    },
    {
        "raw_name": "5. 사망자 및 피후견인 등 재산조회 통합처리에 관한 기준(행정안전).pdf",
        "out_name": "5_jaesanjohoe_rule_chunks.jsonl",
        "mode": "law",
        "id_prefix": "rule",
        "category": "행정기준"
    },
    {
        "raw_name": "6. 상속세 및 증여세법.pdf",
        "out_name": "6_sangsokse_beob_chunks.jsonl",
        "mode": "law",
        "id_prefix": "taxlaw",
        "category": "법령_상속세증여세"
    },
]

# === 메인 루프: 6개 PDF 자동 전처리 ===
def main():
    total_records = 0
    
    for cfg in files_config:
        raw_path = BASE_DIR / cfg["raw_name"]
        out_path = OUT_DIR / cfg["out_name"]

        print("\n" + "="*50)
        print(f"처리 시작: {raw_path.name}")
        
        if not raw_path.exists():
            print(f"  [ERROR] 파일이 없음: {raw_path}")
            continue

        try:
            # 1) PDF → 텍스트
            print("  → PDF 텍스트 추출 중...")
            raw_text = extract_text_from_pdf(raw_path)
            text = clean_basic(raw_text)

            # 2) 모드별 청킹
            print(f"  → {cfg['mode']} 모드로 청킹 중...")
            if cfg["mode"] == "law":
                law_chunks = chunk_law(
                    text,
                    source_file=cfg["raw_name"],
                    category=cfg["category"],
                    id_prefix=cfg["id_prefix"]
                )
                # law 모드는 id를 여기서 붙여서 JSONL 레코드로 변환
                records = []
                for i, ch in enumerate(law_chunks, start=1):
                    article_title = ch.get('article_title', '')
                    article_id = ch.get('article_id', '')
                    sub_chunk = ch.get('sub_chunk')
                    
                    # 제목 생성 (제어 문자 제거)
                    title = f"{article_title} {article_id}".strip()
                    if sub_chunk:
                        title += f" (부분 {sub_chunk})"
                    title = remove_control_chars(title).strip()
                    
                    # law 모드 - 필수 필드 + 선택적 필드 (값이 있을 때만 포함)
                    record = {
                        "id": f"{cfg['id_prefix']}_{i:04d}",
                        "title": title,
                        "text": ch["text"],
                        "source": ch["source"],
                        "category": ch["category"]
                    }
                    
                    # 선택적 필드는 값이 있을 때만 추가
                    if article_id:
                        record["article_id"] = article_id
                    if article_title:
                        record["article_title"] = remove_control_chars(article_title).strip()
                    if sub_chunk:
                        record["sub_chunk"] = sub_chunk
                    
                    records.append(record)
            else:
                records = chunk_simple(
                    text,
                    source_file=cfg["raw_name"],
                    category=cfg["category"],
                    id_prefix=cfg["id_prefix"],
                )

            # 3) JSONL 저장
            with open(out_path, "w", encoding="utf-8") as f:
                for rec in records:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            print(f"  ✓ 레코드 수: {len(records)}")
            print(f"  ✓ 저장 완료: {out_path}")
            total_records += len(records)
            
        except Exception as e:
            print(f"  [ERROR] 처리 실패: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*50)
    print(f"=== 전체 처리 완료 (총 {total_records}개 레코드) ===")

if __name__ == "__main__":
    main()

