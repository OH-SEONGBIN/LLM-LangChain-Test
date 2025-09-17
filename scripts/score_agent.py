import sys, pandas as pd, numpy as np, pathlib

def describe(path):
    df = pd.read_csv(path)
    p = {
        "n": len(df),
        "pass": float(df["pass"].mean()),
        "json_ok": float(df["json_ok"].mean()) if "json_ok" in df.columns else None,
        "p50": float(np.percentile(df["latency_ms"], 50)),
        "p95": float(np.percentile(df["latency_ms"], 95)),
    }
    return df, p

if __name__ == "__main__":
    baseline_csv = sys.argv[1]
    guard_csv    = sys.argv[2]
    out_md       = sys.argv[3]

    _, b = describe(baseline_csv)
    _, g = describe(guard_csv)

    md = []
    md.append("| metric | baseline | guardrails |")
    md.append("|--|--:|--:|")
    md.append(f"| pass | {b['pass']:.3f} | {g['pass']:.3f} |")
    if b["json_ok"] is not None and g["json_ok"] is not None:
        md.append(f"| json_ok | {b['json_ok']:.3f} | {g['json_ok']:.3f} |")
    md.append(f"| p50(ms) | {b['p50']:.2f} | {g['p50']:.2f} |")
    md.append(f"| p95(ms) | {b['p95']:.2f} | {g['p95']:.2f} |")

    pathlib.Path(out_md).write_text("\n".join(md), encoding="utf-8")
    print("written:", out_md)