"""
نظام شكاوي طلاب متكامل (لوحة تحكم + إشعارات + أرشفة)
"""

import logging
import json
import os
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
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

DATA_FILE = "complaints.json"
COUNTER_FILE = "counters.json"

logging.basicConfig(level=logging.INFO)

NAME, STUDENT_ID, CATEGORY, PROBLEM = range(4)

# =========================
# 💾 تخزين
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

def find_complaint(data, ticket):
    for c in data:
        if c["ticket"] == ticket:
            return c
    return None

# =========================
# 🚀 البداية
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎓 اكتب اسمك للبدء:",
        reply_markup=ReplyKeyboardRemove()
    )
    return NAME

# =========================
# 👤 الاسم
# =========================

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("📌 رقم القيد:")
    return STUDENT_ID

# =========================
# 🆔 القيد
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

    context.user_data["category"] = query.data
    await query.edit_message_text("✍️ اكتب المشكلة بالتفصيل:")
    return PROBLEM

# =========================
# 📝 إرسال الشكوى
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
        "time": str(datetime.now()),
        "status": "🟡 قيد المعالجة"
    }

    db = load_data()
    db.append(complaint)
    save_data(db)

    msg = f"""
📩 شكوى #{ticket_id}
👤 {complaint['name']}
📂 {complaint['category']}
📝 {problem}
"""

    await context.bot.send_message(chat_id=CHANNEL_ID, text=msg)

    await update.message.reply_text(f"✅ تم تسجيل الشكوى: {ticket_id}")

    context.user_data.clear()
    return ConversationHandler.END

# =========================
# 🧑‍💼 لوحة التحكم (عرض الشكاوى)
# =========================

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()

    if not data:
        await update.message.reply_text("لا توجد شكاوى")
        return

    for c in data[-10:]:  # آخر 10 شكاوى
        keyboard = [
            [
                InlineKeyboardButton("🟢 حل", callback_data=f"resolve:{c['ticket']}"),
                InlineKeyboardButton("🔴 رفض", callback_data=f"reject:{c['ticket']}"),
            ],
            [
                InlineKeyboardButton("📌 قيد", callback_data=f"pending:{c['ticket']}"),
            ]
        ]

        text = f"""
📩 {c['ticket']}
👤 {c['name']}
📂 {c['category']}
📊 {c['status']}
"""

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# =========================
# 🔄 تغيير الحالة + إشعار الطالب
# =========================

async def handle_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, ticket = query.data.split(":")
    data = load_data()

    c = find_complaint(data, ticket)
    if not c:
        await query.edit_message_text("غير موجودة")
        return

    user_id = c["user_id"]

    if action == "resolve":
        c["status"] = "🟢 تم الحل"
        status_text = "تم حل الشكوى"

    elif action == "reject":
        c["status"] = "🔴 مرفوضة"
        status_text = "تم رفض الشكوى"

    elif action == "pending":
        c["status"] = "🟡 قيد المعالجة"
        status_text = "قيد المعالجة"

    save_data(data)

    # 📢 إشعار الطالب
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"📢 تحديث شكواك #{ticket}\n📊 الحالة: {status_text}"
        )
    except:
        pass

    await query.edit_message_text(f"{ticket} → {status_text}")

# =========================
# 🚀 تشغيل
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
        fallbacks=[],
    )

    app.add_handler(conv)

    # 🧑‍💼 لوحة التحكم
    app.add_handler(CommandHandler("panel", panel))

    # 🔄 أزرار الإدارة
    app.add_handler(CallbackQueryHandler(handle_actions))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
