"""
بوت تيليجرام لاستقبال شكاوي ومشاكل الطلاب
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# 🔐 حطي التوكن الجديد هنا
BOT_TOKEN = "8764101661:AAHn3IS2EA-ZkGy6jk5or6EUKvaKvZdyttk"

# 📢 معرف القناة (برايفيت أو عام)
CHANNEL_ID = "-1003992977228"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

NAME, STUDENT_ID, CATEGORY, PROBLEM = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    welcome_text = (
        "🎓 *أهلاً وسهلاً بك في بوابة الشكاوي والمشكلات*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏛️ *مكتب شؤون الطلبة*\n\n"
        "يسعدنا استقبال استفساراتكم وشكاواكم.\n"
        "سنقوم بمعالجة طلبك في أقرب وقت ممكن.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "للبدء، يُرجى إدخال *اسمك الكامل* 👇"
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if len(name) < 3:
        await update.message.reply_text("⚠️ يُرجى إدخال الاسم كاملاً (ثلاثة أحرف على الأقل).")
        return NAME

    context.user_data["name"] = name
    await update.message.reply_text(
        f"✅ شكراً *{name}*\n\n"
        "الآن يُرجى إدخال *رقم قيدك الجامعي* 🔢",
        parse_mode="Markdown",
    )
    return STUDENT_ID


async def get_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    student_id = update.message.text.strip()
    if not student_id:
        await update.message.reply_text("⚠️ يُرجى إدخال رقم القيد.")
        return STUDENT_ID

    context.user_data["student_id"] = student_id

    keyboard = [
        [InlineKeyboardButton("🏢 إدارية", callback_data="administrative")],
        [InlineKeyboardButton("📚 أكاديمية", callback_data="academic")],
        [InlineKeyboardButton("📋 أخرى", callback_data="other")],
    ]

    await update.message.reply_text(
        "📂 *تصنيف المشكلة*\n\nيُرجى اختيار نوع مشكلتك:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CATEGORY


CATEGORY_LABELS = {
    "administrative": "🏢 إدارية",
    "academic": "📚 أكاديمية",
    "other": "📋 أخرى",
}


async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    category_key = query.data
    context.user_data["category"] = CATEGORY_LABELS.get(category_key, category_key)

    await query.edit_message_text(
        f"✅ التصنيف: *{context.user_data['category']}*\n\n"
        "✏️ الآن اكتب *مشكلتك أو شكواك* بالتفصيل 👇",
        parse_mode="Markdown",
    )
    return PROBLEM


async def get_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    problem = update.message.text.strip()
    if len(problem) < 10:
        await update.message.reply_text("⚠️ يُرجى وصف المشكلة بشكل أوضح (١٠ أحرف على الأقل).")
        return PROBLEM

    user = update.effective_user
    data = context.user_data

    channel_message = (
        "📩 *شكوى جديدة*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *الاسم:* {data.get('name', '—')}\n"
        f"🆔 *رقم القيد:* {data.get('student_id', '—')}\n"
        f"📂 *التصنيف:* {data.get('category', '—')}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 *المشكلة:*\n{problem}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 المُرسِل: {user.full_name}"
        + (f" (@{user.username})" if user.username else "")
        + f"🆔 Telegram ID: {user.id}"
    )

    try:
        await context.bot.send_message(
    chat_id=CHANNEL_ID,
    text=channel_message,
)
    except Exception as e:
        logger.error(f"فشل إرسال الرسالة إلى القناة: {e}")
        await update.message.reply_text(
            "⚠️ حدث خطأ أثناء إرسال رسالتك. يُرجى التأكد أن البوت أدمن في القناة."
        )
        return ConversationHandler.END

    confirmation = (
        "✅ *استلمنا رسالتك،*\n"
        "سيتم الرد عليك في أقرب فرصة.\n\n"
        "🏛️ *مكتب شؤون الطلبة*"
    )
    await update.message.reply_text(confirmation, parse_mode="Markdown")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "❌ تم إلغاء العملية.\n"
        "يمكنك البدء من جديد بكتابة /start",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            STUDENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_student_id)],
            CATEGORY: [CallbackQueryHandler(get_category)],
            PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_problem)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)

    logger.info("🤖 البوت يعمل الآن...")
    app.run_polling()


if __name__ == "__main__":
    main()
