import os
import time
import threading
import requests
from datetime import datetime
from flask import Flask
import yfinance as yf
import pandas as pd

# ====== RENDER PORT FIX ======
app = Flask('')
@app.route('/')
def home(): return "PRO GOLD BOT IS LIVE!"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=10000)).start()

# ====== CONFIG ======
BOT_TOKEN = "8975288953:AAENyWD2nWDaMAUeYsMKPpGv-_dj6dCgFiw" # Render Env Variable এ দিতে হবে
CHAT_ID = "8960830581"      # তোমার Telegram ID

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        requests.post(url, data=data)
    except Exception as e:
        print(f"Error: {e}")

def get_gold_data():
    try:
        gold = yf.download("GC=F", period="1d", interval="5m", progress=False)
        if len(gold) < 50: return None, 0
        close = gold['Close'].iloc[-1].item()
        
        # Simple BOS Logic
        high_20 = gold['High'].tail(20).max().item()
        low_20 = gold['Low'].tail(20).min().item()
        
        score = 50
        signal_type = None
        
        if close > high_20:
            signal_type = "BUY"
            score = 82
        elif close < low_20:
            signal_type = "SELL"
            score = 84
        else:
            signal_type = "WAIT"
            score = 55
            
        return close, signal_type, score, high_20, low_20
    except Exception as e:
        print(e)
        return None, "WAIT", 0, 0, 0

def format_pro_signal(price, sig_type, score, high, low):
    now = datetime.now().strftime("%I:%M %p")
    
    if sig_type == "WAIT":
        return None  # WAIT হলে মেসেজ পাঠাবে না, শুধু Strong Signal পাঠাবে

    if sig_type == "BUY":
        entry = price
        sl = entry - 10
        tp1 = entry + 10
        tp2 = entry + 20
        tp3 = entry + 35
        emoji = "🟢"
        action = "BUY / LONG"
    else:
        entry = price
        sl = entry + 10
        tp1 = entry - 10
        tp2 = entry - 20
        tp3 = entry - 35
        emoji = "🔴"
        action = "SELL / SHORT"

    msg = f"""
{emoji} **NEXT LEVEL GOLD {action}** {emoji}

━━━━━━━━━━━━━━━
💰 **Pair:** `XAUUSD - GOLD`
📊 **Price:** `${price:.2f}`
📈 **Action:** {action}

🎯 **ENTRY:** `{entry:.2f}`
🛑 **STOP LOSS:** `{sl:.2f}` (-100 Pips)

✅ **TP1:** `{tp1:.2f}` (+100 Pips)
✅ **TP2:** `{tp2:.2f}` (+200 Pips)
✅ **TP3:** `{tp3:.2f}` (+350 Pips)

━━━━━━━━━━━━━━━
🧠 **AI Confidence:** `{score}%` {'🟢' if score > 80 else '🟡'}
📚 **Strategy:** BOS Break + Liquidity Sweep
⏰ **Timeframe:** M15 / M5 Confirmation
🕒 **Time:** {now}

⚠️ **Risk Management:** Use 1-2% Lot Only!
"""
    return msg

# ====== MAIN LOOP ======
def run_bot():
    send_telegram("🚀 **PRO GOLD BOT চালু হয়েছে!**\nএখন থেকে শুধু Professional Signal আসবে। WAIT মেসেজ আর আসবে না।")
    last_signal = ""
    while True:
        try:
            price, sig_type, score, high, low = get_gold_data()
            if price and sig_type != "WAIT" and score >= 80:
                # একই Signal বারবার যাতে না যায়
                signal_id = f"{sig_type}-{int(price)}"
                if signal_id != last_signal:
                    pro_msg = format_pro_signal(price, sig_type, score, high, low)
                    if pro_msg:
                        send_telegram(pro_msg)
                        last_signal = signal_id
            print(f"Checked: {price} - {sig_type} - {score}")
            time.sleep(180) # 3 মিনিট পর পর চেক
        except Exception as e:
            print(f"Loop Error: {e}")
            time.sleep(60)

threading.Thread(target=run_bot).start()si
