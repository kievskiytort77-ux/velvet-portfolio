import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "8858872740:AAHpTC4WbQDvNi2K9TTvFwaVpRPsJROAN5M")
ADMIN_USERNAME = "ez_life_brand"
PRODUCTS_FILE = "products.json"

# States
WAIT_PHOTO, WAIT_NAME, WAIT_BRAND, WAIT_CATEGORY, WAIT_PRICE, WAIT_OLD_PRICE, WAIT_BADGE = range(7)

CATEGORIES = {
    "summer": "☀️ Лето",
    "spring": "🌸 Весна", 
    "autumn": "🍂 Осень",
    "winter": "❄️ Зима",
    "brooch": "✨ Брошки"
}

BADGES = {
    "none": "— без значка —",
    "Хіт": "🔥 Хит",
    "Новинка": "⭐ Новинка",
    "−15%": "−15%",
    "−20%": "−20%",
    "−30%": "−30%"
}

def load_products():
    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_products(products):
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def is_admin(update: Update) -> bool:
    return update.effective_user.username == ADMIN_USERNAME

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить товар", callback_data="add_product")],
        [InlineKeyboardButton("📦 Список товаров", callback_data="list_products")],
        [InlineKeyboardButton("🗑 Удалить товар", callback_data="delete_product")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Привет! Это панель управления магазином *Velvet Step*\n\nЧто хочешь сделать?",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update):
        return

    if query.data == "add_product":
        await query.message.reply_text("📸 Отправь фото товара:")
        return WAIT_PHOTO
    
    elif query.data == "list_products":
        products = load_products()
        if not products:
            await query.message.reply_text("📦 Товаров пока нет.")
            return
        text = "📦 *Список товаров:*\n\n"
        for i, p in enumerate(products, 1):
            text += f"{i}. {p['icon']} *{p['name']}* — {p['price']}₴\n"
        await query.message.reply_text(text, parse_mode="Markdown")
    
    elif query.data == "delete_product":
        products = load_products()
        if not products:
            await query.message.reply_text("Товаров нет.")
            return
        keyboard = []
        for p in products:
            keyboard.append([InlineKeyboardButton(
                f"🗑 {p['name']} — {p['price']}₴",
                callback_data=f"del_{p['id']}"
            )])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
        await query.message.reply_text("Выбери товар для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data.startswith("del_"):
        pid = int(query.data.split("_")[1])
        products = load_products()
        products = [p for p in products if p["id"] != pid]
        save_products(products)
        await query.message.reply_text("✅ Товар удалён!")
    
    elif query.data.startswith("cat_"):
        cat = query.data.split("_", 1)[1]
        context.user_data["category"] = cat
        keyboard = [[InlineKeyboardButton(v, callback_data=f"badge_{k}")] for k, v in BADGES.items()]
        await query.message.reply_text("🏷 Выбери значок:", reply_markup=InlineKeyboardMarkup(keyboard))
        return WAIT_BADGE
    
    elif query.data.startswith("badge_"):
        badge = query.data.split("_", 1)[1]
        context.user_data["badge"] = None if badge == "none" else badge
        await save_new_product(query.message, context)
        return ConversationHandler.END
    
    elif query.data == "cancel":
        await query.message.reply_text("❌ Отменено.")
        return ConversationHandler.END

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_url = file.file_path
    context.user_data["photo_url"] = file_url
    context.user_data["file_id"] = photo.file_id
    await update.message.reply_text("✏️ Введи название товара:")
    return WAIT_NAME

async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("🏷 Введи бренд:")
    return WAIT_BRAND

async def receive_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["brand"] = update.message.text
    keyboard = [[InlineKeyboardButton(v, callback_data=f"cat_{k}")] for k, v in CATEGORIES.items()]
    await update.message.reply_text("📂 Выбери категорию:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAIT_CATEGORY

async def receive_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["price"] = int(update.message.text)
        await update.message.reply_text("💰 Введи старую цену (или напиши 0 если нет):")
        return WAIT_OLD_PRICE
    except:
        await update.message.reply_text("Введи только число, например: 4900")
        return WAIT_PRICE

async def receive_old_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = int(update.message.text)
        context.user_data["old"] = val if val > 0 else None
        keyboard = [[InlineKeyboardButton(v, callback_data=f"badge_{k}")] for k, v in BADGES.items()]
        await update.message.reply_text("🏷 Выбери значок:", reply_markup=InlineKeyboardMarkup(keyboard))
        return WAIT_BADGE
    except:
        await update.message.reply_text("Введи только число, например: 6000 или 0")
        return WAIT_OLD_PRICE

async def save_new_product(message, context: ContextTypes.DEFAULT_TYPE):
    import time
    data = context.user_data
    
    cat_icons = {"summer":"👡","spring":"🥿","autumn":"🥾","winter":"👢","brooch":"🌸"}
    
    product = {
        "id": int(time.time()),
        "cat": data.get("category", "summer"),
        "icon": cat_icons.get(data.get("category", "summer"), "👟"),
        "brand": data.get("brand", ""),
        "name": data.get("name", ""),
        "price": data.get("price", 0),
        "old": data.get("old"),
        "badge": data.get("badge"),
        "photo_url": data.get("photo_url", ""),
        "file_id": data.get("file_id", "")
    }
    
    products = load_products()
    products.append(product)
    save_products(products)
    
    text = (
        f"✅ *Товар добавлен!*\n\n"
        f"📦 *{product['name']}*\n"
        f"🏷 {product['brand']}\n"
        f"💰 {product['price']}₴"
    )
    if product["old"]:
        text += f" (было {product['old']}₴)"
    
    await message.reply_text(text, parse_mode="Markdown")
    context.user_data.clear()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END

async def handle_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принимает заказы от сайта через webhook"""
    pass

def main():
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^add_product$")],
        states={
            WAIT_PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
            WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            WAIT_BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_brand)],
            WAIT_CATEGORY: [CallbackQueryHandler(button_handler, pattern="^cat_")],
            WAIT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price)],
            WAIT_OLD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_old_price)],
            WAIT_BADGE: [CallbackQueryHandler(button_handler, pattern="^badge_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
