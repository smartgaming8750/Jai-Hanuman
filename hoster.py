import pandas as pd
import requests
import io
import logging
import asyncio
import threading
import os
from flask import Flask
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- KEEP ALIVE SERVER ---
app_flask = Flask(__name__)

@app_flask.route('/')
def health_check():
    return "Oracle Bot is Live!", 200

def run_flask():
    # Render's dynamic port handling
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host='0.0.0.0', port=port)

# --- CONFIGURATION ---
BOT_TOKEN = "8318488317:AAFyfOLjIAY-p8GaJXmPlhXCu82R3_XEqgU"
ADMIN_USER = "t.me/Katter_Hindu_00"

SOURCES = [
    "https://raw.githubusercontent.com/binlist/data/master/ranges.csv",
    "https://raw.githubusercontent.com/venelinkochev/bin-list-data/master/bin-list-data.csv",
    "https://raw.githubusercontent.com/BasixKOR/binlist-data/master/ranges.csv",
    "https://raw.githubusercontent.com/iannuttall/binlist-data/master/binlist-data.csv",
    "https://raw.githubusercontent.com/adrianosousa/check-bin/master/bins.csv",
    "https://raw.githubusercontent.com/moov-io/ach/master/test/testdata/fed-routing-directory.csv"
]

logging.basicConfig(level=logging.INFO)
df_master = pd.DataFrame()

def hunt_the_world():
    global df_master
    all_dfs = []
    print("🔱 ORACLE: Scouring global data lakes...")
    
    for url in SOURCES:
        try:
            resp = requests.get(url, timeout=12)
            if resp.status_code == 200:
                # FIX: Drop duplicate columns before processing
                temp_df = pd.read_csv(io.BytesIO(resp.content), dtype=str).fillna("N/A")
                temp_df = temp_df.loc[:, ~temp_df.columns.duplicated()].copy()
                
                temp_df.columns = [c.lower().strip() for c in temp_df.columns]
                
                rename_map = {
                    'iin': 'bin', 'bin_start': 'bin', 'number': 'bin', 'iin_start': 'bin',
                    'issuer': 'bank', 'bank_name': 'bank', 'bankname': 'bank',
                    'brand_name': 'brand', 'card_brand': 'brand', 'scheme': 'brand',
                    'type': 'type', 'card_type': 'type'
                }
                temp_df.rename(columns=rename_map, inplace=True)
                
                if 'bin' in temp_df.columns:
                    temp_df['bin'] = temp_df['bin'].str.slice(0, 6)
                    cols = [c for c in ['bin', 'bank', 'country', 'brand', 'type'] if c in temp_df.columns]
                    sub_df = temp_df[cols].copy()
                    # Secondary unique check to prevent InvalidIndexError
                    sub_df = sub_df.loc[:, ~sub_df.columns.duplicated()].copy()
                    all_dfs.append(sub_df)
        except Exception as e:
            print(f"⚠️ Source skip: {e}")
            continue

    if all_dfs:
        df_master = pd.concat(all_dfs, ignore_index=True)
        df_master = df_master.drop_duplicates(subset=['bin'], keep='first')
        df_master.set_index('bin', inplace=True)
        print(f"🌟 Master Database Built: {len(df_master)} Active Ranges.")

# Run database build
hunt_the_world()

async def handle_bin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Free for all - No Auth check
    raw_text = "".join(filter(str.isdigit, update.message.text))
    if len(raw_text) < 6: return
    bin_id = raw_text[:6]

    progress = await update.message.reply_text("⚡ *Checking...*", parse_mode="Markdown")
    
    # Check local DB
    result = None
    if bin_id in df_master.index:
        row = df_master.loc[bin_id]
        if isinstance(row, pd.DataFrame): row = row.iloc[0]
        result = {'bank': row.get('bank', 'N/A'), 'country': row.get('country', 'N/A'), 'brand': row.get('brand', 'N/A'), 'type': row.get('type', 'N/A'), 'status': "✅ DB MATCHED"}

    if result:
        text = (f"👑 **ORACLE ANALYSIS: {bin_id}**\n━━━━━━━━━━━━━━━━━━━━━\n📡 **Status:** `{result['status']}`\n🏦 **Bank:** `{str(result['bank']).upper()}`\n🌍 **Country:** `{str(result['country']).upper()}`\n💳 **Brand:** `{str(result['brand']).upper()}`\n🛠️ **Type:** `{str(result['type']).upper()}`\n━━━━━━━━━━━━━━━━━━━━━")
        await progress.edit_text(text, parse_mode="Markdown")
    else:
        await progress.edit_text("❌ **NOT FOUND**")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔱 **ORACLE v5 ONLINE**\nSend 6-digit BIN.", parse_mode="Markdown")

if __name__ == '__main__':
    # Start Keep-Alive Server
    threading.Thread(target=run_flask, daemon=True).start()
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bin))
    app.run_polling()
