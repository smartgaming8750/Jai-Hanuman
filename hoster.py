import pandas as pd
import requests
import io
import logging
import threading
import os
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- KEEP ALIVE SERVER ---
app_flask = Flask(__name__)

@app_flask.route('/')
def health_check():
    return "Oracle Bot is Online!", 200

def run_flask():
    # Render's dynamic port
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
BOT_TOKEN = "8318488317:AAFyfOLjIAY-p8GaJXmPlhXCu82R3_XEqgU"

# Memory Optimized: Sirf 1 main source load karenge RAM bachane ke liye
SOURCE_URL = "https://raw.githubusercontent.com/binlist/data/master/ranges.csv"

logging.basicConfig(level=logging.INFO)
df_master = pd.DataFrame()

def hunt_the_world():
    global df_master
    print("🔱 ORACLE: Loading optimized database...")
    try:
        resp = requests.get(SOURCE_URL, timeout=15)
        if resp.status_code == 200:
            df = pd.read_csv(io.BytesIO(resp.content), dtype=str).fillna("N/A")
            df = df.loc[:, ~df.columns.duplicated()].copy()
            df.columns = [c.lower().strip() for c in df.columns]
            
            rename_map = {'iin': 'bin', 'issuer': 'bank', 'bank_name': 'bank'}
            df.rename(columns=rename_map, inplace=True)
            
            if 'bin' in df.columns:
                df['bin'] = df['bin'].str.slice(0, 6)
                df_master = df[['bin', 'bank']].drop_duplicates(subset=['bin']).set_index('bin')
                print(f"🌟 DB Loaded: {len(df_master)} ranges.")
    except Exception as e:
        print(f"⚠️ Initial Load Error: {e}")

# Build DB
hunt_the_world()

async def live_query_api(bin_id):
    # Live API check for better accuracy without using RAM
    url = f"https://data.handyapi.com/bin/{bin_id}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'bank': data.get('bank', {}).get('name', 'N/A'),
                'country': data.get('country', {}).get('name', 'N/A'),
                'brand': data.get('scheme', 'N/A'),
                'status': "💎 LIVE VERIFIED"
            }
    except: return None

async def handle_bin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = "".join(filter(str.isdigit, update.message.text))
    if len(raw_text) < 6: return
    bin_id = raw_text[:6]

    progress = await update.message.reply_text("⚡ *Processing...*", parse_mode="Markdown")
    
    # Check Local DB first
    result = None
    if bin_id in df_master.index:
        result = {'bank': df_master.loc[bin_id]['bank'], 'status': "✅ DB MATCHED", 'country': 'N/A', 'brand': 'N/A'}
    
    # Try Live API for better details
    live = await live_query_api(bin_id)
    if live: result = live

    if result:
        text = (f"👑 **ORACLE ANALYSIS: {bin_id}**\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📡 **Status:** `{result['status']}`\n"
                f"🏦 **Bank:** `{str(result['bank']).upper()}`\n"
                f"🌍 **Country:** `{str(result.get('country', 'N/A')).upper()}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━")
        await progress.edit_text(text, parse_mode="Markdown")
    else:
        await progress.edit_text("❌ **NOT FOUND**")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔱 **ORACLE PUBLIC v5**\nSend a BIN to check.")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bin))
    app.run_polling()
