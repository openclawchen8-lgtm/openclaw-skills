#!/usr/bin/env python3
"""md-viewer-app T003-B/C 進度回報"""
import os
import subprocess
import json

def load_telegram_config():
    config_path = os.path.expanduser("~/.qclaw/gold_monitor_config.json")
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return None

def send_telegram(message):
    config = load_telegram_config()
    if not config:
        print("No telegram config found")
        return
    
    token = config.get("telegram_token")
    chat_id = config.get("telegram_chat_id")
    if not token or not chat_id:
        print("Missing telegram token/chat_id")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    
    try:
        import urllib.request
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        print("Sent!")
    except Exception as e:
        print(f"Failed: {e}")

def check_progress():
    base = "/Users/claw/Projects/md-viewer-app"
    results = []
    
    # Check core/
    core_files = os.listdir(f"{base}/core") if os.path.exists(f"{base}/core") else []
    results.append(f"📁 core/: {', '.join(core_files) if core_files else '(empty)'}")
    
    # Check ui/
    ui_files = os.listdir(f"{base}/ui") if os.path.exists(f"{base}/ui") else []
    results.append(f"📁 ui/: {', '.join(ui_files) if ui_files else '(empty)'}")
    
    # Check assets/
    assets_files = os.listdir(f"{base}/assets") if os.path.exists(f"{base}/assets") else []
    results.append(f"📁 assets/: {', '.join(assets_files) if assets_files else '(empty)'}")
    
    # Check go build
    build_ok = os.path.exists(f"{base}/md-viewer")
    results.append(f"🔨 build: {'✅ done' if build_ok else '⏳ pending'}")
    
    message = "【md-viewer-app 進度】\n" + "\n".join(results)
    send_telegram(message)
    print(message)

if __name__ == "__main__":
    check_progress()