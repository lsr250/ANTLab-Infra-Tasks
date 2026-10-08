#!/usr/bin/env python3
from flask import Flask, jsonify, render_template
from pathlib import Path
import json, glob, statistics

app = Flask(__name__)
DEV = Path(__file__).resolve().parent.parent.parent
RESULTS = DEV / "results"

def load_strategy(strategy):
    rows = []
    for f in sorted(glob.glob(str(RESULTS / strategy / "*.jsonl"))):
        for line in open(f):
            try:
                r = json.loads(line)
                rows.append({
                    "run": Path(f).stem,
                    "task_id": r.get("task_id"),
                    "priority": "高" if r.get("priority") == 0 else "低",
                    "status": r.get("status"),
                    "queue_wait": round(r.get("queue_wait_s", 0), 2),
                    "total_latency": round(r.get("total_latency_s", 0), 2),
                    "e2e": round(r.get("e2e_s", 0), 2),
                    "tokens": r.get("output_tokens", 0),
                    "submit_ts": round(r.get("submit_ts", 0), 3),
                })
            except Exception:
                pass
    return rows

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/results/<strategy>")
def api_results(strategy):
    rows = load_strategy(strategy)
    # 按 run 分组，每组内按 submit_ts 排序，展示实际执行顺序
    runs = {}
    for r in rows:
        runs.setdefault(r["run"], []).append(r)
    for k in runs:
        runs[k].sort(key=lambda x: x["submit_ts"])
    return jsonify(runs)

@app.route("/api/summary")
def api_summary():
    out = {}
    for strategy in ["fifo", "priority"]:
        rows = load_strategy(strategy)
        high = [r for r in rows if r["priority"] == "高"]
        low  = [r for r in rows if r["priority"] == "低"]
        def s(xs):
            if not xs: return {"n": 0, "avg_queue": 0, "avg_total": 0}
            return {
                "n": len(xs),
                "avg_queue": round(statistics.mean([x["queue_wait"] for x in xs]), 2),
                "avg_total": round(statistics.mean([x["total_latency"] for x in xs]), 2),
            }
        out[strategy] = {"high": s(high), "low": s(low)}
    return jsonify(out)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
