from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask, request
import google.generativeai as genai
import zipfile
import os
import asyncio
import threading

# Conversation states
TOKEN, API_KEY, FEATURE = range(3)

# Flask app
app_flask = Flask(__name__)

# Telegram Bot Token - Railway এর Environment Variable থেকে নিবে
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Bot Application
application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 AI Bot Maker চালু\n\n"
        "Step 1/3: তোমার Telegram Bot Token পাঠাও\n"
        "@BotFather থেকে কপি করে দাও"
    )
    return TOKEN

async def get_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['token'] = update.message.text.strip()
    await update.message.reply_text(
        "Step 2/3: Gemini API Key দাও\n"
        "ফ্রি নিবা: https://aistudio.google.com/app/apikey"
    )
    return API_KEY

async def get_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['api_key'] = update.message.text.strip()
    await update.message.reply_text(
        "Step 3/3: তোমার Bot কি করবে লিখে বলো\n"
        "উদাহরণ: ধানের দাম হিসাব করবে, জোকস বলবে"
    )
    return FEATURE

async def generate_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_req = update.message.text
    token = context.user_data['token']
    api_key = context.user_data['api_key']
    user_id = update.effective_user.id
    
    msg = await update.message.reply_text("⏳ AI দিয়া bot বানাচ্ছি... 15 সেকেন্ড")
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        code_prompt = f"""
        Telegram bot বানাও এই কাজের জন্য: {user_req}
        লাইব্রেরি: python-telegram-bot v20+
        TOKEN = "{token}"
        /start, /help কমান্ড মাস্ট
        Error handling try-except দিয়া
        কোডের কমেন্ট বাংলায়
        শেষে কমেন্টে রান করার নিয়ম লিখো
        শুধু কোড দাও
        """
        
        response = model.generate_content(code_prompt)
        bot_code = response.text.replace("```python", "").replace("```", "").strip()
        
        readme = f"""XIFAT AI Bot Maker দিয়া বানানো Bot
ফিচার: {user_req}

কিভাবে চালাবা:
1. pip install python-telegram-bot
2. python bot.py
3. Telegram এ bot সার্চ করে /start

নোট: Token অলরেডি সেট করা।
"""
        
        zip_name = f"bot_{user_id}.zip"
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            zipf.writestr('bot.py', bot_code)
            zipf.writestr('README.txt', readme)
        
        await msg.delete()
        await update.message.reply_document(
            document=InputFile(zip_name),
            caption="✅ Bot রেডি! Unzip করে README পড়ো। /start দিয়ে আরেকটা বানাও"
        )
        os.remove(zip_name)
        context.user_data.clear()
        
    except Exception as e:
        await msg.edit_text(f"❌ এরর: {str(e)}\n/start দাও আবার")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("বাতিল। /start দিয়ে শুরু করো")
    return ConversationHandler.END

# Handler add
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_token)],
        API_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api)],
        FEATURE: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_zip)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
application.add_handler(conv_handler)

# Webhook route
@app_flask.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "ok"

@app_flask.route("/")
def index():
    return "AI Bot Maker is Running on Railway!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app_flask.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Bot webhook set
    import requests
    RAILWAY_URL = os.getenv("RAILWAY_STATIC_URL")
    if RAILWAY_URL:
        webhook_url = f"https://{RAILWAY_URL}/{TELEGRAM_TOKEN}"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook?url={webhook_url}")
        print(f"Webhook set: {webhook_url}")
    
    # Flask চালাও
    run_flask()
