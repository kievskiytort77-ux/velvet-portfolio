import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = "ez_life_92"
PRODUCTS_FILE = "products.json"

WAIT_PHOTO, WAIT_NAME, WAIT_BRAND, WAIT_CATEGORY, WAIT_PRICE, WAIT_OLD_PRICE, WAIT_SIZE, WAIT_BADGE = range(8)

CATEGORIES = {
    "summer": "Лето",
    "spring": "Весна",
    "autumn": "Осень",
    "winter": "Зима",
    "brooch": "Брошки"
}

BADGES = {
    "none": "без значка",
    "Hit": "Хит",
    "New": "Новинка",
    "sale15": "-15%",
    "sale20": "-20%",
    "sale30": "-30%"
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
    await update.message.reply_text(
        "👋 Привет! Это панель управления магазином *Velvet Step*\n\nЧто хочешь сделать?",
        reply_markup=InlineKeyboardMarkup(keyboard),
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
            size = f" | Размер: {p.get('size', '—')}" if p.get('size') else ""
            text += f"{i}. {p['icon']} *{p['name']}* — {p['price']}₴{size}\n"
        await query.message.reply_text(text, parse_mode="Markdown")
    elif query.data == "delete_product":
        products = load_products()
        if not products:
            await query.message.reply_text("Товаров нет.")
            return
        keyboard = [[InlineKeyboardButton(f"🗑 {p['name']} — {p['price']}₴", callback_data=f"del_{p['id']}")] for p in products]
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
        await query.message.reply_text("Выбери товар для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith("del_"):
        pid = int(query.data.split("_")[1])
        products = [p for p in load_products() if p["id"] != pid]
        save_products(products)
        await query.message.reply_text("✅ Товар удалён!")
    elif query.data.startswith("cat_"):
        context.user_data["category"] = query.data.split("_", 1)[1]
        await query.message.reply_text("💰 Введи цену товара (например: 4900):")
        return WAIT_PRICE
    elif query.data.startswith("badge_"):
        badge_map = {"none": None, "Hit": "Хіт", "New": "Новинка", "sale15": "-15%", "sale20": "-20%", "sale30": "-30%"}
        context.user_data["badge"] = badge_map.get(query.data.split("_", 1)[1])
        await save_new_product(query.message, context)
        return ConversationHandler.END
    elif query.data == "cancel":
        context.user_data.clear()
        await query.message.reply_text("❌ Отменено.")
        return ConversationHandler.END

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    photo = update.message.photo[-1]
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
        context.user_data["price"] = int(update.message.text.replace(" ", "").replace(",", ""))
        await update.message.reply_text("💰 Введи старую цену (или 0 если нет):")
        return WAIT_OLD_PRICE
    except:
        await update.message.reply_text("⚠️ Введи только число, например: 4900")
        return WAIT_PRICE

async def receive_old_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = int(update.message.text.replace(" ", "").replace(",", ""))
        context.user_data["old"] = val if val > 0 else None
        await update.message.reply_text("📏 Введи размеры (например: 36,37,38,39 или 0 если не нужно):")
        return WAIT_SIZE
    except:
        await update.message.reply_text("⚠️ Введи только число, например: 6000 или 0")
        return WAIT_OLD_PRICE

async def receive_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    size_text = update.message.text.strip()
    context.user_data["size"] = None if size_text == "0" else size_text
    keyboard = [[InlineKeyboardButton(v, callback_data=f"badge_{k}")] for k, v in BADGES.items()]
    await update.message.reply_text("🏷 Выбери значок:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAIT_BADGE

async def save_new_product(message, context: ContextTypes.DEFAULT_TYPE):
    import time
    data = context.user_data
    cat_icons = {"summer": "👡", "spring": "🥿", "autumn": "🥾", "winter": "👢", "brooch": "🌸"}
    product = {
        "id": int(time.time()),
        "cat": data.get("category", "summer"),
        "icon": cat_icons.get(data.get("category", "summer"), "👟"),
        "brand": data.get("brand", ""),
        "name": data.get("name", ""),
        "price": data.get("price", 0),
        "old": data.get("old"),
        "size": data.get("size"),
        "badge": data.get("badge"),
        "file_id": data.get("file_id", "")
    }
    products = load_products()
    products.append(product)
    save_products(products)
    size_text = f"\n📏 Размеры: {product['size']}" if product.get("size") else ""
    old_text = f" (было {product['old']}₴)" if product.get("old") else ""
    text = (
        f"✅ *Товар добавлен!*\n\n"
        f"{product['icon']} *{product['name']}*\n"
        f"🏷 {product['brand']}\n"
        f"💰 {product['price']}₴{old_text}"
        f"{size_text}"
    )
    await message.reply_text(text, parse_mode="Markdown")
    context.user_data.clear()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Отменено.")
    return ConversationHandler.END

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
            WAIT_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_size)],
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
