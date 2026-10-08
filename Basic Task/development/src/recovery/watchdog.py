#!/usr/bin/env python3
"""服务状态检测 + 自动重启"""
import time, subprocess, json, os
from datetime import datetime
from pathlib import Path
import requests

HEALTH = "http://localhost:8080/health"
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "results/recovery"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG = LOG_DIR / "watchdog.log"

SERVER_CMD = [
    "/home/lenovo/llama.cpp/build/bin/llama-server",
    "-m", "/home/lenovo/models/qwen2.5-3b-instruct-q4_k_m.gguf",
    "-ngl", "99", "-c", "65536", "-np", "4",
    "-ctk", "f16", "-ctv", "f16",
    "--host", "0.0.0.0", "--port", "8080"
]

def log(msg):
    line = f"{datetime.now().isoformat()} {msg}"
    print(line)
    with open(LOG, "a") as f: f.write(line + "\n")

def check_health():
    try:
        r = requests.get(HEALTH, timeout=3)
        return r.status_code == 200
    except: return False

def restart():
    log("检测到服务异常，开始重启")
    subprocess.run(["pkill", "-f", "llama-server"], check=False)
    time.sleep(2)
    logf = open("/home/lenovo/llama-server-watchdog.log", "a")
    subprocess.Popen(SERVER_CMD, stdout=logf, stderr=logf)
    log("已发起重启，等待就绪...")
    for i in range(60):
        time.sleep(2)
        if check_health():
            log(f"服务恢复就绪，耗时 {(i+1)*2}s")
            return True
    log("重启后仍未就绪")
    return False

if __name__ == "__main__":
    log("watchdog 启动")
    while True:
        if not check_health():
            log("健康检查失败")
            restart()
        time.sleep(5)
