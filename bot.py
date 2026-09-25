import yfinance as yf, requests, time, pandas as pd, threading, random
BOT_TOKEN="8975288953:AAENyWD2nWDaMAUeYsMKPpGv-_dj6dCgFiw"
CHAT_ID="8960830581"
is_running=True
last_update_id=0

def send_msg(t):
    try:
        url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": t, "parse_mode":"Markdown"}, timeout=15)
    except: pass

def listen():
    global is_running, last_update_id
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id+1}&timeout=20"
            r = requests.get(url, timeout=25).json()
            for u in r.get("result",[]):
                last_update_id=u["update_id"]
                txt=u.get("message",{}).get("text","").lower()
                cid=str(u.get("message",{}).get("chat",{}).get("id",""))
                if cid!=CHAT_ID: continue
                if txt in ["/stop","stop","off"]: is_running=False; send_msg("⏸️ *High-Tech Bot বন্ধ হলো*")
                if txt in ["/start","start","on"]: is_running=True; send_msg("🚀 *High-Tech Bot চালু হলো*")
        except: pass
        time.sleep(2)

def get_analysis():
    try:
        df=yf.download("GC=F", period="10d", interval="15m", progress=False, auto_adjust=True)
        if df.empty: return None
        c=df['Close']; 
        if hasattr(c,'shape') and len(c.shape)>1: c=c.iloc[:,0]
        h=df['High'].iloc[:,0] if hasattr(df['High'],'shape') and len(df['High'].shape)>1 else df['High']
        l=df['Low'].iloc[:,0] if hasattr(df['Low'],'shape') and len(df['Low'].shape)>1 else df['Low']
        
        price=float(c.iloc[-1])
        # SMC & Indicators
        ema20=float(c.ewm(20).mean().iloc[-1]); ema50=float(c.ewm(50).mean().iloc[-1]); ema200=float(c.ewm(200).mean().iloc[-1])
        delta=c.diff(); gain=delta.where(delta>0,0).rolling(14).mean(); loss=-delta.where(delta<0,0).rolling(14).mean()
        rsi=float((100-(100/(1+gain/loss))).iloc[-1])
        atr=float((h-l).rolling(14).mean().iloc[-1])
        
        # SMC Logic
        recent_high=float(h.tail(20).max()); recent_low=float(l.tail(20).min())
        bos = "Bullish BOS" if price > recent_high*0.998 else "Bearish BOS" if price < recent_low*1.002 else "No BOS"
        fvg = "Bullish FVG Found" if (l.iloc[-2] > h.iloc[-4]) else "Bearish FVG Found" if (h.iloc[-2] < l.iloc[-4]) else "No FVG"
        
        score=50
        if ema20>ema50>ema200: score+=20
        if ema20<ema50<ema200: score-=20
        if rsi<30: score+=15
        if rsi>70: score-=15
        if "Bullish" in bos: score+=15
        if "Bearish" in bos: score-=15
        
        signal = "BUY 🟢" if score>=70 else "SELL 🔴" if score<=30 else "WAIT 🟡"
        sl = price - atr*1.5 if signal=="BUY 🟢" else price + atr*1.5 if signal=="SELL 🔴" else 0
        tp = price + atr*3 if signal=="BUY 🟢" else price - atr*3 if signal=="SELL 🔴" else 0
        
        return price,rsi,ema20,ema50,score,signal,sl,tp,bos,fvg,atr
    except Exception as e:
        print(e); return None

threading.Thread(target=listen, daemon=True).start()
send_msg("💎 *NEXT LEVEL GOLD BOT চালু!*\n\nFeatures: SMC + BOS + FVG + AI Score + TP/SL\n/stop - বন্ধ\n/start - চালু")

last=0
while True:
    if is_running and time.time()-last>180: # 3 মিনিট পর পর
        d=get_analysis()
        if d:
            p,rsi,e20,e50,score,sig,sl,tp,bos,fvg,atr=d
            if sig!="WAIT 🟡":
                send_msg(f"⚡️ *GOLD HIGH-TECH SIGNAL* ⚡️\n\n💰 Price: ${p:.2f}\n📈 Signal: *{sig}*\n🎯 AI Score: *{score}/100*\n\n📊 RSI: {rsi:.1f} | ATR: {atr:.1f}\n🔹 BOS: {bos}\n🔹 FVG: {fvg}\n\n🎯 TP: ${tp:.2f}\n🛑 SL: ${sl:.2f}\n\n⏰ Time: 15M SMC")
            else:
                send_msg(f"💰 *GOLD: ${p:.2f}* | WAIT 🟡\nScore: {score}/100 | RSI: {rsi:.1f}\nBOS: {bos} | No clear entry")
            last=time.time()
    time.sleep(10)
