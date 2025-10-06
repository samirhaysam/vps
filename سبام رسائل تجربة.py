import asyncio
import requests
import random
import string
import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# إعداد تسجيل الأحداث
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# متغيرات البيئة
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8441832522:AAF7JRh0aw1X2diiCFdg8Fx9cGU2L-1NXuY")
URL1 = "https://api.twistmena.com/music/Dlogin/sendCode"
URL2 = "https://mab.etisalat.com.eg:11003/Saytar/rest/quickAccess/sendVerCodeQuickAccessV4"

# قائمة User-Agent و Referer و Origin عشوائية
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
]

referers = ["https://www.google.com", "https://www.bing.com"]
origin_urls = ["https://www.example.com", "https://www.someotherdomain.com"]

# رؤوس API الثاني
HEADERS_API2 = {
    'Host': "mab.etisalat.com.eg:11003",
    'User-Agent': "okhttp/5.0.0-alpha.11",
    'Connection': "Keep-Alive",
    'Accept': "text/xml",
    'Content-Type': "text/xml; charset=UTF-8",
}

# دالة لتوليد الهيدر العشوائي لـ API الأول
def get_headers():
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": random.choice(referers),
        "Origin": random.choice(origin_urls),
    }

# دالة لتوليد رقم عشوائي
def random_string(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# بيانات المستخدمين
numbers_data = {}  # {user_id: {number: {"count": 5, "delay": 1.0}}}
sending_tasks = {}  # {user_id: asyncio.Task}
stop_flags = {}  # {user_id: bool}

# قائمة الأزرار الرئيسية
main_keyboard = [
    ["➕ إضافة رقم", "📋 عرض الأرقام"],
    ["📤 إرسال الرسائل"]
]

# ======== /start =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🌟 أهلاً بك في بوت إرسال الرسائل! 🌟\n\n"
        "يمكنك استخدام الأزرار التالية:\n"
        "➕ إضافة رقم: لإضافة رقم جديد\n"
        "📋 عرض الأرقام: لعرض الأرقام المسجلة\n"
        "📤 إرسال الرسائل: لإرسال الرسائل للأرقام المسجلة",
        reply_markup=reply_markup,
    )

# ======== إضافة رقم =========
ASK_NUMBER, ASK_COUNT, ASK_DELAY = range(3)

async def add_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📱 الرجاء إدخال رقم الهاتف (مثال: 01123456789):")
    return ASK_NUMBER

async def get_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = update.message.text.strip()

    if not (number.isdigit() and len(number) == 11 and number.startswith("01")):
        await update.message.reply_text(
            "❌ الرقم غير صالح! الرجاء إدخال رقم هاتف صحيح مكون من 11 رقم ويبدأ بـ 01:"
        )
        return ASK_NUMBER

    context.user_data["number"] = number
    await update.message.reply_text("📧 الرجاء إدخال عدد الرسائل المراد إرسالها:")
    return ASK_COUNT

async def get_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text)
        if count <= 0:
            await update.message.reply_text("❌ عدد الرسائل يجب أن يكون أكبر من صفر!")
            return ASK_COUNT
        context.user_data["count"] = count
        await update.message.reply_text("⏱️ الرجاء إدخال الوقت بالثواني بين كل رسالة:")
        return ASK_DELAY
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح لعدد الرسائل!")
        return ASK_COUNT

async def get_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        delay = float(update.message.text)
        if delay <= 0:
            await update.message.reply_text("❌ الوقت يجب أن يكون أكبر من صفر!")
            return ASK_DELAY

        user_id = update.message.from_user.id
        number = context.user_data["number"]
        count = context.user_data["count"]

        if user_id not in numbers_data:
            numbers_data[user_id] = {}
        numbers_data[user_id][number] = {"count": count, "delay": delay}

        keyboard = [[InlineKeyboardButton(f"🚀 إرسال إلى {number}", callback_data=f"send_{number}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ تم تسجيل {count} رسالة للرقم {number} بفاصل {delay} ثانية بين كل رسالة.",
            reply_markup=reply_markup,
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح للوقت بالثواني!")
        return ASK_DELAY

# ======== عرض الأرقام =========
async def show_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in numbers_data or not numbers_data[user_id]:
        await update.message.reply_text("❌ لا يوجد أرقام مسجلة لديك.")
        return
    msg = "📋 الأرقام المسجلة:\n\n"
    for num, data in numbers_data[user_id].items():
        msg += f"📞 {num} : {data['count']} رسالة | كل {data['delay']} ثانية\n"
    await update.message.reply_text(msg)

# ======== إرسال الرسائل باستخدام API =========
def send_sms(number, use_api_1=True):
    if use_api_1:
        # استخدام API الأول
        payload = {"dial": "2" + number, "randomValue": random_string()}
        headers = get_headers()
        try:
            response = requests.post(URL1, json=payload, headers=headers)
            return response.status_code, response.text, use_api_1
        except Exception as e:
            return None, str(e), use_api_1
    else:
        # استخدام API الثاني
        payload = f"""<?xml version='1.0' encoding='UTF-8' standalone='no' ?>
        <sendVerCodeQuickAccessRequest>
            <dial>{number}</dial>
            <hCaptchaToken></hCaptchaToken>
            <udid></udid>
        </sendVerCodeQuickAccessRequest>"""
        try:
            response = requests.post(URL2, data=payload, headers=HEADERS_API2)
            return response.status_code, response.text, use_api_1
        except Exception as e:
            return None, str(e), use_api_1

# ======== دالة إرسال الرسائل =========
async def send_task_function(bot, chat_id, user_id, numbers_list):
    stop_flags[user_id] = False
    for number in numbers_list:
        if stop_flags.get(user_id):
            await bot.send_message(chat_id=chat_id, text="🛑 تم إيقاف عملية الإرسال!")
            break
        info = numbers_data[user_id][number]
        count = info["count"]
        delay = info["delay"]

        # تحديد API الناجح
        use_api_1 = True
        for i in range(count):
            if stop_flags.get(user_id):
                break

            status, response_text, api_used = send_sms(number, use_api_1)

            if status == 200 or "true" in response_text.lower():
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ تم إرسال الرسالة {i+1} إلى {number} باستخدام {'API الأول' if api_used else 'API الثاني'}"
                )
            else:
                if use_api_1:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ فشل إرسال الرسالة {i+1} إلى {number} باستخدام API الأول، سيتم استخدام API الثاني..."
                    )
                    use_api_1 = False
                    # إعادة إرسال الرسالة باستخدام API الثاني
                    status, response_text, api_used = send_sms(number, use_api_1)
                    if status == 200 or "true" in response_text.lower():
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"✅ تم إرسال الرسالة {i+1} إلى {number} باستخدام API الثاني"
                        )
                    else:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"❌ فشل إرسال الرسالة {i+1} إلى {number} باستخدام API الثاني - الحالة: {status}, الاستجابة: {response_text}"
                        )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ فشل إرسال الرسالة {i+1} إلى {number} باستخدام API الثاني - الحالة: {status}, الاستجابة: {response_text}"
                    )

            await asyncio.sleep(delay)
    await bot.send_message(chat_id=chat_id, text="🎉 تم الانتهاء من عملية الإرسال!")

# ======== /send =========
async def send_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in numbers_data or not numbers_data[user_id]:
        await update.message.reply_text("❌ لا يوجد أرقام لإرسال الرسائل لها.")
        return

    keyboard = []
    for num in numbers_data[user_id].keys():
        keyboard.append([InlineKeyboardButton(num, callback_data=f"select_{num}")])

    keyboard.append([InlineKeyboardButton("🚀 إرسال", callback_data="send")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📌 الرجاء اختيار الأرقام لإرسال الرسائل لها:", reply_markup=reply_markup)

# ======== معالج الأزرار =========
async def send_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if "selected_numbers" not in context.user_data:
        context.user_data["selected_numbers"] = []

    if data.startswith("select_"):
        number = data.replace("select_", "")
        selected_numbers = context.user_data["selected_numbers"]

        if number in selected_numbers:
            selected_numbers.remove(number)
        else:
            selected_numbers.append(number)

        keyboard = []
        for num in numbers_data[user_id].keys():
            if num in selected_numbers:
                keyboard.append([InlineKeyboardButton(f"✅ {num}", callback_data=f"select_{num}")])
            else:
                keyboard.append([InlineKeyboardButton(num, callback_data=f"select_{num}")])

        keyboard.append([InlineKeyboardButton("🚀 إرسال", callback_data="send")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📌 الرجاء اختيار الأرقام لإرسال الرسائل لها:", reply_markup=reply_markup)

    elif data.startswith("send_"):
        number = data.replace("send_", "")
        task = asyncio.create_task(
            send_task_function(context.bot, query.message.chat.id, user_id, [number])
        )
        sending_tasks[user_id] = task
        keyboard = [[InlineKeyboardButton("🛑 إيقاف العملية", callback_data="stop")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"🚀 جاري إرسال الرسائل للرقم: {number}", reply_markup=reply_markup)

    elif data == "send":
        selected_numbers = context.user_data["selected_numbers"]
        if not selected_numbers:
            await query.edit_message_text("❌ الرجاء اختيار رقم واحد على الأقل.")
            return

        task = asyncio.create_task(
            send_task_function(context.bot, query.message.chat.id, user_id, selected_numbers)
        )
        sending_tasks[user_id] = task
        keyboard = [[InlineKeyboardButton("🛑 إيقاف العملية", callback_data="stop")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"🚀 جاري إرسال الرسائل للأرقام: {', '.join(selected_numbers)}",
            reply_markup=reply_markup,
        )

    elif data == "stop":
        await stop_automation(user_id)
        await query.edit_message_text("🛑 تم إيقاف العملية!")

# ======== دالة الإيقاف =========
async def stop_automation(user_id: int):
    stop_flags[user_id] = True

# ======== main =========
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    add_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("➕ إضافة رقم"), add_number)],
        states={
            ASK_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_number)],
            ASK_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_count)],
            ASK_DELAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_delay)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("📋 عرض الأرقام"), show_numbers))
    app.add_handler(MessageHandler(filters.Regex("📤 إرسال الرسائل"), send_start))
    app.add_handler(add_conv)
    app.add_handler(CallbackQueryHandler(send_button))

    app.run_polling()

if __name__ == "__main__":
    main()
