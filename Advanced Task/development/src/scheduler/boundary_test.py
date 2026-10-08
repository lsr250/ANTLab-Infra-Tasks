#!/usr/bin/env python3
"""边界测试：请求执行中杀掉 llama-server，观察调度器处理"""
import sys, time, json, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from benchmark_base import parse_tasks, one_request

OUT = HERE.parent.parent / "results" / "boundary"
OUT.mkdir(parents=True, exist_ok=True)

SERVER_CMD = [
    "/home/lenovo/llama.cpp/build/bin/llama-server",
    "-m", "/home/lenovo/models/qwen2.5-3b-instruct-q4_k_m.gguf",
    "-ngl", "99", "-c", "65536", "-np", "4",
    "-ctk", "q8_0", "-ctv", "q8_0",
    "--host", "0.0.0.0", "--port", "8080",
]

def log(msg):
    line = f"{datetime.now().isoformat()} {msg}"
    print(line)
    with open(OUT / "boundary.log", "a") as f:
        f.write(line + "\n")

def run_task(item, submit_ts):
    r = one_request(item["task"], 256)
    r["submit_ts"] = submit_ts
    r["total_latency_s"] = time.time() - submit_ts
    return r

def main():
    tasks = parse_tasks()[:6]
    scenario = [{"task": t, "arrival": 0.0} for t in tasks]

    log("=== 边界测试开始 ===")
    log("场景：6 个请求顺序提交，执行到第 3 个时杀掉 llama-server")

    results = []
    with ThreadPoolExecutor(max_workers=1) as pool:
        futures = []
        for idx, item in enumerate(scenario):
            submit_ts = time.time()
            f = pool.submit(run_task, item, submit_ts)
            futures.append((f, item, submit_ts, idx))
            if idx == 2:
                time.sleep(3)
                log("故意杀掉 llama-server")
                subprocess.run(["pkill", "-f", "llama-server"], check=False)
                time.sleep(2)
                log("重新启动 llama-server")
                subprocess.Popen(SERVER_CMD,
                                 stdout=open("/tmp/boundary-restart.log", "w"),
                                 stderr=subprocess.STDOUT)
                time.sleep(15)

        for f, item, submit_ts, idx in futures:
            r = f.result()
            r["task_id"] = item["task"]["id"]
            r["order"] = idx
            results.append(r)
            status = r.get("status", "unknown")
            log(f"  任务 {r['task_id']} 状态={status} 总延迟={r['total_latency_s']:.2f}s")

    with open(OUT / "boundary_results.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    ok = sum(1 for r in results if r.get("status") == "success")
    failed = sum(1 for r in results if r.get("status") == "error")
    log(f"=== 边界测试结束：成功 {ok}/{len(results)}，失败 {failed} ===")

if __name__ == "__main__":
    main()
