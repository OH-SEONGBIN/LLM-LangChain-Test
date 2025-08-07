# ✈️ LangChain 기반 여행 고객센터 AI 에이전트

LangChain과 GPT-3.5를 활용한 간단한 여행 고객센터 자동화 프로젝트입니다.

## 📌 주요 기능

- 사용자의 질문을 받아 GPT가 응답
- LangChain `ConversationChain` + `BufferMemory` 기반 대화 유지
- Streamlit 웹 UI 제공
- 대화 기록 자동 CSV 저장

## 🚀 실행 방법

1. `.env` 파일 생성 후 OpenAI API 키 입력

```
OPENAI_API_KEY=sk-xxxxxx...
```

2. 필요한 라이브러리 설치

```
pip install -r requirements.txt
```

3. Streamlit 앱 실행

```
streamlit run travel_assistant_app.py
```

## 📁 파일 구조

```
.
├── travel_assistant_app.py
├── .env.example
├── .gitignore
├── README.md
└── log_langchain.csv (자동 생성)
```

## 📦 설치 라이브러리

- streamlit
- langchain
- openai
- pandas
