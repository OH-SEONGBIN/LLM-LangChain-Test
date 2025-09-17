# ✈️ LangChain 기반 여행 고객센터 AI 에이전트

LangChain과 GPT-4o mini를 활용한 간단한 여행 고객센터 자동화 프로젝트입니다.

## 📌 주요 기능

사용자의 질문을 받아 GPT가 응답

- LangChain ConversationChain + BufferMemory 기반 대화 유지

- Streamlit 웹 UI 제공

- 대화 기록 자동 CSV 저장

- 평가 파이프라인 내장: Baseline ↔ Guardrails(JSON 강제/금칙 검사) A/B, pass / json_ok / p50 / p95 자동 집계 및 리포트

## 🚀 실행 방법

1) .env 파일 생성 후 OpenAI API 키 입력
```ini
OPENAI_API_KEY=sk-xxxxxx...
OPENAI_MODEL=gpt-4o-mini
```

2) 필요한 라이브러리 설치
```nginx
pip install -r requirements.txt
```

3) Streamlit 앱 실행
```arduino
streamlit run travel_assistant_app.py
```

## 📁 파일 구조
```
.
├── travel_assistant_app.py
├── data/
│   └── tasks.csv                  # 평가용 질문/힌트
├── guardrails/
│   └── policies.yaml              # 금칙/출처/스키마 정책
├── tools/
│   ├── __init__.py
│   └── agent_eval.py              # Baseline/Guardrails 실행 스크립트
├── validators/
│   ├── __init__.py
│   └── output_checker.py          # JSON/출처/금칙 검증
├── scripts/
│   └── score_agent.py             # A/B 리포트 생성
├── results/                       # 실행 결과 CSV/JSONL (재현 로그)
├── reports/
│   └── summary.md                 # A/B 비교 표
├── .env.example
├── .gitignore
└── README.md
```

## 📦 설치 라이브러리

- streamlit, langchain, langchain-openai, openai

- pandas, rapidfuzz, pyyaml

- (선택/RAG 확장 시) chromadb, langchain-community, langchain-text-splitters

## 📊 재현 / 개선 요약

- Baseline

  - Pass 0.80 (n=5)

  - 지연 p50 1.60s / p95 2.19s

- Guardrails(JSON + 가드레일 + 채점 보강)

  - Pass 1.00 (+20pp)

  - 지연 p50 1.39s / p95 1.53s (p95 –30%)

>핵심 보완: 출력 형식 JSON 고정(모델 JSON 응답 모드) + 도메인 핵심 포인트(23kg/100ml/6개월 등) 시스템에 명시 + few-shot을 JSON 예시로 통일 + 채점(token_set_ratio + 키워드 규칙) 보강.
>실패 케이스는 results/*.jsonl에 저장되어 동일 조건 재현 가능.

|  metric | baseline | guardrails |
| ------: | -------: | ---------: |
|    pass |     0.80 |   **1.00** |
| p50(ms) |     1604 |   **1394** |
| p95(ms) |     2192 |   **1527** |

## 🔁 재현 방법
1) 환경 준비
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -r requirements.txt
```

2) Baseline / Guardrails 실행
```bash
# Baseline
python -m tools.agent_eval --tasks data/tasks.csv --mode baseline --outdir results

# Guardrails(JSON 강제/금칙 검사)
python -m tools.agent_eval --tasks data/tasks.csv --mode guardrails --outdir results
```

3) 리포트 생성

Git Bash
```bash
base=$(ls -t results/agent_eval_baseline_*.csv   | head -n 1)
guard=$(ls -t results/agent_eval_guardrails_*.csv | head -n 1)
python scripts/score_agent.py "$base" "$guard" reports/summary.md
```

PowerShell
```powershell
$base  = Get-ChildItem results\agent_eval_baseline_*.csv   | Sort-Object LastWriteTime | Select-Object -Last 1
$guard = Get-ChildItem results\agent_eval_guardrails_*.csv | Sort-Object LastWriteTime | Select-Object -Last 1
python scripts/score_agent.py "$($base.FullName)" "$($guard.FullName)" reports/summary.md
```

## ❗️주의 / 트러블슈팅

- 비밀키 커밋 방지: .gitignore에 .env 포함. 이미 추적 중이면 git rm --cached .env 후 커밋(키 재발급 권장).

- ModuleNotFoundError: validators: 루트에서 모듈 실행(python -m tools.agent_eval) + tools/, validators/에 __init__.py 확인.

- CSV 파싱 오류: tasks.csv의 콤마 포함 문구는 "로 감싸기(예: "100ml 액체 제한, 날카로운 물품 금지").

- PowerShell/Bash 혼용 주의: PowerShell 전용 명령(Get-ChildItem)은 Bash에서 동작하지 않음. 본문에서 내 셸에 맞는 블록만 사용.
