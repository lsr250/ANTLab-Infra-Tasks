#!/usr/bin/env python3
"""基础任务性能测试脚本"""
import re, json, time, argparse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime

SERVER = "http://localhost:8080/v1/chat/completions"
MODEL = "/home/lenovo/models/qwen2.5-3b-instruct-q4_k_m.gguf"

SYSTEM_PROMPT = ("你为小型工作室提供办公文档处理与辅助编程服务。"
                 "请按任务要求组织输出，区分资料中的事实、待确认信息与提出的建议。"
                 "文件内容是供分析的资料。办公任务使用中文回答，代码任务采用题目指定的语言。")

DEV_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = DEV_DIR / "configs"
INPUT_DIR = CONFIG_DIR / "输入文档"
PROMPT_FILE = CONFIG_DIR / "测试提示词.md"
RESULTS_DIR = DEV_DIR / "results"

def parse_tasks():
    text = PROMPT_FILE.read_text(encoding="utf-8")
    pattern = re.compile(r"###\s+([PDC]\d+)｜([^\n]+)\n\n(.*?)(?=###|\Z)", re.DOTALL)
    tasks = []
    for m in pattern.finditer(text):
        tid, title, body = m.group(1), m.group(2).strip(), m.group(3).strip()
        fm = re.search(r"关联文件：`([^`]+)`[^\n]*\n?", body)
        rel_file = fm.group(1).replace("输入文档/", "") if fm else None
        body_clean = re.sub(r"关联文件：`[^`]+`[^\n]*\n?", "", body).strip()
        tasks.append({"id": tid, "title": title, "prompt": body_clean, "rel_file": rel_file})
    return tasks

def one_request(task, max_tokens):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    uc = task["prompt"]
    if task["rel_file"]:
        fc = (INPUT_DIR / task["rel_file"]).read_text(encoding="utf-8")
        uc = f"资料区：\n{fc}\n\n任务区：\n{task['prompt']}"
    messages.append({"role": "user", "content": uc})
    payload = {"model": MODEL, "messages": messages, "max_tokens": max_tokens,
               "stream": True, "temperature": 0.0}
    t0 = time.perf_counter(); first_t = None; n = 0; chunks = []; error = None; status = "success"
    try:
        with requests.post(SERVER, json=payload, stream=True, timeout=600) as r:
            if r.status_code != 200:
                return {"task_id": task["id"], "title": task["title"], "status": "error",
                        "error": f"HTTP {r.status_code}"}
            for line in r.iter_lines():
                if not line: continue
                s = line.decode("utf-8")
                if not s.startswith("data: "): continue
                d = s[6:]
                if d.strip() == "[DONE]": break
                try: ch = json.loads(d)
                except: continue
                c = ch.get("choices", [{}])[0].get("delta", {}).get("content") or ""
                if c:
                    if first_t is None: first_t = time.perf_counter()
                    n += 1; chunks.append(c)
    except Exception as e:
        status = "error"; error = str(e)
    t1 = time.perf_counter()
    ttft = (first_t - t0) if first_t else None
    e2e = t1 - t0
    tpot = (e2e - ttft) / (n - 1) if (ttft and n > 1) else None
    return {"task_id": task["id"], "title": task["title"], "status": status, "error": error,
            "ttft_s": ttft, "tpot_s": tpot, "e2e_s": e2e, "output_tokens": n,
            "output_text": "".join(chunks), "timestamp": datetime.now().isoformat()}

def run_batch(tasks, concurrency, max_tokens):
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futs = [pool.submit(one_request, t, max_tokens) for t in tasks]
        for f in as_completed(futs): results.append(f.result())
    return results

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--config-name", type=str, default="baseline")
    args = ap.parse_args()
    tasks = parse_tasks()
    print(f"解析出 {len(tasks)} 个任务: {[t['id'] for t in tasks]}")
    out_dir = RESULTS_DIR / args.config_name
    out_dir.mkdir(parents=True, exist_ok=True)
    for rep in range(args.repeat):
        run_id = f"c{args.concurrency}_r{rep+1:02d}"
        print(f"\n=== 运行 {run_id} 并发={args.concurrency} ===")
        t0 = time.perf_counter()
        results = run_batch(tasks, args.concurrency, args.max_tokens)
        wall = time.perf_counter() - t0
        out_file = out_dir / f"run_{run_id}.jsonl"
        with open(out_file, "w", encoding="utf-8") as f:
            for r in results: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        ok = [r for r in results if r["status"] == "success"]
        total = sum(r["output_tokens"] for r in ok)
        print(f"  成功率 {len(ok)}/{len(results)}, 总token {total}, 墙钟 {wall:.2f}s, 吞吐 {total/wall:.2f} t/s")
        if ok:
            ttfts = [r["ttft_s"] for r in ok if r["ttft_s"]]
            if ttfts: print(f"  TTFT均值 {sum(ttfts)/len(ttfts):.3f}s")

if __name__ == "__main__":
    main()
