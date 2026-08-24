import os, asyncio, yfinance as yf, pandas as pd
from datetime import datetime
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from io import BytesIO
from curl_cffi import requests as cffi_requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
app = Flask(__name__)

session = cffi_requests.Session(impersonate="chrome")

FNO = ["RELIANCE.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","AXISBANK.NS","KOTAKBANK.NS","TCS.NS","INFY.NS","LT.NS","ITC.NS","BHARTIARTL.NS","BAJFINANCE.NS","MARUTI.NS","M&M.NS","TATAMOTORS.NS","SUNPHARMA.NS","HCLTECH.NS","WIPRO.NS","ADANIENT.NS","ADANIPOWER.NS","ADANIPORTS.NS","TATAPOWER.NS","TATASTEEL.NS","JSWSTEEL.NS","ZOMATO.NS","JIOFIN.NS","HYUNDAI.NS"]

user_settings = {}
trade_log = {}

def get_settings(chat_id):
    return user_settings.get(chat_id, {"near": 0.6, "move": 1.0, "sl": 0.5, "target_ratio": 2})

application = Application.builder().token(BOT_TOKEN).build()

def get_fno_alerts(chat_id, save_log=True):
    cfg = get_settings(chat_id)
    alerts = []
    for sym in FNO:
        try:
            df_daily = yf.download(sym, period="5d", interval="1d", progress=False, auto_adjust=True, session=session)
            df_intra = yf.download(sym, period="1d", interval="5m", progress=False, auto_adjust=True, session=session)
            if df_daily.empty or df_intra.empty or len(df_daily) < 2 or len(df_intra) < 2: continue
            if isinstance(df_daily.columns, pd.MultiIndex): df_daily.columns = df_daily.columns.get_level_values(0)
            if isinstance(df_intra.columns, pd.MultiIndex): df_intra.columns = df_intra.columns.get_level_values(0)
            prev_close = float(df_daily['Close'].iloc[-2])
            today_open = float(df_daily['Open'].iloc[-1])
            curr_price = float(df_intra['Close'].iloc[-1])
            near_cond = abs(today_open - prev_close) / prev_close * 100 <= cfg["near"]
            if not near_cond: continue
            move_pct = (curr_price - today_open) / today_open * 100
            if abs(move_pct) < cfg["move"]: continue
            is_up = move_pct > 0
            sl_price = today_open * (1 - cfg["sl"]/100) if is_up else today_open * (1 + cfg["sl"]/100)
            target_price = curr_price + (curr_price - sl_price) * cfg["target_ratio"] if is_up else curr_price - (sl_price - curr_price) * cfg["target_ratio"]
            symbol = sym.replace('.NS','')
            side = "🟢 LONG" if is_up else "🔴 SHORT"
            text = f"{side} **{symbol}**\nEntry: ₹{curr_price:.2f} ({move_pct:+.2f}%)\nPrev: {prev_close:.2f} | Open: {today_open:.2f}\nSL: ₹{sl_price:.2f} | TGT: ₹{target_price:.2f} (1:{cfg['target_ratio']})\nTime: {datetime.now().strftime('%I:%M %p')}"
            alerts.append(text)
            if save_log:
                trade_log.setdefault(chat_id, []).append({"time": datetime.now().strftime('%Y-%m-%d %H:%M'),"symbol": symbol,"side": "LONG" if is_up else "SHORT","entry": curr_price,"prev_close": prev_close,"open": today_open,"move%": round(move_pct,2),"sl": round(sl_price,2),"target": round(target_price,2),"rr": f"1:{cfg['target_ratio']}"})
        except: continue
    return alerts

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **PDC + SL/TGT Bot**\n/scan\n/settings\n/auto\n/export\n/stop")
async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Scanning...")
    alerts = get_fno_alerts(update.effective_chat.id)
    if not alerts: await update.message.reply_text("No breakout now.")
    else:
        for a in alerts[:10]:
            await update.message.reply_text(a, parse_mode="Markdown")
            await asyncio.sleep(0.3)
async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_settings(update.effective_chat.id)
    kb = [[InlineKeyboardButton(f"Near {cfg['near']}%", callback_data="noop"), InlineKeyboardButton(f"Move {cfg['move']}%", callback_data="noop")],[InlineKeyboardButton("Near 0.3%", callback_data="near_0.3"), InlineKeyboardButton("Near 0.6%", callback_data="near_0.6"), InlineKeyboardButton("Near 1%", callback_data="near_1.0")],[InlineKeyboardButton("Move 0.5%", callback_data="move_0.5"), InlineKeyboardButton("Move 1%", callback_data="move_1.0"), InlineKeyboardButton("Move 2%", callback_data="move_2.0")],[InlineKeyboardButton(f"SL {cfg['sl']}%", callback_data="noop"), InlineKeyboardButton(f"TGT 1:{cfg['target_ratio']}", callback_data="noop")],[InlineKeyboardButton("SL 0.3%", callback_data="sl_0.3"), InlineKeyboardButton("SL 0.5%", callback_data="sl_0.5"), InlineKeyboardButton("SL 1%", callback_data="sl_1.0")],[InlineKeyboardButton("TGT 1:1", callback_data="tgt_1"), InlineKeyboardButton("TGT 1:2", callback_data="tgt_2"), InlineKeyboardButton("TGT 1:3", callback_data="tgt_3")],]
    await update.message.reply_text(f"⚙️ Settings Near={cfg['near']}% Move={cfg['move']}% SL={cfg['sl']}% TGT=1:{cfg['target_ratio']}", reply_markup=InlineKeyboardMarkup(kb))
async def button_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    logs = trade_log.get(update.effective_chat.id, [])
    if not logs: await update.message.reply_text("Aaj koi log nahi /scan karo"); return
    df = pd.DataFrame(logs)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    await update.message.reply_document(document=output, filename=f"Trades_{datetime.now().strftime('%d-%b')}.xlsx")
auto_users = set()
async def auto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_users.add(update.effective_chat.id)
    await update.message.reply_text("✅ Auto ON")
async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_users.discard(update.effective_chat.id)
    await update.message.reply_text("🔴 Auto OFF")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("scan", scan_cmd))
application.add_handler(CommandHandler("fno", scan_cmd))
application.add_handler(CommandHandler("settings", settings_cmd))
application.add_handler(CommandHandler("export", export_cmd))
application.add_handler(CommandHandler("auto", auto_cmd))
application.add_handler(CommandHandler("stop", stop_cmd))
application.add_handler(CallbackQueryHandler(button_cb))

@app.route('/')
def home(): return "Bot Live"

async def auto_loop():
    while True:
        await asyncio.sleep(300)
        now = datetime.now()
        if not (9 <= now.hour <= 12): continue
        for uid in list(auto_users):
            alerts = get_fno_alerts(uid)
            if alerts:
                for a in alerts[:5]:
                    try: await application.bot.send_message(chat_id=uid, text=a, parse_mode="Markdown")
                    except: pass

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    # CONFLICT FIX: Purana polling instance kill karo
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop().create_task(auto_loop())
    application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
