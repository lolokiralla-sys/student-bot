"""
نظام شكاوي طلاب متكامل (إدارة + أرشفة + ترقيم)
"""

import logging
import json
import os
from datetime import datetime

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

# 🔐 التوكن
BOT_TOKEN = "8764101661:AAHn3IS2EA-ZkGy6jk5or6EUKvaKvZdyttk"

# 📢 القناة
CHANNEL_ID = "-1003992977228"

# 📂 ملفات التخزين
DATA_FILE = "complaints.json"
COUNTER_FILE = "counters.json"

logging.basicConfig(level=logging.INFO)

NAME, STUDENT_ID, CATEGORY, PROBLEM = range(4)

# =========================
# 🧠 التخزين والأرشفة
# =========================

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_counters():
    if not os.path.exists(COUNTER_FILE):
        return {"administrative": 0, "academic": 0, "other": 0}
    with open(COUNTER_FILE, "r") as f:
        return json.load(f)

def save_counters(data):
    with open(COUNTER_FILE, "w") as f:
        json.dump(data, f)

# =========================
# 🚀 البداية
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 أهلاً بك في نظام الشكاوي\nاكتب اسمك الكامل للبدء:",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME

# =========================
# 👤 الاسم
# =========================

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("📌 اكتب رقم القيد:")
    return STUDENT_ID

# =========================
# 🆔 رقم القيد
# =========================

async def get_student_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["student_id"] = update.message.text

    keyboard = [
        [InlineKeyboardButton("🏢 إداري", callback_data="administrative")],
        [InlineKeyboardButton("📚 أكاديمي", callback_data="academic")],
        [InlineKeyboardButton("📋 أخرى", callback_data="other")],
    ]

    await update.message.reply_text(
        "اختر نوع الشكوى:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CATEGORY

# =========================
# 📂 التصنيف
# =========================

CATEGORY_LABELS = {
    "administrative": "🏢 إداري",
    "academic": "📚 أكاديمي",
    "other": "📋 أخرى",
}

CATEGORY_CODES = {
    "administrative": "1",
    "academic": "2",
    "other": "3",
}

async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat = query.data
    context.user_data["category"] = cat

    await query.edit_message_text("✍️ اكتب تفاصيل المشكلة:")
    return PROBLEM

# =========================
# 📝 المشكلة + إرسال
# =========================

async def get_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    problem = update.message.text
    user = update.effective_user
    data = context.user_data

    counters = load_counters()
    cat = data["category"]

    counters[cat] += 1
    save_counters(counters)

    ticket_id = f"{CATEGORY_CODES[cat]}-{counters[cat]:03d}"

    complaint = {
        "ticket": ticket_id,
        "name": data["name"],
        "student_id": data["student_id"],
        "category": CATEGORY_LABELS[cat],
        "problem": problem,
        "user_id": user.id,
        "username": user.username,
        "time": str(datetime.now())
    }

    all_data = load_data()
    all_data.append(complaint)
    save_data(all_data)

    message = f"""
📩 شكوى جديدة #{ticket_id}
━━━━━━━━━━━━━━
👤 الاسم: {complaint['name']}
🆔 القيد: {complaint['student_id']}
📂 النوع: {complaint['category']}
━━━━━━━━━━━━━━
📝 المشكلة:
{problem}
━━━━━━━━━━━━━━
👤 المرسل: {user.full_name}
"""

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=message
    )

    await update.message.reply_text(f"✅ تم تسجيل شكواك برقم: {ticket_id}")

    context.user_data.clear()
    return ConversationHandler.END

# =========================
# ❌ إلغاء
# =========================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("تم الإلغاء")
    return ConversationHandler.END

# =========================
# 📊 إدارة (للمشرف)
# =========================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    await update.message.reply_text(f"📊 عدد الشكاوي: {len(data)}")

# =========================
# 🚀 تشغيل البوت
# =========================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT, get_name)],
            STUDENT_ID: [MessageHandler(filters.TEXT, get_student_id)],
            CATEGORY: [CallbackQueryHandler(get_category)],
            PROBLEM: [MessageHandler(filters.TEXT, get_problem)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("stats", stats))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
