#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전처리된 JSONL 파일들을 읽어서 벡터 DB에 인덱싱하는 스크립트
"""

import os
import json
from pathlib import Path
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv
import time

# 환경 변수 로드
load_dotenv()

# === 설정 ===
BASE_DIR = Path(__file__).parent
PROCESSED_DIR = BASE_DIR / "processed"
DB_DIR = BASE_DIR / "chroma_db"

# OpenAI 클라이언트 초기화
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ChromaDB 클라이언트 초기화
chroma_client = chromadb.PersistentClient(
    path=str(DB_DIR),
    settings=Settings(anonymized_telemetry=False)
)

# 컬렉션 생성 또는 가져오기
collection_name = "well_dying_legacy_data"
try:
    collection = chroma_client.get_collection(name=collection_name)
    print(f"기존 컬렉션 '{collection_name}' 사용")
except:
    collection = chroma_client.create_collection(
        name=collection_name,
        metadata={"description": "Well Dying 유산상속 관련 데이터"}
    )
    print(f"새 컬렉션 '{collection_name}' 생성")

def get_embedding(text: str, model: str = "text-embedding-3-small") -> list:
    """텍스트를 임베딩 벡터로 변환"""
    try:
        response = openai_client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"임베딩 생성 오류: {e}")
        raise

def index_jsonl_file(jsonl_path: Path):
    """JSONL 파일을 읽어서 벡터 DB에 인덱싱"""
    print(f"\n처리 중: {jsonl_path.name}")
    
    documents = []
    metadatas = []
    ids = []
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            data = json.loads(line)
            
            # 텍스트와 메타데이터 추출
            text = data.get('text', '')
            if not text or len(text.strip()) < 20:
                continue
            
            # ID와 메타데이터 준비
            doc_id = data.get('id', '')
            metadata = {
                'title': data.get('title', ''),
                'source': data.get('source', ''),
                'category': data.get('category', ''),
            }
            
            # 선택적 필드 추가
            if 'article_id' in data:
                metadata['article_id'] = data['article_id']
            if 'article_title' in data:
                metadata['article_title'] = data['article_title']
            if 'sub_chunk' in data:
                metadata['sub_chunk'] = str(data['sub_chunk'])
            
            documents.append(text)
            metadatas.append(metadata)
            ids.append(doc_id)
    
    if not documents:
        print(f"  경고: {jsonl_path.name}에 유효한 문서가 없습니다.")
        return
    
    print(f"  {len(documents)}개 문서 발견")
    
    # 배치로 임베딩 생성 및 추가
    batch_size = 100
    total_batches = (len(documents) + batch_size - 1) // batch_size
    
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        batch_metadatas = metadatas[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        print(f"  배치 {batch_num}/{total_batches} 처리 중... ({len(batch_docs)}개 문서)")
        
        # 임베딩 생성
        embeddings = []
        for doc in batch_docs:
            embedding = get_embedding(doc)
            embeddings.append(embedding)
            time.sleep(0.1)  # API rate limit 방지
        
        # ChromaDB에 추가
        collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_docs,
            metadatas=batch_metadatas
        )
        
        print(f"  배치 {batch_num} 완료")
    
    print(f"  ✓ {jsonl_path.name} 인덱싱 완료")

def main():
    """모든 JSONL 파일을 인덱싱"""
    print("=" * 60)
    print("Well Dying Legacy Data 인덱싱 시작")
    print("=" * 60)
    
    # DB 디렉토리 생성
    DB_DIR.mkdir(exist_ok=True)
    
    # 처리된 JSONL 파일 찾기
    jsonl_files = sorted(PROCESSED_DIR.glob("*.jsonl"))
    
    if not jsonl_files:
        print(f"경고: {PROCESSED_DIR}에 JSONL 파일이 없습니다.")
        return
    
    print(f"\n총 {len(jsonl_files)}개 파일 발견")
    
    # 각 파일 인덱싱
    for jsonl_file in jsonl_files:
        try:
            index_jsonl_file(jsonl_file)
        except Exception as e:
            print(f"오류: {jsonl_file.name} 처리 중 오류 발생: {e}")
            continue
    
    # 최종 통계
    count = collection.count()
    print("\n" + "=" * 60)
    print(f"인덱싱 완료! 총 {count}개 문서가 벡터 DB에 저장되었습니다.")
    print("=" * 60)

if __name__ == "__main__":
    main()

