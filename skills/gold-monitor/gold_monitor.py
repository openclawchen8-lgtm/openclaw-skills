#!/usr/bin/env python3
"""
台灣銀行黃金存摺價格監控腳本
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta

# 配置
CONFIG_FILE = os.path.expanduser("~/.qclaw/gold_monitor_config.json")
STATE_FILE = os.path.expanduser("~/.qclaw/gold_monitor_state.json")
HISTORY_FILE = os.path.expanduser("~/.qclaw/gold_price_history.json")

# Telegram 配置從環境變數或配置檔讀取
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def load_config():
    """載入配置"""
    default_config = {
        "threshold": 50,  # 價格變動閾值（元）
        "notify_final_only": False,  # 是否只在 15:30 通知
        "price_targets": [],  # 特定價格點位監控
        # 格式: [{"price": 4500, "type": "buy", "label": "買入點", "triggered": False}, ...]
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return {**default_config, **json.load(f)}
    return default_config

def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def load_state():
    """載入狀態"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_price": None, "last_notify_time": None}

def save_state(state):
    """保存狀態"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def load_history():
    """載入歷史價格"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {"daily": {}, "intraday": {}}

def save_history(history):
    """保存歷史價格"""
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def record_price(price, time_str, is_daily_close=False):
    """記錄價格到歷史"""
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 記錄日內價格
    if today not in history["intraday"]:
        history["intraday"][today] = []
    
    history["intraday"][today].append({
        "time": time_str,
        "price": price,
        "timestamp": datetime.now().isoformat()
    })
    
    # 如果是收盤，記錄到每日歷史
    if is_daily_close:
        history["daily"][today] = {
            "price": price,
            "time": time_str
        }
    
    # 清理超過 30 天的歷史
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    history["intraday"] = {k: v for k, v in history["intraday"].items() if k >= cutoff}
    history["daily"] = {k: v for k, v in history["daily"].items() if k >= cutoff}
    
    save_history(history)
    return history

def fetch_gold_price():
    """使用瀏覽器抓取台銀黃金存摺價格"""
    import tempfile
    import shutil
    
    # 創建臨時目錄
    tmp_dir = tempfile.mkdtemp()
    
    # 使用 Playwright 通過 node 腳本抓取
    script = '''
import { chromium } from 'playwright';

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.goto('https://rate.bot.com.tw/gold?Lang=zh-TW', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    const content = await page.content();
    const sellMatch = content.match(/本行賣出[\\s\\S]*?(\\d{1,3},\\d{3})/);
    const buyMatch = content.match(/本行買進[\\s\\S]*?(\\d{1,3},\\d{3})/);
    const timeMatch = content.match(/掛牌時間[\\uff1a:]\\s*(\\d{4}\\/\\d{2}\\/\\d{2}\\s+\\d{2}:\\d{2})/);
    
    const result = {
        sell_price: sellMatch ? parseInt(sellMatch[1].replace(',', '')) : null,
        buy_price: buyMatch ? parseInt(buyMatch[1].replace(',', '')) : null,
        time: timeMatch ? timeMatch[1] : null
    };
    
    console.log(JSON.stringify(result));
    await browser.close();
})();
'''
    
    # 複製 node_modules 到臨時目錄
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    src_modules = os.path.join(scripts_dir, 'node_modules')
    if os.path.exists(src_modules):
        shutil.copytree(src_modules, os.path.join(tmp_dir, 'node_modules'))
    
    script_path = os.path.join(tmp_dir, 'fetch.mjs')
    with open(script_path, 'w') as f:
        f.write(script)
    
    try:
        result = subprocess.run(
            ['node', script_path],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=tmp_dir
        )
        shutil.rmtree(tmp_dir)
        
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        else:
            print(f"Error: {result.stderr}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Exception: {e}", file=sys.stderr)
        if os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)
        return None

def send_telegram_message(text, photo_path=None):
    """發送 Telegram 訊息"""
    import urllib.request
    import urllib.parse
    
    # 從配置檔讀取 Telegram 設定
    config = load_config()
    bot_token = config.get("telegram_bot_token", TELEGRAM_BOT_TOKEN)
    chat_id = config.get("telegram_chat_id", TELEGRAM_CHAT_ID)
    
    if not bot_token or not chat_id:
        print("❌ 未設定 Telegram Bot Token 或 Chat ID", file=sys.stderr)
        print("   請設定環境變數或在配置檔中加入：", file=sys.stderr)
        print('   {"telegram_bot_token": "YOUR_TOKEN", "telegram_chat_id": "YOUR_CHAT_ID"}', file=sys.stderr)
        return None
    
    if photo_path:
        # 發送圖片
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        with open(photo_path, 'rb') as photo:
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "caption": text,
                "parse_mode": "HTML"
            }).encode()
            # Multipart form data
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            body = []
            body.append(f'--{boundary}\r\n'.encode())
            body.append(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode())
            body.append(f'--{boundary}\r\n'.encode())
            body.append(f'Content-Disposition: form-data; name="photo"; filename="chart.png"\r\n'.encode())
            body.append(b'Content-Type: image/png\r\n\r\n')
            body.append(photo.read())
            body.append(f'\r\n--{boundary}\r\n'.encode())
            body.append(f'Content-Disposition: form-data; name="caption"\r\n\r\n{text}\r\n'.encode())
            body.append(f'--{boundary}\r\n'.encode())
            body.append(f'Content-Disposition: form-data; name="parse_mode"\r\n\r\nHTML\r\n'.encode())
            body.append(f'--{boundary}--\r\n'.encode())
            
            req = urllib.request.Request(url, data=b''.join(body))
            req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
    else:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }).encode()
        
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())

def generate_price_chart(history, current_price, current_time):
    """生成價格走勢圖"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime
    
    # 設置中文字體
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang TC', 'Heiti TC', 'STHeiti', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 收集數據點
    dates = []
    prices = []
    
    # 獲取前一個交易日的收盤價
    # 週一 → 上週五，週二~週四 → 前一天
    today_dt = datetime.now()
    weekday = today_dt.weekday()  # 0=週一, 1=週二, ..., 4=週五
    
    if weekday == 0:  # 週一
        # 找上週五（3天前）
        prev_trading_day = (today_dt - timedelta(days=3)).strftime("%Y-%m-%d")
    else:
        # 週二~週五，找前一天
        prev_trading_day = (today_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    
    if prev_trading_day in history["daily"]:
        prev_close = history["daily"][prev_trading_day]["price"]
        prev_time = history["daily"][prev_trading_day].get("time", "15:30")
        if "/" in prev_time:
            dt = datetime.strptime(prev_time, "%Y/%m/%d %H:%M")
        else:
            dt = datetime.strptime(f"{prev_trading_day} {prev_time}", "%Y-%m-%d %H:%M")
        dates.append(dt)
        prices.append(prev_close)
    
    # 加入今天的日內價格
    today = datetime.now().strftime("%Y-%m-%d")
    if today in history["intraday"]:
        for point in history["intraday"][today]:
            time_str = point["time"]
            if "/" in time_str:
                dt = datetime.strptime(time_str, "%Y/%m/%d %H:%M")
            else:
                dt = datetime.strptime(f"{today} {time_str}", "%Y-%m-%d %H:%M")
            dates.append(dt)
            prices.append(point["price"])
    
    # 加入當前價格
    if "/" in current_time:
        now_dt = datetime.strptime(current_time, "%Y/%m/%d %H:%M")
    else:
        now_dt = datetime.now()
    dates.append(now_dt)
    prices.append(current_price)
    
    if len(dates) < 2:
        return None
    
    # 創建圖表
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # 繪製價格線
    ax.plot(dates, prices, 'b-', linewidth=2, marker='o', markersize=4)
    
    # 標記最新價格
    ax.scatter([dates[-1]], [prices[-1]], color='red', s=100, zorder=5)
    ax.annotate(f'{prices[-1]:,}', xy=(dates[-1], prices[-1]), 
                xytext=(10, 10), textcoords='offset points',
                fontsize=12, fontweight='bold', color='red')
    
    # 設置格式
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    plt.xticks(rotation=45)
    
    ax.set_ylabel('價格 (元/公克)', fontsize=12)
    ax.set_title('黃金存摺價格走勢', fontsize=14, fontweight='bold')
    
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_ylim(min(prices) - 20, max(prices) + 20)
    
    plt.tight_layout()
    
    # 保存圖片
    chart_path = "/tmp/gold_chart.png"
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path

def format_price_change(old_price, new_price, threshold):
    """格式化價格變動訊息"""
    change = new_price - old_price
    change_pct = (change / old_price) * 100
    direction = "📈 上漲" if change > 0 else "📉 下跌"
    
    return f"""🔔 <b>黃金存摺價格變動通知</b>

{direction} <b>{abs(change):,} 元</b> ({change_pct:+.2f}%)

📊 <b>目前價格</b>
• 本行賣出：<b>{new_price:,} 元/公克</b>
• 前次價格：{old_price:,} 元/公克

⏰ 時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📉 閾值設定：±{threshold} 元"""

def format_daily_report(price, time_str, prev_price=None, is_monday=False):
    """格式化日報"""
    change_str = ""
    if prev_price:
        change = price - prev_price
        change_pct = (change / prev_price) * 100
        direction = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        period = "週五" if is_monday else "前日"
        change_str = f"""
{direction} <b>較上{period}變動</b>：{change:+,} 元 ({change_pct:+.2f}%)
上{period}收盤：{prev_price:,} 元/公克"""
    
    return f"""📊 <b>黃金存摺每日收盤報告</b>

💰 <b>本行賣出</b>：{price:,} 元/公克
📅 掛牌時間：{time_str}{change_str}

⏰ 報告時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

def format_price_target_alert(price, target, current_price):
    """格式化價格點位觸發通知"""
    target_type = "買入" if target["type"] == "buy" else "賣出"
    emoji = "🟢" if target["type"] == "buy" else "🔴"
    direction = "跌破" if current_price <= target["price"] else "突破"
    
    return f"""{emoji} <b>黃金存摺價格點位觸發</b>

🎯 <b>{target_type}點位</b>：{target['price']:,} 元/公克
📊 <b>目前價格</b>：{current_price:,} 元/公克
📈 已{direction}目標價格！

📝 備註：{target.get('label', '無')}
⏰ 時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

def check_price_targets(config, current_price):
    """檢查價格點位"""
    targets = config.get("price_targets", [])
    triggered = []
    
    for target in targets:
        if target.get("triggered", False):
            continue  # 已觸發過，跳過
        
        price = target["price"]
        target_type = target["type"]
        
        # 買入點：價格跌到或跌破目標
        # 賣出點：價格漲到或突破目標
        should_trigger = False
        if target_type == "buy" and current_price <= price:
            should_trigger = True
        elif target_type == "sell" and current_price >= price:
            should_trigger = True
        
        if should_trigger:
            triggered.append(target)
            target["triggered"] = True
    
    return triggered

def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description="台銀黃金存摺價格監控")
    parser.add_argument("--check", action="store_true", help="檢查價格變動")
    parser.add_argument("--daily", action="store_true", help="發送每日報告")
    parser.add_argument("--set-threshold", type=int, help="設定價格變動閾值")
    parser.add_argument("--config", action="store_true", help="顯示當前配置")
    parser.add_argument("--add-target", type=str, help="新增價格點位 (格式: price:type:label，如 4500:buy:進場點)")
    parser.add_argument("--remove-target", type=int, help="移除價格點位 (價格)")
    parser.add_argument("--list-targets", action="store_true", help="列出所有價格點位")
    parser.add_argument("--reset-targets", action="store_true", help="重置所有點位的觸發狀態")
    args = parser.parse_args()
    
    config = load_config()
    state = load_state()
    
    if args.set_threshold:
        config["threshold"] = args.set_threshold
        save_config(config)
        print(f"✅ 閾值已設定為 {args.set_threshold} 元")
        return
    
    if args.add_target:
        # 新增價格點位
        parts = args.add_target.split(":")
        if len(parts) < 2:
            print("❌ 格式錯誤，正確格式: price:type:label")
            print("   例如: 4500:buy:進場點")
            print("   type: buy (買入) 或 sell (賣出)")
            sys.exit(1)
        
        price = int(parts[0])
        target_type = parts[1].lower()
        label = parts[2] if len(parts) > 2 else f"{target_type}點位"
        
        if target_type not in ["buy", "sell"]:
            print("❌ type 必須是 buy 或 sell")
            sys.exit(1)
        
        if "price_targets" not in config:
            config["price_targets"] = []
        
        config["price_targets"].append({
            "price": price,
            "type": target_type,
            "label": label,
            "triggered": False
        })
        save_config(config)
        
        type_name = "買入" if target_type == "buy" else "賣出"
        print(f"✅ 已新增 {type_name}點位：{price:,} 元 ({label})")
        return
    
    if args.remove_target:
        # 移除價格點位
        targets = config.get("price_targets", [])
        original_count = len(targets)
        config["price_targets"] = [t for t in targets if t["price"] != args.remove_target]
        
        if len(config["price_targets"]) < original_count:
            save_config(config)
            print(f"✅ 已移除價格點位：{args.remove_target:,} 元")
        else:
            print(f"❌ 找不到價格點位：{args.remove_target:,} 元")
        return
    
    if args.list_targets:
        # 列出所有價格點位
        targets = config.get("price_targets", [])
        if not targets:
            print("目前沒有設定價格點位")
            return
        
        print("📊 價格點位列表：")
        for i, t in enumerate(targets, 1):
            type_name = "買入" if t["type"] == "buy" else "賣出"
            status = "✅ 已觸發" if t.get("triggered") else "⏳ 待觸發"
            print(f"  {i}. {t['price']:,} 元 - {type_name} ({t.get('label', '')}) {status}")
        return
    
    if args.reset_targets:
        # 重置所有點位的觸發狀態
        targets = config.get("price_targets", [])
        for t in targets:
            t["triggered"] = False
        config["price_targets"] = targets
        save_config(config)
        print(f"✅ 已重置 {len(targets)} 個價格點位的觸發狀態")
        return
    
    if args.config:
        print(f"當前配置：")
        print(f"  閾值：{config['threshold']} 元")
        print(f"  價格點位：{len(config.get('price_targets', []))} 個")
        print(f"  狀態：{state}")
        return
    
    # 抓取價格
    price_data = fetch_gold_price()
    
    if not price_data or not price_data.get("sell_price"):
        print("❌ 無法獲取價格數據", file=sys.stderr)
        sys.exit(1)
    
    current_price = price_data["sell_price"]
    current_time = price_data.get("time", datetime.now().strftime("%Y/%m/%d %H:%M"))
    
    if args.daily:
        # 發送每日報告
        history = record_price(current_price, current_time, is_daily_close=True)
        
        # 獲取前一個交易日的收盤價
        # 週一 → 上週五，週二~週四 → 前一天
        today_dt = datetime.now()
        weekday = today_dt.weekday()  # 0=週一, 1=週二, ..., 4=週五
        
        if weekday == 0:  # 週一
            prev_trading_day = (today_dt - timedelta(days=3)).strftime("%Y-%m-%d")
            is_monday = True
        else:
            prev_trading_day = (today_dt - timedelta(days=1)).strftime("%Y-%m-%d")
            is_monday = False
        
        prev_price = history["daily"].get(prev_trading_day, {}).get("price")
        
        # 生成走勢圖
        chart_path = generate_price_chart(history, current_price, current_time)
        
        msg = format_daily_report(current_price, current_time, prev_price, is_monday)
        
        if chart_path and os.path.exists(chart_path):
            send_telegram_message(msg, chart_path)
        else:
            send_telegram_message(msg)
        
        print(f"✅ 已發送每日報告：{current_price:,} 元")
        return
    
    if args.check:
        # 記錄價格
        history = record_price(current_price, current_time, is_daily_close=False)
        
        # 檢查價格點位
        triggered_targets = check_price_targets(config, current_price)
        for target in triggered_targets:
            msg = format_price_target_alert(target["price"], target, current_price)
            send_telegram_message(msg)
            print(f"🎯 價格點位觸發：{target['price']:,} 元 ({target['type']})")
        
        # 保存更新後的配置（觸發狀態）
        if triggered_targets:
            save_config(config)
        
        # 檢查價格變動
        last_price = state.get("last_price")
        
        if last_price is None:
            # 首次運行，只記錄價格
            state["last_price"] = current_price
            state["last_time"] = current_time
            save_state(state)
            print(f"✅ 首次運行，已記錄價格：{current_price:,} 元")
            return
        
        price_change = abs(current_price - last_price)
        threshold = config["threshold"]
        
        if price_change >= threshold:
            # 價格變動超過閾值，發送通知
            msg = format_price_change(last_price, current_price, threshold)
            send_telegram_message(msg)
            print(f"✅ 價格變動 {price_change} 元，已發送通知")
        
        # 更新狀態
        state["last_price"] = current_price
        state["last_time"] = current_time
        save_state(state)
        print(f"📊 目前價格：{current_price:,} 元（變動：{price_change} 元）")

if __name__ == "__main__":
    main()
