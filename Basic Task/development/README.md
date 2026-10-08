# 基础任务开发说明

## 所选方向
基础任务（本地推理服务 + 性能测试 + 前端展示 + 服务恢复 + KV 优化）

## 最终分支
master

## 最终 Commit SHA
8108dac

## 模型信息
- 模型：Qwen2.5-3B-Instruct
- 量化：Q4_K_M
- 来源：https://hf-mirror.com/Qwen/Qwen2.5-3B-Instruct-GGUF
- 文件：qwen2.5-3b-instruct-q4_k_m.gguf（约 2.0 GB）

## 运行入口
- 启动推理服务：见 configs/baseline.conf
- 性能测试：python3 src/benchmark/benchmark.py --concurrency 1 --repeat 3 --config-name baseline
- 前端展示：python3 src/frontend/app.py，访问 http://localhost:5000
- 服务恢复：python3 src/recovery/watchdog.py

## 报告位置
reports/基础阶段考核报告.md

## 测试数据位置
- 基线：results/baseline/
- 优化：results/optimized/
- 恢复：results/recovery/
