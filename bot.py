import os, time, requests, yfinance as yf, pandas as pd, pandas_ta as ta
from datetime import datetime
import threading
BOT_TOKEN=os.getenv("BOT_TOKEN"); CHAT_ID=os.getenv("CHAT_ID")
BOT_ACTIVE=True; OPEN_TRADE=None; STATS={"win":0,"loss":0}
def send(t): requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":t,"parse_mode":"HTML"})
def get_data():
    df=yf.download("GC=F",period="2d",interval="15m",progress=False)
    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    df['EMA20']=ta.ema(df['Close'],20); df['EMA50']=ta.ema(df['Close'],50); df['RSI']=ta.rsi(df['Close'],14); df['ATR']=ta.atr(df['High'],df['Low'],df['Close'],14)
    return df.dropna()
def listener():
    global BOT_ACTIVE; last=0
    while True:
        try:
            r=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last+1}&timeout=15",timeout=20).json()
            for u in r.get("result",[]):
                last=u["update_id"]; m=u.get("message",{}).get("text","")
                if "/on" in m: BOT_ACTIVE=True; send("✅ BOT চালু")
                if "/off" in m: BOT_ACTIVE=False; send("❌ BOT বন্ধ")
                if "/price" in m: send(f"💰 Gold: {get_data().iloc[-1]['Close']:.2f}")
                if "/report" in m: send(f"Win:{STATS['win']} Loss:{STATS['loss']}")
        except: pass
        time.sleep(3)
threading.Thread(target=listener,daemon=True).start()
send("🚀 ULTIMATE BOT V5 চালু! প্রতি ৫ মিনিটে আপডেট পাবে। /on /off")
while True:
    try:
        df=get_data(); p=df.iloc[-1]['Close']; rsi=df.iloc[-1]['RSI']; now=datetime.now().strftime("%H:%M")
        if OPEN_TRADE is None and BOT_ACTIVE:
            if df.iloc[-2]['EMA20']<df.iloc[-2]['EMA50'] and df.iloc[-1]['EMA20']>df.iloc[-1]['EMA50'] and rsi>45:
                OPEN_TRADE={"type":"BUY","e":p,"sl":p-df.iloc[-1]['ATR']*1.5,"tp":p+df.iloc[-1]['ATR']*2.5}; send(f"🟢 BUY NOW\nEntry:{p:.2f}\nSL:{OPEN_TRADE['sl']:.2f}\nTP:{OPEN_TRADE['tp']:.2f}")
            elif df.iloc[-2]['EMA20']>df.iloc[-2]['EMA50'] and df.iloc[-1]['EMA20']<df.iloc[-1]['EMA50'] and rsi<55:
                OPEN_TRADE={"type":"SELL","e":p,"sl":p+df.iloc[-1]['ATR']*1.5,"tp":p-df.iloc[-1]['ATR']*2.5}; send(f"🔴 SELL NOW\nEntry:{p:.2f}\nSL:{OPEN_TRADE['sl']:.2f}\nTP:{OPEN_TRADE['tp']:.2f}")
            else: send(f"⏳ [{now}] Price:{p:.2f} RSI:{rsi:.1f} - Wait for setup")
        if OPEN_TRADE:
            if (OPEN_TRADE['type']=="BUY" and p>=OPEN_TRADE['tp']) or (OPEN_TRADE['type']=="SELL" and p<=OPEN_TRADE['tp']): send(f"✅ লাভ হয়েছে! {OPEN_TRADE['type']} TP Hit"); STATS['win']+=1; OPEN_TRADE=None
            if (OPEN_TRADE['type']=="BUY" and p<=OPEN_TRADE['sl']) or (OPEN_TRADE['type']=="SELL" and p>=OPEN_TRADE['sl']): send(f"❌ লস হয়েছে! {OPEN_TRADE['type']} SL Hit"); STATS['loss']+=1; OPEN_TRADE=None
        time.sleep(300)
    except Exception as e: print(e); time.sleep(60)
