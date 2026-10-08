#!/usr/bin/env python3
from flask import Flask, jsonify, render_template, request
import requests, json
from pathlib import Path

app = Flask(__name__)
DEV = Path(__file__).resolve().parent.parent.parent
RESULTS = DEV / "results"
SERVER = "http://localhost:8080"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/health")
def health():
    try:
        r = requests.get(f"{SERVER}/health", timeout=2)
        return jsonify({"ok": r.status_code == 200})
    except: return jsonify({"ok": False})

@app.route("/api/results")
def results():
    cfg = request.args.get("config", "baseline")
    out = []
    for f in sorted((RESULTS / cfg).glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            try: out.append(json.loads(line))
            except: pass
    return jsonify(out)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
