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
    now_time = datetime.now().strftime("%d %b %H:%M")
    
    for url in SOURCES:
        try:
            resp = requests.get(url, timeout=12)
            if resp.status_code == 200:
                # FIX: Standardize column names and drop duplicates within a single source
                temp_df = pd.read_csv(io.BytesIO(resp.content), dtype=str).fillna("N/A")
                
                # Force unique columns if the CSV has duplicate headers
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
                    
                    # Ensure sub_df itself doesn't have duplicate 'bin' columns after renaming
                    sub_df = sub_df.loc[:, ~sub_df.columns.duplicated()].copy()
                    
                    sub_df['source'] = url.split('/')[3]
                    sub_df['found_at'] = now_time
                    all_dfs.append(sub_df)
        except Exception as e:
            print(f"⚠️ Source Error ({url}): {e}")
            continue

    if all_dfs:
        # Concatenate all valid dataframes
        df_master = pd.concat(all_dfs, ignore_index=True)
        # Final cleanup: Remove duplicate BIN entries across all sources
        df_master = df_master.drop_duplicates(subset=['bin'], keep='first')
        df_master.set_index('bin', inplace=True)
        print(f"🌟 Master Database Built: {len(df_master)} Active Ranges.")

hunt_the_world()

async def live_query_api(bin_id):
    endpoints = [f"https://data.handyapi.com/bin/{bin_id}", f"https://lookup.binlist.net/{bin_id}"]
    for url in endpoints:
        try:
            headers = {'Accept-Version': '3', 'User-Agent': 'OracleBot/4.0'}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'bank': (data.get('bank', {}).get('name') or data.get('Issuer') or "N/A"),
                    'country': (data.get('country', {}).get('name') or data.get('Country', {}).get('Name') or "N/A"),
                    'brand': (data.get('scheme') or data.get('Scheme') or "N/A"),
                    'type': (data.get('type') or data.get('Type') or "N/A"),
                    'status': "💎 LIVE / VERIFIED"
                }
        except: continue
    return None

async def handle_bin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # PUBLIC ACCESS: No authorization check
    raw_text = "".join(filter(str.isdigit, update.message.text))
    if len(raw_text) < 6: return
    bin_id = raw_text[:6]

    progress = await update.message.reply_text("⚡ *Accessing Global Tunnels...*", parse_mode="Markdown")
    result = None
    
    if bin_id in df_master.index:
        row = df_master.loc[bin_id]
        if isinstance(row, pd.DataFrame): row = row.iloc[0]
        result = {'bank': row.get('bank', 'N/A'), 'country': row.get('country', 'N/A'), 'brand': row.get('brand', 'N/A'), 'type': row.get('type', 'N/A'), 'status': "✅ DB MATCHED"}

    live_data = await live_query_api(bin_id)
    if live_data: result = live_data

    if result:
        text = (f"👑 **ORACLE ANALYSIS: {bin_id}**\n━━━━━━━━━━━━━━━━━━━━━\n📡 **Status:** `{result['status']}`\n🏦 **Bank:** `{str(result['bank']).upper()}`\n🌍 **Country:** `{str(result['country']).upper()}`\n💳 **Brand:** `{str(result['brand']).upper()}`\n🛠️ **Type:** `{str(result['type']).upper()}`\n━━━━━━━━━━━━━━━━━━━━━")
        await progress.edit_text(text, parse_mode="Markdown")
    else:
        await progress.edit_text("❌ **NOT FOUND**")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔱 **ORACLE v5: PUBLIC MODE ACTIVE** 🔱\n\nSend a 6-digit BIN to begin.", parse_mode="Markdown")

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bin))
    print("🤖 Oracle v1 Live.")
    app.run_polling()
