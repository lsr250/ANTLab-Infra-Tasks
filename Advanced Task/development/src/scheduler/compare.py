#!/usr/bin/env python3
"""方向二：FIFO vs Priority 调度对比（含真实排队延迟）"""
import sys, time, json, statistics
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from benchmark_base import parse_tasks, one_request

MAX_CONCURRENT = 1
HIGH_DELAY = 0.5
MAX_TOKENS = 512

def priority(task):
    return 0 if task["id"].startswith("P") else 1

def task_wrapper(item, max_tokens, submit_ts):
    start_worker = time.time()
    r = one_request(item["task"], max_tokens)
    completion = time.time()
    r["priority"] = priority(item["task"])
    r["submit_ts"] = submit_ts
    r["queue_wait_s"] = start_worker - submit_ts
    r["total_latency_s"] = completion - submit_ts
    return r

def _run(ordered):
    start = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
        futures = []
        for item in ordered:
            wait = item["arrival"] - (time.time() - start)
            if wait > 0:
                time.sleep(wait)
            submit_ts = time.time()
            f = pool.submit(task_wrapper, item, MAX_TOKENS, submit_ts)
            futures.append(f)
        for f in futures:
            results.append(f.result())
    return results

def run_fifo(scenario):
    ordered = sorted(scenario, key=lambda x: (x["arrival"], x["task"]["id"]))
    return _run(ordered)

def run_priority(scenario):
    ordered = sorted(scenario, key=lambda x: (priority(x["task"]), x["arrival"]))
    return _run(ordered)

def summarize(results):
    def stats(reqs):
        if not reqs:
            return {"n": 0, "avg_queue": 0, "max_queue": 0,
                    "avg_total": 0, "max_total": 0, "avg_e2e": 0}
        q = [r["queue_wait_s"] for r in reqs]
        t = [r["total_latency_s"] for r in reqs]
        e = [r["e2e_s"] for r in reqs if r.get("e2e_s")]
        return {
            "n": len(reqs),
            "avg_queue": statistics.mean(q),
            "max_queue": max(q),
            "avg_total": statistics.mean(t),
            "max_total": max(t),
            "avg_e2e": statistics.mean(e) if e else 0,
        }
    return {
        "high": stats([r for r in results if r["priority"] == 0]),
        "low":  stats([r for r in results if r["priority"] == 1]),
    }

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--output-dir", default="results")
    args = ap.parse_args()

    tasks = parse_tasks()
    low = [t for t in tasks if priority(t) == 1] * 2
    high = [t for t in tasks if priority(t) == 0] * 2
    scenario = []
    for t in low:
        scenario.append({"task": t, "arrival": 0.0})
    for t in high:
        scenario.append({"task": t, "arrival": HIGH_DELAY})

    print(f"场景: {len(low)} 低优先级(t=0) + {len(high)} 高优先级(t={HIGH_DELAY}s)")
    print(f"并发: {MAX_CONCURRENT}  |  tokens: {MAX_TOKENS}\n")

    out_root = Path(args.output_dir)

    for strategy in ["fifo", "priority"]:
        print(f"=== {strategy} ===")
        for run in range(args.repeat):
            run_id = f"run_{run+1:02d}"
            print(f"  {run_id}...", end=" ", flush=True)
            results = run_fifo(scenario) if strategy == "fifo" else run_priority(scenario)
            s = summarize(results)
            out_dir = out_root / strategy
            out_dir.mkdir(parents=True, exist_ok=True)
            with open(out_dir / f"{run_id}.jsonl", "w") as f:
                for r in results:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"高: 排队{ s['high']['avg_queue']:.2f}s 总{ s['high']['avg_total']:.2f}s | "
                  f"低: 排队{ s['low']['avg_queue']:.2f}s 总{ s['low']['avg_total']:.2f}s")

if __name__ == "__main__":
    main()
