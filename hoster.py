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
    return "Oracle Bot is Live!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
BOT_TOKEN = "8318488317:AAFyfOLjIAY-p8GaJXmPlhXCu82R3_XEqgU"

# Memory bachane ke liye sirf zaroori sources rakhein
SOURCES = [
    "https://raw.githubusercontent.com/binlist/data/master/ranges.csv",
    "https://raw.githubusercontent.com/venelinkochev/bin-list-data/master/bin-list-data.csv"
]

logging.basicConfig(level=logging.INFO)
df_master = pd.DataFrame()

def hunt_the_world():
    global df_master
    all_dfs = []
    print("🔱 ORACLE: Memory Optimized Loading...")
    for url in SOURCES:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                temp_df = pd.read_csv(io.BytesIO(resp.content), dtype=str).fillna("N/A")
                temp_df = temp_df.loc[:, ~temp_df.columns.duplicated()].copy()
                temp_df.columns = [c.lower().strip() for c in temp_df.columns]
                
                rename_map = {'iin': 'bin', 'bin_start': 'bin', 'number': 'bin', 'issuer': 'bank', 'bank_name': 'bank'}
                temp_df.rename(columns=rename_map, inplace=True)
                
                if 'bin' in temp_df.columns:
                    temp_df['bin'] = temp_df['bin'].str.slice(0, 6)
                    cols = [c for c in ['bin', 'bank', 'country', 'brand', 'type'] if c in temp_df.columns]
                    all_dfs.append(temp_df[cols].copy())
        except Exception as e:
            print(f"Error: {e}")
            continue
    if all_dfs:
        df_master = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=['bin'], keep='first')
        df_master.set_index('bin', inplace=True)
        print("🌟 DB Ready.")

# DB Build
hunt_the_world()

async def handle_bin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # PUBLIC ACCESS: Everyone can use
    raw_text = "".join(filter(str.isdigit, update.message.text))
    if len(raw_text) < 6: return
    bin_id = raw_text[:6]

    result = None
    if bin_id in df_master.index:
        row = df_master.loc[bin_id]
        if isinstance(row, pd.DataFrame): row = row.iloc[0]
        result = {'bank': row.get('bank', 'N/A'), 'status': "✅ DB MATCHED"}

    if result:
        text = f"👑 **ORACLE ANALYSIS: {bin_id}**\n🏦 **Bank:** `{result['bank']}`\n📡 **Status:** `{result['status']}`"
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ **BIN NOT FOUND**")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔱 **ORACLE ONLINE**\nSend 6-digit BIN.")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bin))
    app.run_polling()