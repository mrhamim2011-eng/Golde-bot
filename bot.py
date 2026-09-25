import os, time, requests, yfinance as yf, json
import pandas as pd
import pandas_ta as ta
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Bot State
STATE_FILE = "bot_state.json"
def load_state():
    try:
        with open(STATE_FILE, 'r') as f: return json.load(f)
    except: return {"is_on": True, "wins": 0, "losses": 0, "active_trade": None}

def save_state(s):
    with open(STATE_FILE, 'w') as f: json.dump(f, f)

state = load_state()
last_update_id = 0

def send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try: requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def check_commands():
    global last_update_id, state
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=5"
        r = requests.get(url, timeout=10).json()
        for upd in r.get("result", []):
            last_update_id = upd["update_id"]
            msg = upd.get("message", {}).get("text", "").lower()
            if "/on" in msg or "/start" in msg:
                state["is_on"] = True; save_state(state)
                send("🟢 *BOT ON* - এখন থেকে প্রতি 5 মিনিটে Price + Signal আসবে")
            elif "/off" in msg or "/stop" in msg:
                state["is_on"] = False; save_state(state)
                send("🔴 *BOT OFF* - বট বন্ধ করা হলো। চালু করতে /on লিখো")
            elif "/report" in msg:
                total = state["wins"]+state["losses"]
                wr = (state["wins"]/total*100) if total>0 else 0
                send(f"📊 *REPORT*\nWin: {state['wins']}\nLoss: {state['losses']}\nWin Rate: {wr:.1f}%")
            elif "/price" in msg:
                p = yf.download("XAUUSD=X", period="1d", interval="1m", progress=False)['Close'].iloc[-1]
                send(f"💵 *XAUUSD Live:* `${p:.2f}`")
    except: pass

def analyze_xau():
    df = yf.download("XAUUSD=X", period="5d", interval="5m", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.ta.ema(length=50, append=True); df.ta.ema(length=200, append=True)
    df.ta.rsi(length=14, append=True); df.ta.macd(append=True); df.ta.atr(length=14, append=True)
    df = df.dropna()
    l = df.iloc[-1]
    price = float(l['Close']); atr = float(l['ATRr_14'])
    
    score = 0
    if l['EMA_50'] > l['EMA_200']: score+=40
    else: score-=40
    if l['RSI_14']>55 and l['RSI_14']<70: score+=30
    if l['RSI_14']<45 and l['RSI_14']>30: score-=30
    if l['MACD_12_26_9'] > l['MACDs_12_26_9']: score+=30
    else: score-=30

    if score >= 75: return "BUY", price, price-atr*1.8, price+atr*3, score
    if score <= -75: return "SELL", price, price+atr*1.8, price-atr*3, abs(score)
    return None, price, None, None, score

def check_trade_result(current_price):
    global state
    if not state["active_trade"]: return
    tr = state["active_trade"]
    side, entry, sl, tp = tr["side"], tr["entry"], tr["sl"], tr["tp"]
    
    hit_tp = (side=="BUY" and current_price>=tp) or (side=="SELL" and current_price<=tp)
    hit_sl = (side=="BUY" and current_price<=sl) or (side=="SELL" and current_price>=sl)

    if hit_tp:
        state["wins"]+=1; state["active_trade"]=None; save_state(state)
        send(f"✅ *TP HIT - PROFIT* 💰\n{side} {entry:.2f} -> {current_price:.2f}\n+${abs(tp-entry):.2f} Profit")
    elif hit_sl:
        state["losses"]+=1; state["active_trade"]=None; save_state(state)
        send(f"❌ *SL HIT - LOSS*\n{side} {entry:.2f} -> {current_price:.2f}\n-${abs(entry-sl):.2f} Loss")

# START
send("🚀 *XAUUSD V4 ULTIMATE LIVE*\n\nCommands:\n/on - Bot চালু\n/off - Bot বন্ধ\n/report - লাভ/লস রিপোর্ট\n/price - এখনকার Price")

while True:
    try:
        check_commands()
        if not state["is_on"]:
            time.sleep(5); continue

        side, price, sl, tp, score = analyze_xau()
        if price: check_trade_result(price)

        # Price Update
        if side: # Signal
            emoji = "🟢📈 BUY" if side=="BUY" else "🔴📉 SELL"
            state["active_trade"] = {"side": side, "entry": price, "sl": sl, "tp": tp}
            save_state(state)
            send(f"🔥 *{emoji} XAUUSD SIGNAL* | Score {score}%\n\n*Entry:* `{price:.2f}`\n*SL:* `{sl:.2f}` ({abs(price-sl):.2f}$)\n*TP:* `{tp:.2f}` ({abs(tp-price):.2f}$)\nRR: 1:1.6\n\nএখন Trade নিতে পারো")
        else:
            send(f"💵 *XAUUSD:* `${price:.2f}` | Score: {score}% | No Trade - Waiting...")

        time.sleep(300) # 5 min
    except Exception as e:
        print(e); time.sleep(30)
