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


---

## 📊 재현 / 개선 요약

- **Baseline** (few-shot 전):
  - Pass **60%** (n=5)
  - 지연 **p50 2.27s / p95 3.10s**
  - 결과 파일: `metrics/agent_eval_2025-09-02_195006.csv`

- **After** (System + Few-shot 보강 후):
  - Pass **100%** (**+40pp**)
  - 지연 **p50 2.12s (-6.6%) / p95 2.50s (-19.5%)**
  - 결과 파일: `metrics/agent_eval_2025-09-02_200913.csv`

> 보강 내용: System 프롬프트에 핵심 포인트(23kg/100ml/6개월 등) 강제 + 2-shot 예시 추가  
> 동일 조건 재측정: `gpt-3.5-turbo`, `temperature=0.0`, QA 5건

---

## 🔁 재현 방법

### 1) 환경 준비
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -r requirements.txt