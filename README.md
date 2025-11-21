# Well Dying Legacy Data Preprocessing & RAG System

Well Dying 시스템의 유산상속 관련 데이터 전처리 및 RAG(Retrieval-Augmented Generation) 챗봇 시스템입니다.

**✨ LangGraph 기반 워크플로우로 구현되었습니다.**

## 📖 프로젝트 개요

이 프로젝트는 **Well Dying(존엄한 삶의 마무리)** 시스템의 일부로, 고객들이 궁금해할 만한 유산상속 관련 정보를 제공하는 RAG 챗봇을 구축합니다. 법률 문서와 안내 자료를 전처리하여 벡터 데이터베이스에 저장하고, 사용자 질문에 대해 정확하고 차분한 톤으로 답변을 제공합니다.

### 주요 특징

- 📄 **PDF 문서 전처리**: 법률 문서를 RAG에 최적화된 형태로 정제
- 🗄️ **벡터 데이터베이스**: ChromaDB를 활용한 효율적인 문서 검색
- 🤖 **RAG 챗봇**: GPT-4o mini 기반의 컨텍스트 인식 답변 생성
- 💬 **차분한 톤앤매너**: Well Dying 주제에 맞는 안정적이고 담백한 상담 스타일
- 🌐 **웹 인터페이스**: Streamlit 기반의 사용자 친화적 UI

---

## 📋 프로젝트 구조

```
.
├── preprocess_pdfs.py          # PDF 전처리 스크립트
├── index_data.py                # 벡터 DB 인덱싱 스크립트
├── rag_chatbot.py               # RAG 챗봇 (기본 버전)
├── rag_chatbot_langgraph.py    # RAG 챗봇 (LangGraph 버전)
├── app.py                       # Streamlit 웹 인터페이스 (LangGraph 사용)
├── validate_processed_data.py   # 데이터 검증 스크립트
├── test_chatbot.py              # 챗봇 테스트 스크립트
├── requirements.txt             # Python 패키지 의존성
├── RAG_DATA_PREPROCESSING_GUIDE.md  # 전처리 가이드
├── processed/                   # 전처리된 JSONL 파일들
│   ├── 1_minbeob_sangsok_chunks.jsonl
│   ├── 2_segeumsangsik_I_simple.jsonl
│   ├── 3_segeumsangsik_II_simple.jsonl
│   ├── 4_ansimsangsok_web_simple.jsonl
│   ├── 5_jaesanjohoe_rule_chunks.jsonl
│   └── 6_sangsokse_beob_chunks.jsonl
├── chroma_db/                   # 벡터 DB 저장소 (자동 생성)
└── *.pdf                        # 원본 PDF 파일들 (6개)
```

---

## 🔄 전체 워크플로우

```
1. PDF 파일 (원본)
   ↓
2. preprocess_pdfs.py
   - 텍스트 추출
   - 제어 문자 제거
   - 한글 단어 복원
   - 청킹 (법조문/문단 단위)
   ↓
3. processed/*.jsonl (전처리된 데이터)
   ↓
4. index_data.py
   - OpenAI Embedding 생성
   - ChromaDB에 벡터 저장
   ↓
5. chroma_db/ (벡터 데이터베이스)
   ↓
6. rag_chatbot.py / app.py
   - 사용자 질문 → 벡터 검색
   - 관련 문서 검색
   - GPT-4o mini로 답변 생성
   ↓
7. 사용자에게 답변 제공
```

---

## 🛠️ 기술 스택

### 데이터 처리
- **PyMuPDF (fitz)**: PDF 텍스트 추출
- **Python 3.10+**: 주요 프로그래밍 언어

### 벡터 데이터베이스
- **ChromaDB**: 로컬 벡터 DB 저장 및 검색
- **OpenAI Embeddings**: `text-embedding-3-small` 모델 사용

### LLM & 챗봇
- **OpenAI GPT-4o mini**: 답변 생성 (비용 효율적)
- **RAG (Retrieval-Augmented Generation)**: 문서 기반 답변 생성
- **LangGraph**: 워크플로우 관리 및 상태 관리
- **LangChain**: LLM 통합 및 체인 구성

### 웹 인터페이스
- **Streamlit**: 웹 UI 프레임워크

### 환경 관리
- **python-dotenv**: 환경 변수 관리

---

## 🚀 시작하기

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/souluk319/well_dying_legacy_data_preprocessing.git
cd well_dying_legacy_data_preprocessing

# 가상환경 생성 및 활성화 (conda 권장)
conda create -n well_dying python=3.10
conda activate well_dying

# 또는 venv 사용
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 패키지 설치
pip install -r requirements.txt
```

### 2. OpenAI API Key 설정

`.env` 파일을 생성하고 OpenAI API Key를 설정하세요:

```bash
# .env 파일 생성
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

또는 환경 변수로 직접 설정:
```bash
export OPENAI_API_KEY=your_api_key_here
```

### 3. 데이터 전처리 (선택사항)

이미 전처리된 JSONL 파일이 `processed/` 폴더에 있지만, 원본 PDF를 다시 전처리하려면:

```bash
python preprocess_pdfs.py
```

### 4. 벡터 DB 인덱싱

전처리된 JSONL 파일들을 벡터 DB에 인덱싱합니다:

```bash
python index_data.py
```

**소요 시간**: 약 100개 문서당 10초 정도 (OpenAI Embedding API 사용)

**결과**: `chroma_db/` 폴더에 벡터 데이터베이스가 생성됩니다.

### 5. 챗봇 실행

#### 방법 1: 웹 인터페이스 (권장) 🌐

```bash
streamlit run app.py
```

브라우저가 자동으로 열리며 `http://localhost:8501`에서 챗봇을 사용할 수 있습니다.

**다른 PC에서 접속하기:**

같은 네트워크의 다른 PC에서도 접속할 수 있습니다:

1. 서버 PC에서 Streamlit 실행 (자동으로 `0.0.0.0`으로 설정됨)
2. 서버 PC의 IP 주소 확인:
   ```bash
   # macOS/Linux
   ifconfig | grep "inet "
   
   # Windows
   ipconfig
   ```
3. 다른 PC의 브라우저에서 접속:
   ```
   http://[서버IP주소]:8501
   ```
   예: `http://192.168.0.100:8501`

**참고**: `.streamlit/config.toml` 파일에 네트워크 접속 설정이 포함되어 있습니다.

**웹 인터페이스 기능:**
- 💬 실시간 채팅 인터페이스
- 📚 참고 출처 표시 (접기/펼치기)
- 💾 대화 기록 유지
- 🗑️ 대화 기록 초기화 버튼
- ℹ️ 사이드바 안내

#### 방법 2: 터미널 대화형 모드

```bash
python rag_chatbot.py
```

터미널에서 대화형 모드로 실행됩니다. 종료하려면 `quit` 또는 `exit`를 입력하세요.

---

## 📝 데이터 정제 과정

### 1단계: PDF 텍스트 추출

- **도구**: PyMuPDF (fitz)
- **방법**: `page.get_text("text")` 방식으로 순수 텍스트만 추출
- **이유**: 레이아웃 정보는 RAG에 불필요하며, 텍스트 왜곡을 방지

### 2단계: 제어 문자 제거

- 일반 제어 문자 제거 (0x00-0x1F, 0x7F-0x9F)
- Private Use Area 제거 (U+E000~U+F8FF)
- 개행(\n), 탭(\t), 캐리지 리턴(\r)은 유지

### 3단계: 한글 단어 중간 개행 복원

- PDF 추출 시 분리된 한글 단어 복원
- 예: "상속\n\n민법권" → "상속권"

### 4단계: PDF 헤더/푸터 제거

- 문서 본문이 아닌 헤더/푸터 제거
- 검색 시 노이즈 방지

### 5단계: 특수 패턴 정리

- "분의 1" 다음 숫자 분리
- "및" 뒤 공백 추가
- 법률 용어 보호

### 6단계: 청킹 전략

#### Law 모드 (법령 문서)
- 조문 단위로 청킹 ("제000조" 패턴 기준)
- 조문이 500자 초과 시 문단/문장 단위로 분할

#### Simple 모드 (일반 문서)
- 문단 기준 청킹 (\n\n 기준)
- 문단이 500자 초과 시 문장 단위로 분할

### 7단계: 길이 제한

- 모든 청크를 **500자 이하**로 제한
- 너무 짧은 청크(20자 미만)는 제외
- **이유**: 임베딩 모델의 토큰 제한(512 토큰) 고려

### 8단계: 스키마 정리

- null 값 제거
- 선택적 필드는 값이 있을 때만 포함

**상세 가이드**: `RAG_DATA_PREPROCESSING_GUIDE.md` 참고

---

## 🗄️ 벡터 데이터베이스

### 저장 방식

- **벡터 DB**: ChromaDB (로컬 파일 기반)
- **임베딩 모델**: OpenAI `text-embedding-3-small`
- **저장 위치**: `chroma_db/` 폴더

### 메타데이터 구조

각 문서는 다음 메타데이터와 함께 저장됩니다:

```json
{
  "id": "minlaw_0001",
  "title": "상속개시의 원인 제997조",
  "text": "상속은 사망으로 인하여 개시된다...",
  "source": "1. 민법 상속편.pdf",
  "category": "법령_민법_상속",
  "article_id": "제997조",
  "article_title": "상속개시의 원인"
}
```

### 검색 방식

1. 사용자 질문을 임베딩 벡터로 변환
2. ChromaDB에서 유사도가 높은 문서 검색 (기본 5개)
3. 검색된 문서의 텍스트와 메타데이터 반환

---

## 🤖 챗봇 모델 선정

### 선택한 모델

- **임베딩**: `text-embedding-3-small`
  - 이유: 비용 효율적이면서도 충분한 성능 제공
  - 차원: 1536차원

- **생성 모델**: `gpt-4o-mini`
  - 이유: 비용 효율적이면서도 고품질 답변 생성
  - 토큰 제한: 최대 1000 토큰
  - Temperature: 0.7 (균형잡힌 창의성)

### RAG 작동 원리

1. **Retrieval (검색)**: 사용자 질문과 유사한 문서 청크를 벡터 DB에서 검색
2. **Augmentation (증강)**: 검색된 청크를 컨텍스트로 LLM에 제공
3. **Generation (생성)**: 컨텍스트를 바탕으로 정확한 답변 생성

### 하이브리드 답변 방식

- **문서 기반 정보 우선**: 제공된 문서에 관련 정보가 있으면 우선 사용
- **일반 지식 보완**: 문서에 정보가 없거나 부족한 경우, GPT-4o mini의 일반 지식을 활용
- **구분 표시**: 일반 지식 사용 시 "일반적으로", "보통" 등의 표현으로 구분

---

## 💬 톤앤매너 설정

Well Dying 주제에 맞는 **차분하고 안정적인 상담 스타일**을 적용했습니다.

### 핵심 원칙

1. **과도한 감정 표현 금지**: 동정, 위로 표현 사용하지 않음
2. **감정 추측 금지**: 사용자가 말하지 않은 감정이나 상태를 추측하지 않음
3. **담백한 어조**: 따뜻하되 절제되어 있으며, 안정적이고 담백한 말투
4. **선택권 제공**: 해결책을 강요하지 않고, 선택권을 사용자에게 돌려줌
5. **부드러운 안내**: 필요한 만큼만 부드럽게 안내
6. **중립적 정보**: 전문 분야는 단정적 조언 대신 일반적 정보와 안내 중심

### 금지 표현 예시

- ❌ "요즘 많이 힘드셨죠…"
- ❌ "괜찮아요. 다 잘될 거예요."
- ❌ "정말 많이 힘드셨겠네요."
- ❌ "걱정하지 마세요."

### 지향 표현 스타일

- ✅ 고요하고 차분한 말투
- ✅ 존중, 선택권 제공, 과장 없는 친절함
- ✅ "원하시면…", "필요하신 만큼…", "이런 방향으로도 살펴볼 수 있어요"
- ✅ 사용자가 말한 내용 안에서만 공감하거나 정리

### 예시 말투

- "말해줘서 고마워요. 천천히 필요한 부분부터 이야기해도 괜찮아요."
- "이 부분에서 어떤 정보를 알고 싶은지 편한 만큼 알려주세요."
- "원하신다면 ○○와 같은 정보부터 차분히 정리해드릴 수 있어요."
- "부담 없이, 알고 싶은 범위까지만 말씀해주세요."

**톤앤매너 설정 위치**: `rag_chatbot.py` 파일의 `generate_response()` 함수 내부 (99-139번 줄)

---

## 🌐 Streamlit 웹 인터페이스

### 주요 기능

1. **채팅 인터페이스**
   - 실시간 질문/답변
   - 대화 기록 유지
   - 스크롤 가능한 채팅 히스토리

2. **참고 출처 표시**
   - 각 답변에 참고한 문서 출처 표시
   - 접기/펼치기 가능한 아코디언 형태
   - 출처별 상세 정보 (조문 번호, 제목 등)

3. **사이드바**
   - 프로젝트 안내
   - 사용 방법 설명
   - 대화 기록 초기화 버튼

4. **반응형 디자인**
   - 다양한 화면 크기 지원
   - 깔끔하고 직관적인 UI

### 실행 방법

```bash
streamlit run app.py
```

자동으로 브라우저가 열리며 `http://localhost:8501`에서 접속 가능합니다.

---

## 📊 데이터 구조

### 전처리된 JSONL 형식

```json
{
  "id": "minlaw_0001",
  "title": "상속개시의 원인 제997조",
  "text": "상속은 사망으로 인하여 개시된다. <개정 1990. 1. 13.> [제목개정 1990. 1. 13.]",
  "source": "1. 민법 상속편.pdf",
  "category": "법령_민법_상속",
  "article_id": "제997조",
  "article_title": "상속개시의 원인"
}
```

### 필드 설명

- `id`: 고유 식별자
- `title`: 문서 제목
- `text`: 문서 본문 (500자 이하)
- `source`: 원본 PDF 파일명
- `category`: 문서 카테고리
- `article_id`: 법조문 번호 (선택적)
- `article_title`: 조문 제목 (선택적)
- `sub_chunk`: 분할된 청크 번호 (선택적)

---

## 📚 포함된 문서

1. **민법 상속편.pdf** - 민법 상속 관련 조문
2. **국세청-상속·증여 세금상식1.pdf** - 상속세 기본 안내
3. **국세청-상속·증여 세금상식Ⅱ.pdf** - 상속세 상세 안내
4. **사망자 및 피후견인 등 재산조회 통합처리 신청(안심상속)웹스크래핑.pdf** - 안심상속 서비스 안내
5. **사망자 및 피후견인 등 재산조회 통합처리에 관한 기준(행정안전).pdf** - 재산조회 기준
6. **상속세 및 증여세법.pdf** - 상속세법 조문

**총 인덱싱된 문서 수**: 약 450개 청크

---

## 🔍 검색 파라미터

`rag_chatbot.py`의 `chat()` 함수에서 검색 결과 개수를 조정할 수 있습니다:

```python
from rag_chatbot import chat

# 기본값: 5개 문서 검색
result = chat("상속세 신고 기한은 언제인가요?")

# 검색 결과 개수 조정
result = chat("상속세 신고 기한은 언제인가요?", n_results=10)
```

---

## 📝 사용 예시

### 웹 인터페이스

1. `streamlit run app.py` 실행
2. 브라우저에서 질문 입력
3. 답변 확인 및 참고 출처 확인

### Python 코드에서 사용

```python
from rag_chatbot import chat

# 질문하기
result = chat("상속세 신고 기한은 언제인가요?")

print("답변:", result['answer'])
print("참고 출처:", result['sources'])
print("출처 개수:", result['num_sources'])
```

### 터미널 대화형 모드

```bash
$ python rag_chatbot.py

============================================================
Well Dying 유산상속 상담 챗봇
============================================================
질문을 입력하세요. 종료하려면 'quit' 또는 'exit'를 입력하세요.

질문: 상속세는 어떻게 계산하나요?

검색 중...

------------------------------------------------------------
답변:
상속세는 피상속인의 재산에서 채무와 상속공제를 제외한 금액을 기준으로 계산됩니다...
[답변 내용]

참고 출처:
  1. 2. 국세청-상속·증여 세금상식1.pdf
  2. 6. 상속세 및 증여세법.pdf
------------------------------------------------------------
```

---

## ⚠️ 주의사항

### API 비용

- **Embedding**: `text-embedding-3-small` 모델 사용 (비용 효율적)
- **Chat**: GPT-4o mini 사용 (비용 효율적)
- 인덱싱 시 약 450개 문서 처리로 일정 비용 발생
- 챗봇 사용 시 질문당 비용 발생

### 인덱싱 시간

- 문서 수에 따라 인덱싱에 시간이 걸릴 수 있습니다
- Rate limit 방지를 위해 배치 처리 시 딜레이(0.1초) 포함
- 약 100개 문서당 10초 정도 소요

### 벡터 DB 관리

- `chroma_db/` 폴더는 Git에 포함하지 않음 (`.gitignore`에 추가됨)
- 다른 PC에서 사용하려면 `index_data.py`를 다시 실행해야 함
- 벡터 DB는 로컬 파일로 저장되므로 백업 필요 시 폴더 전체 복사

### 환경 변수

- `.env` 파일은 Git에 포함하지 않음 (`.gitignore`에 추가됨)
- API 키는 반드시 환경 변수로 관리

---

## 🧪 테스트

챗봇 테스트 스크립트를 실행할 수 있습니다:

```bash
python test_chatbot.py
```

여러 질문에 대한 답변을 자동으로 테스트합니다.

---

## 📖 상세 가이드

전처리 과정에 대한 상세한 설명과 각 단계의 이유는 `RAG_DATA_PREPROCESSING_GUIDE.md`를 참고하세요.

---

## 🔧 주요 스크립트 설명

### `preprocess_pdfs.py`
- PDF 파일을 읽어서 전처리
- Law 모드와 Simple 모드 지원
- JSONL 파일로 출력

### `index_data.py`
- 전처리된 JSONL 파일을 읽어서 벡터 DB에 인덱싱
- OpenAI Embedding API 사용
- ChromaDB에 저장

### `rag_chatbot.py`
- RAG 챗봇 핵심 로직 (기본 버전)
- 벡터 검색 및 답변 생성
- 톤앤매너 설정 포함

### `rag_chatbot_langgraph.py`
- RAG 챗봇 (LangGraph 버전)
- 그래프 기반 워크플로우 관리
- 상태 관리 및 노드 기반 처리
- 확장 가능한 구조 (품질 검증, 재검색 등 추가 용이)

### `app.py`
- Streamlit 웹 인터페이스
- `rag_chatbot.py`의 `chat()` 함수 사용

### `validate_processed_data.py`
- 전처리된 데이터 검증
- 제어 문자, 길이, 스키마 체크

---

## 🤝 기여

이슈나 개선 사항이 있으면 GitHub Issues에 등록해주세요.

---

## 📄 라이선스

이 프로젝트는 Well Dying 시스템의 일부입니다.

---

## 📞 문의

프로젝트 관련 문의사항은 GitHub Issues를 통해 남겨주세요.
