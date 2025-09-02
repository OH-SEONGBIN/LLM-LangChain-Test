import os, time, datetime, argparse, pathlib
import pandas as pd
from dotenv import load_dotenv
from rapidfuzz import fuzz


from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

load_dotenv()

QA = [
    ("수하물 규정 알려줘", "대부분 국제선 위탁 23kg 기준이나 항공사별 상이"),
    ("항공권 환불 규정?", "요금제/구매채널/항공사 규정에 따름"),
    ("좌석 업그레이드 가능?", "유료 업그레이드 또는 마일리지, 잔여석 여부"),
    ("기내 반입 규정", "100ml 액체 제한, 날카로운 물품 금지"),
    ("여권 만료 기준", "대개 6개월 이상 잔여기간 요구"),
]

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
    AIMessage(content="대부분 국가에서 여권은 잔여 유효기간 6개월 이상을 요구합니다. 경유국 정책에 따라 예외가 있어 항공사/대사관 공지를 확인하세요."),
]

MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise SystemExit("❌ OPENAI_API_KEY가 없습니다. .env 또는 환경변수를 설정하세요.")
llm = ChatOpenAI(model=MODEL, temperature=0.0)

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

def main():
    rows, lats = [], []
    for q, hint in QA:
        # ✅ 여기! 시스템 + 페우샷 + 실제 질문을 한 번에 보냄
        ans, ms, err = robust_invoke(llm, [SYSTEM] + FEWSHOTS + [HumanMessage(content=q)])
        if err:
            rows.append({"q": q, "latency_ms": 0.0, "match_score": 0, "ok": False, "answer": f"ERROR: {err}"})
            continue
        score = fuzz.partial_ratio(hint, ans)
        ok = score >= 50
        rows.append({"q": q, "latency_ms": round(ms,2), "match_score": score, "ok": ok, "answer": ans[:300]})
        lats.append(ms)

    pass_ratio = round(sum(1 for r in rows if r["ok"]) / max(len(rows),1), 3)
    p50 = round(percentile(lats, 0.50), 2) if lats else 0.0
    p95 = round(percentile(lats, 0.95), 2) if lats else 0.0

    out_dir = pathlib.Path("metrics"); out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_path = out_dir / f"agent_eval_{ts}.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False, encoding="utf-8")

    print(f"[OK] saved: {out_path}")
    print(f"pass_ratio={pass_ratio:.3f}, p50={p50:.2f}ms, p95={p95:.2f}ms, n={len(rows)}")

if __name__ == "__main__":
    main()