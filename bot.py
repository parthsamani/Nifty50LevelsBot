import os, asyncio, pandas as pd
from datetime import datetime, timedelta, time
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from io import BytesIO
from curl_cffi import requests as cffi_requests
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHANNEL_LINK = "https://t.me/ParthTraderAlertsLive"

app = Flask(__name__)
session = cffi_requests.Session(impersonate="chrome110")

# FULL 188 FNO + NEW LIST
FNO = [
"HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","AXISBANK.NS","KOTAKBANK.NS","INDUSINDBK.NS","FEDERALBNK.NS",
"BANKBARODA.NS","BANKINDIA.NS","CANBK.NS","PNB.NS","UNIONBANK.NS","MAHABANK.NS","IDFCFIRSTB.NS",
"AUBANK.NS","BANDHANBNK.NS","RBLBANK.NS","INDIANB.NS","BAJFINANCE.NS","BAJAJFINSV.NS","CHOLAFIN.NS",
"MUTHOOTFIN.NS","MANAPPURAM.NS","M&MFIN.NS","LICHSGFIN.NS","POONAWALLA.NS","LTF.NS","ABCAPITAL.NS",
"MOTILALOFS.NS","JIOFIN.NS","SBICARD.NS","HDFCAMC.NS","NAM-INDIA.NS","ANGELONE.NS","BSE.NS","CDSL.NS",
"MCX.NS","CAMS.NS","KFINTECH.NS","SBILIFE.NS","HDFCLIFE.NS","ICICIPRULI.NS","LICI.NS","TCS.NS",
"INFY.NS","WIPRO.NS","HCLTECH.NS","LTIM.NS","TECHM.NS","MPHASIS.NS","PERSISTENT.NS","COFORGE.NS",
"LTTS.NS","MARUTI.NS","M&M.NS","TATAMOTORS.NS","EICHERMOT.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS",
"TVSMOTOR.NS","ASHOKLEY.NS","BHARATFORG.NS","MOTHERSON.NS","SONACOMS.NS","EXIDEIND.NS","ENDURANCE.NS",
"FORCEMOT.NS","APOLLOTYRE.NS","ITC.NS","HINDUNILVR.NS","TITAN.NS","TRENT.NS","DMART.NS","VBL.NS",
"DABUR.NS","MARICO.NS","TATACONSUM.NS","COLPAL.NS","BRITANNIA.NS","UNITDSPR.NS","GODREJCP.NS",
"ETERNAL.NS","BHARTIARTL.NS","IDEA.NS","INDUSTOWER.NS","PAYTM.NS","SUNPHARMA.NS","DIVISLAB.NS",
"CIPLA.NS","DRREDDY.NS","APOLLOHOSP.NS","ZYDUSLIFE.NS","LUPIN.NS","AUROPHARMA.NS","BIOCON.NS",
"GRANULES.NS","LAURUSLABS.NS","SYNGENE.NS","ABBOTINDIA.NS","ALKEM.NS","TATASTEEL.NS","JSWSTEEL.NS",
"HINDALCO.NS","JINDALSTEL.NS","VEDL.NS","HINDZINC.NS","HINDCOPPER.NS","NATIONALUM.NS","SAIL.NS",
"NMDC.NS","COALINDIA.NS","RELIANCE.NS","ONGC.NS","IOC.NS","BPCL.NS","HINDPETRO.NS","OIL.NS",
"GAIL.NS","PETRONET.NS","IGL.NS","GUJGASLTD.NS","TATAPOWER.NS","NTPC.NS","POWERGRID.NS",
"JSWENERGY.NS","ADANIGREEN.NS","ADANIPOWER.NS","ADANIENSOL.NS","SUZLON.NS","ADANIENT.NS",
"ADANIPORTS.NS","LT.NS","SIEMENS.NS","ABB.NS","CGPOWER.NS","BHEL.NS","POLYCAB.NS","HAVELLS.NS",
"CROMPTON.NS","VOLTAS.NS","DIXON.NS","THERMAX.NS","CUMMINSIND.NS","BEL.NS","HAL.NS","COCHINSHIP.NS",
"MAZDOCK.NS","RVNL.NS","IRFC.NS","IRCTC.NS","CONCOR.NS","NBCC.NS","NCC.NS","GMRINFRA.NS",
"ULTRACEMCO.NS","AMBUJACEM.NS","ACC.NS","DALBHARAT.NS","RAMCOCEM.NS","DLF.NS","GODREJPROP.NS",
"OBEROIRLTY.NS","LODHA.NS","TATACHEM.NS","UPL.NS","SRF.NS","DEEPAKNTR.NS","CHAMBLFERT.NS",
"COROMANDEL.NS","AARTIIND.NS","PIDILITIND.NS","ATUL.NS","INDIGO.NS","INDHOTEL.NS","POLICYBZR.NS",
"NYKAA.NS","SAGILITY.NS","ATHERENERG.NS","VMM.NS","KALYANKJIL.NS","IEX.NS","INDIAMART.NS",
"NAUKRI.NS","TATAELXSI.NS","TATACOMM.NS","JUBLFOOD.NS","ZEEL.NS","GODFRYPHLP.NS"
]

CHANNEL_FIXED_CFG = {"near": 0.6, "move": 0.8, "sl": 0.7, "target_ratio": 2}
CHANNEL_AUTO_ENABLED = True

user_settings = {}
trade_log = {}
user_tracking = {}
alerted_today = {}
last_alert_time = {}
alerted_today_channel = {}
last_alert_time_channel = {}
COOLDOWN_MIN = 45

def get_ist():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

def get_settings(chat_id):
    return user_settings.get(chat_id, {"near": 0.6, "move": 1.0, "sl": 0.5, "target_ratio": 2})

def track_user(update: Update):
    try:
        user = update.effective_user
        chat = update.effective_chat
        uid = user.id
        now_str = get_ist().strftime('%d-%m-%Y %I:%M:%S %p')
        if uid not in user_tracking:
            user_tracking[uid] = {"user_id": uid,"name": user.full_name,"username": f"@{user.username}" if user.username else "No username","chat_type": chat.type,"chat_id": chat.id,"first_seen": now_str,"last_seen": now_str,"count": 1}
        else:
            user_tracking[uid]["last_seen"] = now_str
            user_tracking[uid]["name"] = user.full_name
            user_tracking[uid]["username"] = f"@{user.username}" if user.username else "No username"
            user_tracking[uid]["count"] += 1
            user_tracking[uid]["chat_id"] = chat.id
    except: pass

def fetch_yahoo_data(symbol, range_str, interval):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"range": range_str, "interval": interval, "includePrePost": "false"}
        r = session.get(url, params=params, timeout=15)
        data = r.json()
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        ohlc = result['indicators']['quote'][0]
        df = pd.DataFrame({'Open': ohlc['open'],'Close': ohlc['close'],'High': ohlc['high'],'Low': ohlc['low'],'Volume': ohlc['volume']}, index=pd.to_datetime(timestamps, unit='s'))
        df.dropna(inplace=True)
        return df
    except: return pd.DataFrame()

application = Application.builder().token(BOT_TOKEN).build()

async def is_joined_channel(user_id):
    if not CHANNEL_ID: return True
    try:
        member = await application.bot.get_chat_member(chat_id=int(CHANNEL_ID), user_id=user_id)
        return member.status in ['member', 'administrator', 'creator', 'owner']
    except Exception as e:
        print(f"Join check fail: {e}")
        return True

def get_fno_alerts(chat_id=None, cfg_override=None, save_log=True, debug=False, is_channel=False):
    if cfg_override:
        cfg = cfg_override
    elif is_channel:
        cfg = CHANNEL_FIXED_CFG
    elif chat_id:
        cfg = get_settings(chat_id)
    else:
        cfg = CHANNEL_FIXED_CFG

    alerts = []
    debug_logs = []
    today_str = get_ist().strftime('%Y-%m-%d')

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
            avg_vol = float(df_daily['Volume'].iloc[-2]) if 'Volume' in df_daily else 0
            curr_vol = float(df_daily['Volume'].iloc[-1]) if 'Volume' in df_daily else 0
            has_low_volume = avg_vol > 0 and curr_vol < avg_vol * 0.8

            if debug: debug_logs.append(f"{sym.replace('.NS','')}: Near={near_pct:.2f}% Move={move_pct:.2f}% Vol={'Low' if has_low_volume else 'Ok'}")
            if near_pct > cfg["near"]: continue
            if abs(move_pct) < cfg["move"]: continue
            if has_low_volume: continue

            symbol = sym.replace('.NS','')
            if is_channel:
                if alerted_today_channel.get(symbol) == today_str: continue
                if symbol in last_alert_time_channel:
                    diff = (get_ist() - last_alert_time_channel[symbol]).seconds / 60
                    if diff < COOLDOWN_MIN: continue
            else:
                if chat_id:
                    if chat_id not in alerted_today: alerted_today[chat_id] = {}
                    if chat_id not in last_alert_time: last_alert_time[chat_id] = {}
                    if alerted_today[chat_id].get(symbol) == today_str: continue
                    if symbol in last_alert_time[chat_id]:
                        diff = (get_ist() - last_alert_time[chat_id][symbol]).seconds / 60
                        if diff < COOLDOWN_MIN: continue

            is_up = move_pct > 0
            sl_price = today_open * (1 - cfg["sl"]/100) if is_up else today_open * (1 + cfg["sl"]/100)
            target_price = curr_price + (curr_price - sl_price) * cfg["target_ratio"] if is_up else curr_price - (sl_price - curr_price) * cfg["target_ratio"]
            side = "🟢 LONG" if is_up else "🔴 SHORT"
            text = f"{side} **{symbol}**\nEntry: ₹{curr_price:.2f} ({move_pct:+.2f}%)\nPrev: {prev_close:.2f} | Open: {today_open:.2f}\nSL: ₹{sl_price:.2f} | TGT: ₹{target_price:.2f} (1:{cfg['target_ratio']})\nTime: {get_ist().strftime('%I:%M %p IST')}"
            alerts.append(text)

            if is_channel:
                alerted_today_channel[symbol] = today_str
                last_alert_time_channel[symbol] = get_ist()
            elif chat_id:
                alerted_today[chat_id][symbol] = today_str
                last_alert_time[chat_id][symbol] = get_ist()
                trade_log.setdefault(chat_id, []).append({"time": get_ist().strftime('%Y-%m-%d %H:%M'),"symbol": symbol,"side": "LONG" if is_up else "SHORT","entry": curr_price,"prev_close": prev_close,"open": today_open,"move%": round(move_pct,2),"sl": round(sl_price,2),"target": round(target_price,2),"rr": f"1:{cfg['target_ratio']}"})
        except: continue
    return alerts, debug_logs

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    if not await is_joined_channel(update.effective_user.id):
        await update.message.reply_text(f"⛔ **Channel Join Karo**\nBot use karne ke liye join karna zaruri hai\n👉 {CHANNEL_LINK}", parse_mode="Markdown")
        return
    await update.message.reply_text(f"🚀 **PDC Bot - Channel Fixed**\nIST: {get_ist().strftime('%I:%M %p')}\n\n**Channel Fixed:** Near {CHANNEL_FIXED_CFG['near']}% Move {CHANNEL_FIXED_CFG['move']}% SL {CHANNEL_FIXED_CFG['sl']}% TGT 1:{CHANNEL_FIXED_CFG['target_ratio']}\nChannel Auto: {'ON' if CHANNEL_AUTO_ENABLED else 'OFF'}\n\nUser: /scan /debug /settings /auto /stop\nAdmin: /channelon /channeloff /setchannel 0.6 0.8 0.7 2 /users\n\nTotal Stocks: {len(FNO)} (188)")

async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    if not await is_joined_channel(update.effective_user.id):
        await update.message.reply_text(f"⛔ **Channel Join Karo**\n👉 {CHANNEL_LINK}", parse_mode="Markdown")
        return
    await update.message.reply_text(f"🔍 Private Scanning {len(FNO)} stocks... {get_ist().strftime('%I:%M %p IST')}")
    alerts, _ = get_fno_alerts(chat_id=update.effective_chat.id, is_channel=False)
    if not alerts:
        await update.message.reply_text(f"No breakout now. Time IST: {get_ist().strftime('%I:%M %p')}\nTry /debug")
    else:
        for a in alerts[:10]:
            await update.message.reply_text(a, parse_mode="Markdown")
            await asyncio.sleep(0.3)

async def debug_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    if not await is_joined_channel(update.effective_user.id):
        await update.message.reply_text(f"⛔ **Channel Join Karo**\n👉 {CHANNEL_LINK}"); return
    await update.message.reply_text("🔍 Debug scanning...")
    alerts, logs = get_fno_alerts(chat_id=update.effective_chat.id, save_log=False, debug=True, is_channel=False)
    msg = "\n".join(logs[:30])
    if not msg: msg = "All empty - Yahoo block still"
    await update.message.reply_text(f"Debug Data:\n{msg}\n\nAlerts: {len(alerts)}")
    if alerts:
        for a in alerts[:3]: await update.message.reply_text(a, parse_mode="Markdown")

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    if not await is_joined_channel(update.effective_user.id):
        await update.message.reply_text(f"⛔ **Channel Join Karo**\n👉 {CHANNEL_LINK}"); return
    cfg = get_settings(update.effective_chat.id)
    kb = [[InlineKeyboardButton(f"Near {cfg['near']}%", callback_data="noop"), InlineKeyboardButton(f"Move {cfg['move']}%", callback_data="noop")],[InlineKeyboardButton("Near 0.3%", callback_data="near_0.3"), InlineKeyboardButton("Near 0.6%", callback_data="near_0.6"), InlineKeyboardButton("Near 1%", callback_data="near_1.0"), InlineKeyboardButton("Near 2%", callback_data="near_2.0")],[InlineKeyboardButton("Move 0.5%", callback_data="move_0.5"), InlineKeyboardButton("Move 1%", callback_data="move_1.0"), InlineKeyboardButton("Move 2%", callback_data="move_2.0")],[InlineKeyboardButton(f"SL {cfg['sl']}%", callback_data="noop"), InlineKeyboardButton(f"TGT 1:{cfg['target_ratio']}", callback_data="noop")],[InlineKeyboardButton("SL 0.3%", callback_data="sl_0.3"), InlineKeyboardButton("SL 0.5%", callback_data="sl_0.5"), InlineKeyboardButton("SL 1%", callback_data="sl_1.0")],[InlineKeyboardButton("TGT 1:1", callback_data="tgt_1"), InlineKeyboardButton("TGT 1:2", callback_data="tgt_2"), InlineKeyboardButton("TGT 1:3", callback_data="tgt_3")],]
    await update.message.reply_text(f"⚙️ **Your Private** Near={cfg['near']}% Move={cfg['move']}% SL={cfg['sl']}% TGT=1:{cfg['target_ratio']}\n**Channel Fixed:** {CHANNEL_FIXED_CFG}", reply_markup=InlineKeyboardMarkup(kb))

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
    if not await is_joined_channel(update.effective_user.id):
        await update.message.reply_text(f"⛔ **Channel Join Karo**\n👉 {CHANNEL_LINK}"); return
    auto_users.add(update.effective_chat.id)
    await update.message.reply_text(f"✅ Auto ON\nChannel: {CHANNEL_FIXED_CFG} Auto:{'ON' if CHANNEL_AUTO_ENABLED else 'OFF'}\nScanning {len(FNO)} stocks")

async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    auto_users.discard(update.effective_chat.id)
    await update.message.reply_text("🔴 Auto OFF")

async def channel_on_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_AUTO_ENABLED
    track_user(update)
    if ADMIN_ID!= 0 and update.effective_user.id!= ADMIN_ID:
        await update.message.reply_text("⛔ Admin only"); return
    CHANNEL_AUTO_ENABLED = True
    await update.message.reply_text(f"✅ Channel Auto ON\nFixed: {CHANNEL_FIXED_CFG} Stocks:{len(FNO)}")

async def channel_off_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_AUTO_ENABLED
    track_user(update)
    if ADMIN_ID!= 0 and update.effective_user.id!= ADMIN_ID:
        await update.message.reply_text("⛔ Admin only"); return
    CHANNEL_AUTO_ENABLED = False
    await update.message.reply_text("🔴 Channel Auto OFF")

async def set_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_FIXED_CFG
    track_user(update)
    if ADMIN_ID!= 0 and update.effective_user.id!= ADMIN_ID:
        await update.message.reply_text("⛔ Admin only"); return
    try:
        args = context.args
        if len(args) < 4:
            await update.message.reply_text(f"Usage: /setchannel near move sl target\nEx: /setchannel 0.6 0.8 0.7 2\nCurrent: {CHANNEL_FIXED_CFG}")
            return
        CHANNEL_FIXED_CFG = {"near": float(args[0]), "move": float(args[1]), "sl": float(args[2]), "target_ratio": int(args[3])}
        await update.message.reply_text(f"✅ Channel Updated\nNew: {CHANNEL_FIXED_CFG}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}\nUsage: /setchannel 0.6 0.8 0.7 2")

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update)
    if ADMIN_ID!= 0 and update.effective_user.id!= ADMIN_ID:
        await update.message.reply_text("⛔ Admin only"); return
    if not user_tracking: await update.message.reply_text("No users"); return
    msg = f"👥 Total: {len(user_tracking)} AutoON:{len(auto_users)} ChannelAuto:{CHANNEL_AUTO_ENABLED} {CHANNEL_FIXED_CFG} Stocks:{len(FNO)}\n"
    for i, (uid, data) in enumerate(list(user_tracking.items())[-20:], 1):
        msg += f"{i}. {data['name']} {data['username']} {data['last_seen']}\n"
    await update.message.reply_text(msg)

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("scan", scan_cmd))
application.add_handler(CommandHandler("debug", debug_cmd))
application.add_handler(CommandHandler("fno", scan_cmd))
application.add_handler(CommandHandler("settings", settings_cmd))
application.add_handler(CommandHandler("export", export_cmd))
application.add_handler(CommandHandler("auto", auto_cmd))
application.add_handler(CommandHandler("stop", stop_cmd))
application.add_handler(CommandHandler("users", users_cmd))
application.add_handler(CommandHandler("channelon", channel_on_cmd))
application.add_handler(CommandHandler("channeloff", channel_off_cmd))
application.add_handler(CommandHandler("setchannel", set_channel_cmd))
application.add_handler(CallbackQueryHandler(button_cb))

@app.route('/')
def home(): return f"Bot Live {CHANNEL_FIXED_CFG} Auto:{CHANNEL_AUTO_ENABLED} Users:{len(user_tracking)} Stocks:{len(FNO)} {get_ist().strftime('%H:%M IST')}"

@app.route('/users')
def users_page():
    if not user_tracking: return "No users yet"
    html = f"<h2>Total: {len(user_tracking)} Channel {CHANNEL_FIXED_CFG} Auto {CHANNEL_AUTO_ENABLED} Stocks {len(FNO)}</h2><table border=1><tr><th>#</th><th>Name</th><th>User</th><th>ID</th><th>Last Seen</th></tr>"
    for i, (uid, d) in enumerate(user_tracking.items(), 1):
        html += f"<tr><td>{i}</td><td>{d['name']}</td><td>{d['username']}</td><td>{d['user_id']}</td><td>{d['last_seen']}</td></tr>"
    html += "</table>"; return html

async def auto_loop():
    while True:
        await asyncio.sleep(300)
        now = get_ist()
        if not (9 <= now.hour <= 15): continue
        if now.hour == 9 and now.minute < 15: continue
        if now.weekday() >= 5: continue
        if not CHANNEL_AUTO_ENABLED: continue
        channel_alerts, _ = get_fno_alerts(is_channel=True, save_log=False)
        if channel_alerts and CHANNEL_ID:
            for a in channel_alerts[:5]:
                try: await application.bot.send_message(chat_id=int(CHANNEL_ID), text=a, parse_mode="Markdown")
                except: pass
        for uid in list(auto_users):
            alerts, _ = get_fno_alerts(chat_id=uid, is_channel=False)
            if alerts:
                for a in alerts[:5]:
                    try: await application.bot.send_message(chat_id=uid, text=a, parse_mode="Markdown")
                    except: pass

@app.route('/reset')
def reset_locks():
    alerted_today.clear(); last_alert_time.clear(); alerted_today_channel.clear(); last_alert_time_channel.clear(); return "Reset done"

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    asyncio.set_event_loop(asyncio.new_event_loop())
    asyncio.get_event_loop().create_task(auto_loop())
    application.run_polling(drop_pending_updates=True)
