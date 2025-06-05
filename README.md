# GPTutor (AI 기반 교육 지원 시스템)

## 프로젝트 소개

GPTutor는 AI를 활용한 교육 지원 시스템으로, 학습자들에게 개인화된 학습 경험을 제공합니다.

## 주요 기능

1. **AI 기반 QnA 시스템**

   - GPT를 활용한 질문-답변 시스템
   - RAG(Retrieval-Augmented Generation) 기반 정확한 답변 제공

2. **개인화된 학습 관리**

   - 개인별 학습 내용 저장 및 관리
   - 학습 진도 추적
   - 맞춤형 복습 문제 생성

3. **공동 학습 기능**
   - 최근 질문 공유
   - 학습 내용 공유 및 협업

## ⚙️ 기술 스택

- Python
- Azure Custom Vision
- Azure Blob Storage
- Flask

## 🚫 주의사항

현재는 Azure 리소스 연결이 끊겨 있어, 일부 기능은 실행되지 않을 수 있습니다.

## ✅ 당시 구현 내용

1. **Azure Custom Vision 연동**

   - 이미지 기반 학습 자료 분석
   - 시각적 콘텐츠 인식 및 처리

2. **Azure Blob Storage 활용**

   - 학습 자료 저장 및 관리
   - 대용량 데이터 처리 지원

3. **Flask 웹 서버**
   - RESTful API 구현
   - 웹 인터페이스 제공

## 설치 방법

1. 저장소 클론

```bash
git clone [repository-url]
```

2. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

3. 환경 변수 설정
   프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 다음 환경 변수들을 설정합니다:

```env
# Azure OpenAI
AZURE_OAI_ENDPOINT=your_openai_endpoint
AZURE_OAI_KEY=your_openai_key
AZURE_OAI_DEPLOYMENT=your_deployment_name

# Azure Search
AZURE_SEARCH_ENDPOINT=your_search_endpoint
AZURE_SEARCH_KEY=your_search_key

# Azure Text Analytics
AZURE_SERVICES_ENDPOINT=your_services_endpoint
AZURE_SERVICES_KEY=your_services_key

# Azure Text Embedding
AZURE_TEXTEMBEDDING_ENDPOINT=your_textembedding_endpoint
AZURE_TEXTEMBEDDING_KEY=your_textembedding_key

# Cosmos DB
COSMOSDB_NOSQL_ENDPOINT=your_cosmos_endpoint
COSMOSDB_NOSQL_KEY=your_cosmos_key

# MongoDB
MONGODB_URI=your_mongodb_uri
```

각 환경 변수에 대한 값은 Azure Portal에서 확인할 수 있습니다.

## 실행 방법

```bash
python main.py
```

## 라이선스

MIT License
