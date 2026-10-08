#!/usr/bin/env python3
import json, glob, statistics
from pathlib import Path
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt

def load(strategy):
    high, low = [], []
    for f in glob.glob(f"results/{strategy}/*.jsonl"):
        for line in open(f):
            r = json.loads(line)
            (high if r["priority"] == 0 else low).append(r["total_latency_s"])
    return high, low

fifo_h, fifo_l = load("fifo")
pri_h, pri_l = load("priority")

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# 图1：总延迟均值
labels = ["高优先级", "低优先级"]
fifo_avg = [statistics.mean(fifo_h), statistics.mean(fifo_l)]
pri_avg = [statistics.mean(pri_h), statistics.mean(pri_l)]
x = range(2)
axes[0].bar([i-0.2 for i in x], fifo_avg, width=0.4, label="FIFO", color="tab:red")
axes[0].bar([i+0.2 for i in x], pri_avg, width=0.4, label="Priority", color="tab:green")
axes[0].set_xticks(x); axes[0].set_xticklabels(labels)
axes[0].set_ylabel("总延迟 (s)"); axes[0].set_title("总延迟对比")
axes[0].legend(); axes[0].grid(True, alpha=0.3, axis="y")
for i, (f, p) in enumerate(zip(fifo_avg, pri_avg)):
    axes[0].text(i-0.2, f+1, f"{f:.1f}s", ha="center", fontsize=9)
    axes[0].text(i+0.2, p+1, f"{p:.1f}s", ha="center", fontsize=9)

# 图2：排队时间对比
def queue_stats(strategy):
    high, low = [], []
    for f in glob.glob(f"results/{strategy}/*.jsonl"):
        for line in open(f):
            r = json.loads(line)
            (high if r["priority"] == 0 else low).append(r["queue_wait_s"])
    return high, low

fq_h, fq_l = queue_stats("fifo")
pq_h, pq_l = queue_stats("priority")
fifo_q = [statistics.mean(fq_h), statistics.mean(fq_l)]
pri_q = [statistics.mean(pq_h), statistics.mean(pq_l)]
axes[1].bar([i-0.2 for i in x], fifo_q, width=0.4, label="FIFO", color="tab:red")
axes[1].bar([i+0.2 for i in x], pri_q, width=0.4, label="Priority", color="tab:green")
axes[1].set_xticks(x); axes[1].set_xticklabels(labels)
axes[1].set_ylabel("排队等待 (s)"); axes[1].set_title("排队时间对比")
axes[1].legend(); axes[1].grid(True, alpha=0.3, axis="y")

plt.tight_layout()
plt.savefig("results/scheduler_comparison.png", dpi=150)
print("图已保存到 results/scheduler_comparison.png")
