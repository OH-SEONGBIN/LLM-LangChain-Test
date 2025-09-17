import os, time, datetime, argparse, pathlib, json, random
import re
import pandas as pd
from dotenv import load_dotenv
from rapidfuzz import fuzz
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from validators.output_checker import (
    load_policies, extract_json_block, check_json_ok, check_citation, check_forbidden
)

load_dotenv()

SYSTEM = SystemMessage(content="""
너는 여행/항공 도우미다. 각 답변에 아래 핵심 포인트를 반드시 포함하라.
- 수하물: "대부분 국제선 위탁 23kg" + "항공사별 상이"
- 환불: "요금제/구매채널/항공사 규정"
- 업그레이드: "유료/마일리지 가능" + "잔여석 여부"
- 기내 반입: "100ml 액체 제한" + "날카로운 물품 금지"
- 여권: "대개 잔여 유효기간 6개월"
불확실하면 단정하지 말고 공식 출처 확인을 권고하라. 답변은 간결하게.
""")

FEWSHOTS = [
    HumanMessage(content="수하물 규정 알려줘"),
    AIMessage(content="대부분 국제선은 위탁 수하물 23kg 기준이며 항공사별로 상이합니다. 초과 시 요금이 부과될 수 있으니 항공사 공지를 확인하세요."),
    HumanMessage(content="여권 만료 기준"),
    AIMessage(content="대부분 국가는 잔여 유효기간 6개월 이상을 요구합니다. 경유국 정책에 따라 예외가 있어 항공사/대사관 공지를 확인하세요."),
]

FEWSHOTS_JSON = [
    HumanMessage(content="수하물 규정 알려줘"),
    AIMessage(content='{"answer":"대부분 국제선은 위탁 23kg 기준이며 항공사별로 상이합니다.","citations":["대한항공 수하물 안내"]}'),

    HumanMessage(content="항공권 환불 규정?"),
    AIMessage(content='{"answer":"환불은 구매 요금제/구매채널/항공사 규정에 따릅니다.","citations":["국적항공사 환불 규정 안내"]}'),

    HumanMessage(content="좌석 업그레이드 가능?"),
    AIMessage(content='{"answer":"유료 업그레이드 또는 마일리지로 가능하며 잔여석 여부에 따라 달라집니다.","citations":["항공사 업그레이드 정책"]}'),

    HumanMessage(content="기내 반입 규정"),
    AIMessage(content='{"answer":"액체는 100ml 이하 용기에 한하며 날카로운 물품은 반입이 금지됩니다.","citations":["국토부/항공사 기내 반입 금지 물품"]}'),

    HumanMessage(content="여권 만료 기준"),
    AIMessage(content='{"answer":"대개 입국 시점 기준으로 여권 잔여 유효기간 6개월 이상을 요구합니다.","citations":["외교부 여권 안내"]}')
]


MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise SystemExit("OPENAI_API_KEY가 없습니다. .env를 설정하세요.")

# baseline: 일반 출력
llm_base = ChatOpenAI(model=MODEL, temperature=0.0, max_tokens=256)

# guardrails: JSON만 출력
llm_json = ChatOpenAI(model=MODEL, temperature=0.0, max_tokens=256).bind(
    response_format={"type": "json_object"}
)

def percentile(arr, p):
    if not arr: return 0.0
    a = sorted(arr)
    i = (len(a)-1)*p
    lo = int(i); hi = min(lo+1, len(a)-1); t = i-lo
    return a[lo]*(1-t) + a[hi]*t

def robust_invoke(llm, messages, tries=3, backoff=1.5):
    for k in range(tries):
        t0 = time.perf_counter()
        try:
            resp = llm.invoke(messages)
            dt  = (time.perf_counter()-t0)*1000.0
            return (getattr(resp, "content", "") or "").strip(), dt, None
        except Exception as e:
            if k == tries-1:
                return "", 0.0, e
            time.sleep(backoff**k)
    return "", 0.0, RuntimeError("unexpected")
def keyword_pass(hint: str, text: str) -> bool:
    """
    힌트에 콤마/슬래시/파이프/점 등으로 핵심 키워드가 나뉘어 있으면
    그중 최소 2개 이상이 답변에 포함되면 통과로 간주한다.
    """
    import re
    keys = [k.strip() for k in re.split(r"[,\|/·+]", hint) if k.strip()]
    if len(keys) >= 2:
        hits = sum(1 for k in keys if k in text)
        return hits >= 2
    return False

def load_tasks(path: str):
    df = pd.read_csv(path)
    rows = []
    for _, r in df.iterrows():
        rows.append({"task_id": int(r["task_id"]), "input": str(r["input"]), "hint": str(r.get("hint",""))})
    return rows

def make_messages(mode: str, question: str):
    if mode == "guardrails":
        sys = SystemMessage(content="""
너는 여행/항공 도우미다.
반드시 JSON 한 줄만 출력한다. 다른 텍스트/설명/코드블록 금지.
형식: {"answer":"...","citations":["...","..."]}

다음 핵심 포인트를 질문에 맞게 포함하라(사실관계를 벗어나지 말 것).
- 수하물: "대부분 국제선 위탁 23kg" + "항공사별 상이"
- 환불: "요금제/구매채널/항공사 규정"
- 업그레이드: "유료/마일리지 가능" + "잔여석 여부"
- 기내 반입: "100ml 액체 제한" + "날카로운 물품 금지"
- 여권: "대개 잔여 유효기간 6개월"
불확실하면 단정하지 말고 공식 출처 확인을 권고하라. 답변은 간결하게.
""")
        return [sys] + FEWSHOTS_JSON + [HumanMessage(content=question)]
    return [SYSTEM] + FEWSHOTS + [HumanMessage(content=question)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=str, default="data/tasks.csv")
    ap.add_argument("--mode", type=str, default="baseline", choices=["baseline","guardrails"])
    ap.add_argument("--policies", type=str, default="guardrails/policies.yaml")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--outdir", type=str, default="results")
    args = ap.parse_args()

    random.seed(args.seed)
    tasks = load_tasks(args.tasks)
    policies = load_policies(args.policies)

    rows, lats = [], []
    for case in tasks:
        q, hint = case["input"], case.get("hint","")
        msgs = make_messages(args.mode, q)

        llm_to_use = llm_json if args.mode == "guardrails" else llm_base
        ans, ms, err = robust_invoke(llm_to_use, msgs)
        if err:
            rows.append({
                "task_id": case["task_id"], "q": q, "mode": args.mode,
                "latency_ms": 0.0, "pass": 0, "json_ok": False,
                "violated_forbidden": False, "citations_ok": False,
                "answer": f"ERROR: {err}", "raw": ""
            })
            continue

        payload = extract_json_block(ans) if args.mode == "guardrails" else None

        # ✅ 필수 키를 동적으로 계산
        required_keys = ["answer"] + (["citations"] if policies["require_citation"] else [])

        json_ok = check_json_ok(payload, required_keys) if args.mode == "guardrails" else True

        # 출처는 require_citation 이 true 일 때만 검사
        citations_ok = check_citation(payload if payload else ans) if (args.mode == "guardrails" and policies["require_citation"]) else True

        violated = check_forbidden(ans, policies["forbidden"])

        ans_text = payload["answer"] if (payload and "answer" in payload) else ans
        s1 = fuzz.token_set_ratio(hint, ans_text)   # 단어 순서 무시, 집합 기반
        s2 = fuzz.partial_ratio(hint, ans_text)     # 부분 일치
        sim_ok = max(s1, s2) >= 55                  
        kw_ok = keyword_pass(hint, ans_text)
        base_ok = sim_ok or kw_ok
        ok = int(base_ok and json_ok and (not violated) and citations_ok) if args.mode == "guardrails" else int(base_ok)

        rows.append({
            "task_id": case["task_id"], "q": q, "mode": args.mode,
            "latency_ms": round(ms,2), "pass": ok,
            "json_ok": bool(json_ok), "violated_forbidden": bool(violated),
            "citations_ok": bool(citations_ok), "answer": ans_text[:600],
            "raw": ans[:1200]
        })
        lats.append(ms)

    pass_ratio = round(sum(r["pass"] for r in rows) / max(len(rows),1), 3)
    p50 = round(percentile(lats, 0.50), 2) if lats else 0.0
    p95 = round(percentile(lats, 0.95), 2) if lats else 0.0

    out_dir = pathlib.Path(args.outdir); out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    csv_path = out_dir / f"agent_eval_{args.mode}_{ts}.csv"
    jsonl_path = out_dir / f"agent_eval_{args.mode}_{ts}.jsonl"

    pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"saved: {csv_path} / {jsonl_path}")
    print(f"mode={args.mode} pass={pass_ratio:.3f} p50={p50:.2f}ms p95={p95:.2f}ms n={len(rows)}")

if __name__ == "__main__":
    main()