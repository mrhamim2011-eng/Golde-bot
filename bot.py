import os
import time
import requests
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Bot Control
BOT_ACTIVE = True
OPEN_TRADE = None
STATS = {"win": 0, "loss": 0, "total_pnl": 0}

def send_msg(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"Send Error: {e}")

def get_gold_data():
    try:
        df = yf.download("GC=F", period="5d", interval="15m", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        return df.dropna()
    except:
        return None

def check_signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = last['Close']
    rsi = last['RSI']
    atr = last['ATR']
    
    # BUY Logic: EMA Cross + RSI
    if prev['EMA20'] < prev['EMA50'] and last['EMA20'] > last['EMA50'] and 45 < rsi < 65:
        sl = price - (atr * 1.5)
        tp = price + (atr * 2.5)
        return "BUY", price, sl, tp
    # SELL Logic
    if prev['EMA20'] > prev['EMA50'] and last['EMA20'] < last['EMA50'] and 35 < rsi < 55:
        sl = price + (atr * 1.5)
        tp = price - (atr * 2.5)
        return "SELL", price, sl, tp
    return None, price, 0, 0

def telegram_listener():
    global BOT_ACTIVE
    last_update = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update+1}&timeout=20"
            r = requests.get(url, timeout=25).json()
            for update in r.get("result", []):
                last_update = update["update_id"]
                msg = update.get("message", {}).get("text", "")
                if "/on" in msg: 
                    BOT_ACTIVE = True
                    send_msg("✅ BOT চালু করা হলো")
                elif "/off" in msg: 
                    BOT_ACTIVE = False
                    send_msg("❌ BOT বন্ধ করা হলো")
                elif "/price" in msg:
                    df = get_gold_data()
                    if df is not None: send_msg(f"💰 এখন Gold Price: {df.iloc[-1]['Close']:.2f}")
                elif "/report" in msg:
                    send_msg(f"📊 <b>Report</b>\nWin: {STATS['win']}\nLoss: {STATS['loss']}\nTotal PnL: {STATS['total_pnl']:.2f}$")
                elif "/status" in msg:
                    status = "চালু 🟢" if BOT_ACTIVE else "বন্ধ 🔴"
                    trade = f"Trade চলছে: {OPEN_TRADE['type']}" if OPEN_TRADE else "কোনো Trade নেই"
                    send_msg(f"Status: {status}\n{trade}")
        except: time.sleep(5)
        time.sleep(2)

def main_loop():
    global OPEN_TRADE
    send_msg("🚀 <b>ULTIMATE GOLD BOT V5 চালু হয়েছে!</b>\n\n✅ প্রতি ৫ মিনিটে দাম বলবে\n✅ Signal পেলে BUY/SELL বলবে\n✅ লাভ/লস Auto জানাবে\n\nCommand:\n/on - চালু\n/off - বন্ধ\n/price - দাম\n/report - রিপোর্ট")
    
    while True:
        try:
            df = get_gold_data()
            if df is None:
                time.sleep(60); continue
            
            current_price = df.iloc[-1]['Close']
            now = datetime.now().strftime("%I:%M %p")

            # 1. Open Trade Check (লাভ/লস হয়েছে কিনা)
            if OPEN_TRADE:
                entry = OPEN_TRADE['entry']
                if OPEN_TRADE['type'] == "BUY":
                    if current_price >= OPEN_TRADE['tp']:
                        pnl = OPEN_TRADE['tp'] - entry
                        STATS["win"]+=1; STATS["total_pnl"]+=pnl
                        send_msg(f"✅ <b>TP HIT! লাভ হয়েছে</b> 💰\n{OPEN_TRADE['type']} @ {entry:.2f} -> {current_price:.2f}\nProfit: +{pnl:.2f}$"); OPEN_TRADE=None
                    elif current_price <= OPEN_TRADE['sl']:
                        pnl = current_price - entry
                        STATS["loss"]+=1; STATS["total_pnl"]+=pnl
                        send_msg(f"❌ <b>SL HIT! লস হয়েছে</b>\n{OPEN_TRADE['type']} @ {entry:.2f} -> {current_price:.2f}\nLoss: {pnl:.2f}$"); OPEN_TRADE=None
                else: # SELL
                    if current_price <= OPEN_TRADE['tp']:
                        pnl = entry - OPEN_TRADE['tp']
                        STATS["win"]+=1; STATS["total_pnl"]+=pnl
                        send_msg(f"✅ <b>TP HIT! লাভ হয়েছে</b> 💰\n{OPEN_TRADE['type']} @ {entry:.2f} -> {current_price:.2f}\nProfit: +{pnl:.2f}$"); OPEN_TRADE=None
                    elif current_price >= OPEN_TRADE['sl']:
                        pnl = entry - current_price
                        STATS["loss"]+=1; STATS["total_pnl"]+=pnl
                        send_msg(f"❌ <b>SL HIT! লস হয়েছে</b>\n{OPEN_TRADE['type']} @ {entry:.2f} -> {current_price:.2f}\nLoss: {pnl:.2f}$"); OPEN_TRADE=None

            # 2. New Signal Check
            if BOT_ACTIVE and not OPEN_TRADE:
                signal, price, sl, tp = check_signal(df)
                if signal:
                    OPEN_TRADE = {"type": signal, "entry": price, "sl": sl, "tp": tp}
                    emoji = "🟢" if signal == "BUY" else "🔴"
                    send_msg(f"{emoji} <b>{signal} SIGNAL</b> {emoji}\n\n💰 Entry: {price:.2f}\n❌ SL: {sl:.2f}\n✅ TP: {tp:.2f}\n⏰ Time: {now}\n\nএখন {signal} করতে পারো!")
                else:
                    send_msg(f"⏳ [{now}] Gold: {price:.2f} | RSI: {df.iloc[-1]['RSI']:.1f} | No Trade Setup")
            elif not OPEN_TRADE:
                 send_msg(f"⏸️ [{now}] Bot বন্ধ আছে। Gold: {current_price:.2f}")

            time.sleep(300) # 5 মিনিট পর পর
        except Exception as e:
            print(e); time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=telegram_listener, daemon=True).start()
    main_loop()
