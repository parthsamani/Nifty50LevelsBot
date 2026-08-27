import os, asyncio, pandas as pd
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from io import BytesIO
from curl_cffi import requests as cffi_requests
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) # Apni Telegram ID yaha env me daal dena
app = Flask(__name__)

session = cffi_requests.Session(impersonate="chrome110")

FNO = ["RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","AXISBANK.NS","KOTAKBANK.NS","TCS.NS","INFY.NS","LT.NS","ITC.NS","BHARTIARTL.NS","BAJFINANCE.NS","MARUTI.NS","M&M.NS","TATAMOTORS.NS","SUNPHARMA.NS","HCLTECH.NS","WIPRO.NS","ADANIENT.NS","ADANIPOWER.NS","ADANIPORTS.NS","TATAPOWER.NS","TATASTEEL.NS","JSWSTEEL.NS","ZOMATO.NS","JIOFIN.NS","HYUNDAI.NS"]

user_settings = {}
trade_log = {}
user_tracking = {} # Tracking system

def get_ist():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

def get_settings(chat_id):
    return user_settings.get(chat_id, {"near": 1.0, "move": 0.5, "sl": 0.5, "target_ratio": 2})

def track_user(update: Update):
    try:
        user = update.effective_user
        chat = update.effective_chat
        uid = user.id
        now_str = get_ist().strftime('%d-%m-%Y %I:%M:%S %p')

        if uid not in user_tracking:
            user_tracking[uid] = {
                "user_id": uid,
                "name": user.full_name,
                "username": f"@{user.username}" if user.username else "No username",
                "chat_type": chat.type,
                "chat_id": chat.id,
                "first_seen": now_str,
                "last_seen": now_str,
                "count": 1
            }
        else:
            user_tracking[uid]["last_seen"] = now_str
            user_tracking[uid]["name"] = user.full_name
            user_tracking[uid]["username"] = f"@{user.username}" if user.username else "No username"
            user_tracking[uid]["count"] += 1
            user_tracking[uid]["chat_id"] = chat.id
    except Exception as e:
        print(f"Track error: {e}")

def fetch_yahoo_data(symbol, range_str, interval):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"range": range_str, "interval": interval, "includePrePost": "false"}
        r = session.get(url, params=params, timeout=15)
        data = r.json()
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        ohlc = result['indicators']['quote'][0]
        df = pd.DataFrame({
            'Open': ohlc['open'],
            'Close': ohlc['close'],
            'High': ohlc['high'],
            'Low': ohlc['low']
        }, index=pd.to_datetime(timestamps, unit='s'))
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"Fetch fail {symbol}: {e}")
        return pd.DataFrame()

application = Application.builder().token(BOT_TOKEN).build()

def get_fno_alerts(chat_id, save_log=True, debug=False):
    cfg = get_settings(chat_id)
    alerts = []
    debug_logs = []
    for sym in FNO:
        try:
            df_daily = fetch_yahoo_data(sym, "5d", "1d")
            df_intra = fetch_yahoo_data(sym, "2d", "5m")
            if df_daily.empty or df_intra.empty or len(df_daily) < 2:
                if debug: debug_logs.append(f"{sym}: Empty")
                continue
            prev_close = float(df_daily['Close'].iloc[-2])
            today_open = float(df_daily['Open'].iloc[-1])
            curr_price = float(df_intra['Close'].iloc[-1])
            near_pct = abs(today_open - prev_close) / prev_close * 100
            move_pct = (curr_price - today_open) / today_open * 100
            if debug:
                debug_logs.append(f"{sym.replace('.NS','')}: Near={near_pct:.2f}% Move={move_pct:.2f}%")
            if near_pct > cfg["near"]: continue
            if abs(move_pct) < cfg["move"]: continue
            is_up = move_pct > 0
            sl_price = today_open * (1 - cfg["sl"]/100) if is_up else today_open * (1 + cfg["sl"]/100)
            target_price = curr_price + (curr_price - sl_price) * cfg["target_ratio"] if is_up else curr_price - (sl_price - curr_price) * cfg["target_ratio"]
            symbol = sym.replace('.NS','')
            side = "🟢 LONG" if is_up else "🔴 SHORT"
            text = f"{side} **{symbol}**\nEntry: ₹{curr_price:.2f} ({move_pct:+.2f}%)\nPrev: {prev_close:.2f} | Open: {today_open:.2f}\nSL: ₹{sl_price:.2f} | TGT: ₹{target_price:.2f} (1:{cfg['target_ratio']})\nTime: {get_ist().strftime('%I:%M %p IST')}"
            alerts.append(text)
            if save_log:
                trade_log.setdefault(chat_id, []).append({"time": get_ist().strftime('%Y-%m-%d %H:%M'),"symbol": symbol,"side": "LONG" if is_up else "SHORT","entry": curr_price,"prev_close": prev_close,"open": today_open,"move%": round(move_pct,2),"sl": round(sl_price,2),"target": round(target_price,2),"rr": f"1:{cfg['target_ratio']}"})
        except Exception as e:
            if debug: debug_logs.append(f"{sym}: Err {e}")
            continue
    return alerts, debug_logs

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    await update.message.reply_text(f"🚀 **PDC Bot Fixed (Yahoo Direct)**\nIST: {get_ist().strftime('%I:%M %p')}\n/scan\n/debug\n/settings")

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    await update.message.reply_text(f"🔍 Scanning {len(FNO)} stocks... {get_ist().strftime('%I:%M %p IST')}")
    alerts, _ = get_fno_alerts(update.effective_chat.id)
    if not alerts:
        await update.message.reply_text(f"No breakout now. Time IST: {get_ist().strftime('%I:%M %p')}\nTry /debug")
    else:
        for a in alerts[:10]:
            await update.message.reply_text(a, parse_mode="Markdown")
            await asyncio.sleep(0.3)

async def debug_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    await update.message.reply_text("🔍 Debug scanning direct API se...")
    alerts, logs = get_fno_alerts(update.effective_chat.id, save_log=False, debug=True)
    msg = "\n".join(logs[:30])
    if not msg: msg = "All empty - Yahoo block still"
    await update.message.reply_text(f"Debug Data:\n{msg}\n\nAlerts: {len(alerts)}")
    if alerts:
        for a in alerts[:3]:
            await update.message.reply_text(a, parse_mode="Markdown")

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    cfg = get_settings(update.effective_chat.id)
    kb = [[InlineKeyboardButton(f"Near {cfg['near']}%", callback_data="noop"), InlineKeyboardButton(f"Move {cfg['move']}%", callback_data="noop")],[InlineKeyboardButton("Near 0.3%", callback_data="near_0.3"), InlineKeyboardButton("Near 0.6%", callback_data="near_0.6"), InlineKeyboardButton("Near 1%", callback_data="near_1.0"), InlineKeyboardButton("Near 2%", callback_data="near_2.0")],[InlineKeyboardButton("Move 0.5%", callback_data="move_0.5"), InlineKeyboardButton("Move 1%", callback_data="move_1.0"), InlineKeyboardButton("Move 2%", callback_data="move_2.0")],[InlineKeyboardButton(f"SL {cfg['sl']}%", callback_data="noop"), InlineKeyboardButton(f"TGT 1:{cfg['target_ratio']}", callback_data="noop")],[InlineKeyboardButton("SL 0.3%", callback_data="sl_0.3"), InlineKeyboardButton("SL 0.5%", callback_data="sl_0.5"), InlineKeyboardButton("SL 1%", callback_data="sl_1.0")],[InlineKeyboardButton("TGT 1:1", callback_data="tgt_1"), InlineKeyboardButton("TGT 1:2", callback_data="tgt_2"), InlineKeyboardButton("TGT 1:3", callback_data="tgt_3")],]
    await update.message.reply_text(f"⚙️ Settings Near={cfg['near']}% Move={cfg['move']}% SL={cfg['sl']}% TGT=1:{cfg['target_ratio']}", reply_markup=InlineKeyboardMarkup(kb))

async def button_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    q = update.callback_query
    await q.answer()
    cfg = get_settings(q.message.chat_id)
    d = q.data
    if d.startswith("near_"): cfg["near"] = float(d.split("_")[1])
    if d.startswith("move_"): cfg["move"] = float(d.split("_")[1])
    if d.startswith("sl_"): cfg["sl"] = float(d.split("_")[1])
    if d.startswith("tgt_"): cfg["target_ratio"] = int(d.split("_")[1])
    user_settings[q.message.chat_id] = cfg
    await q.edit_message_text(f"✅ Saved Near={cfg['near']}% Move={cfg['move']}% SL={cfg['sl']}% TGT=1:{cfg['target_ratio']}\n/scan karo", reply_markup=q.message.reply_markup)

async def export_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    logs = trade_log.get(update.effective_chat.id, [])
    if not logs: await update.message.reply_text("Koi log nahi"); return
    df = pd.DataFrame(logs)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    await update.message.reply_document(document=output, filename=f"Trades_{get_ist().strftime('%d-%b')}.xlsx")

auto_users = set()
async def auto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    auto_users.add(update.effective_chat.id)
    await update.message.reply_text("✅ Auto ON (9:15-15:30 IST)")

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    auto_users.discard(update.effective_chat.id)
    await update.message.reply_text("🔴 Auto OFF")

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    # Sirf aap dekh paoge agar ADMIN_ID set kiya
    if ADMIN_ID!= 0 and update.effective_user.id!= ADMIN_ID:
        await update.message.reply_text("⛔ Ye command sirf admin ke liye hai")
        return

    if not user_tracking:
        await update.message.reply_text("Abhi koi user nahi hai")
        return

    msg = f"👥 **Total Users: {len(user_tracking)}**\nTime: {get_ist().strftime('%d-%m-%Y %I:%M %p IST')}\n\n"
    for i, (uid, data) in enumerate(user_tracking.items(), 1):
        msg += f"{i}. **{data['name']}**\n {data['username']} | ID: `{data['user_id']}`\n Last: {data['last_seen']}\n Count: {data['count']} | Type: {data['chat_type']}\n\n"

    # Agar message bada ho to file me bhej do
    if len(msg) > 4000:
        df = pd.DataFrame(list(user_tracking.values()))
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        await update.message.reply_document(document=output, filename=f"Users_{get_ist().strftime('%d-%b-%Y')}.xlsx", caption=f"Total Users: {len(user_tracking)}")
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("scan", scan_cmd))
application.add_handler(CommandHandler("debug", debug_cmd))
application.add_handler(CommandHandler("fno", scan_cmd))
application.add_handler(CommandHandler("settings", settings_cmd))
application.add_handler(CommandHandler("export", export_cmd))
application.add_handler(CommandHandler("auto", auto_cmd))
application.add_handler(CommandHandler("stop", stop_cmd))
application.add_handler(CommandHandler("users", users_cmd))
application.add_handler(CallbackQueryHandler(button_cb))

@app.route('/')
def home(): return f"Bot Live Direct API {get_ist().strftime('%H:%M IST')} | Users: {len(user_tracking)}"
@app.route('/')
def home(): return f"Bot Live Direct API {get_ist().strftime('%H:%M IST')} | Users: {len(user_tracking)}"

@app.route('/users')
def users_page():
    if not user_tracking:
        return "No users yet"
    html = f"<h2>Total Users: {len(user_tracking)} - {get_ist().strftime('%d-%m-%Y %I:%M %p IST')}</h2><table border=1 cellpadding=5><tr><th>#</th><th>Name</th><th>Username</th><th>User ID</th><th>Chat Type</th><th>First Seen</th><th>Last Seen IST</th><th>Count</th></tr>"
    for i, (uid, d) in enumerate(user_tracking.items(), 1):
        html += f"<tr><td>{i}</td><td>{d['name']}</td><td>{d['username']}</td><td>{d['user_id']}</td><td>{d['chat_type']}</td><td>{d['first_seen']}</td><td>{d['last_seen']}</td><td>{d['count']}</td></tr>"
    html += "</table>"
    return html

async def auto_loop():
async def auto_loop():
    while True:
        await asyncio.sleep(300)
        now = get_ist()
        if not (9 <= now.hour <= 15): continue
        if now.hour == 9 and now.minute < 15: continue
        if now.weekday() >= 5: continue
        for uid in list(auto_users):
            alerts, _ = get_fno_alerts(uid)
            if alerts:
                for a in alerts[:5]:
                    try: await application.bot.send_message(chat_id=uid, text=a, parse_mode="Markdown")
                    except: pass

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop().create_task(auto_loop())
    application.run_polling(drop_pending_updates=True)
