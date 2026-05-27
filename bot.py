import os
import json
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USERNAME = "ez_life_92"

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://qpfilpvlwoikrfvxbwba.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_secret_sc38d6jYs_ceoXdErffffw_AJO90d6m")

WAIT_PHOTO, WAIT_NAME, WAIT_BRAND, WAIT_CATEGORY, WAIT_PRICE, WAIT_OLD_PRICE, WAIT_SIZE, WAIT_DESC, WAIT_BADGE = range(9)

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
    "-15%": "-15%",
    "-20%": "-20%",
    "-30%": "-30%"
}

CAT_ICONS = {
    "summer": "👡",
    "spring": "🥿",
    "autumn": "🥾",
    "winter": "👢",
    "brooch": "🌸"
}

async def supabase_request(method, path, data=None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    async with httpx.AsyncClient() as client:
        if method == "GET":
            r = await client.get(url, headers=headers)
        elif method == "POST":
            r = await client.post(url, headers=headers, json=data)
        elif method == "DELETE":
            r = await client.delete(url, headers=headers)
    return r

async def get_products():
    r = await supabase_request("GET", "products?select=*&order=id.desc")
    return r.json() if r.status_code == 200 else []

async def add_product(product):
    r = await supabase_request("POST", "products", product)
    return r.status_code in [200, 201]

async def delete_product(pid):
    r = await supabase_request("DELETE", f"products?id=eq.{pid}")
    return r.status_code in [200, 204]

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
        "👋 Привет! Панель управления *Velvet Step*\n\nЧто хочешь сделать?",
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
        products = await get_products()
        if not products:
            await query.message.reply_text("📦 Товаров пока нет.")
            return
        text = "📦 *Список товаров:*\n\n"
        for i, p in enumerate(products, 1):
            text += f"{i}. {p.get('icon','👟')} *{p['name']}* — {p['price']}₴\n"
        await query.message.reply_text(text, parse_mode="Markdown")

    elif query.data == "delete_product":
        products = await get_products()
        if not products:
            await query.message.reply_text("Товаров нет.")
            return
        keyboard = [[InlineKeyboardButton(f"🗑 {p['name']} — {p['price']}₴", callback_data=f"del_{p['id']}")] for p in products]
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
        await query.message.reply_text("Выбери товар:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("del_"):
        pid = query.data.split("_")[1]
        await delete_product(pid)
        await query.message.reply_text("✅ Товар удалён!")

    elif query.data.startswith("cat_"):
        cat = query.data.split("_", 1)[1]
        context.user_data["category"] = cat
        context.user_data["icon"] = CAT_ICONS.get(cat, "👟")
        await query.message.reply_text("💰 Введи цену (например: 4900):")
        return WAIT_PRICE

    elif query.data.startswith("badge_"):
        badge = query.data.split("_", 1)[1]
        context.user_data["badge"] = None if badge == "none" else badge
        await save_product(query.message, context)
        return ConversationHandler.END

    elif query.data == "cancel":
        context.user_data.clear()
        await query.message.reply_text("❌ Отменено.")
        return ConversationHandler.END

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
    photo = update.message.photo[-1]
    file = await photo.get_file()

    # Скачиваем фото из Telegram
    async with httpx.AsyncClient() as client:
        response = await client.get(file.file_path)
        photo_bytes = response.content

    # Загружаем в Supabase Storage
    file_name = f"{photo.file_unique_id}.jpg"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/products/{file_name}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "image/jpeg"
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(upload_url, headers=headers, content=photo_bytes)

    # Постоянная публичная ссылка
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/products/{file_name}"
    context.user_data["photo_url"] = public_url
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
        await update.message.reply_text("💰 Введи старую цену (или 0):")
        return WAIT_OLD_PRICE
    except:
        await update.message.reply_text("⚠️ Только число, например: 4900")
        return WAIT_PRICE

async def receive_old_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = int(update.message.text.replace(" ", "").replace(",", ""))
        context.user_data["old_price"] = val if val > 0 else None
        await update.message.reply_text("📏 Введи размеры (например: 36,37,38 или 0):")
        return WAIT_SIZE
    except:
        await update.message.reply_text("⚠️ Только число, например: 6000 или 0")
        return WAIT_OLD_PRICE

async def receive_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    context.user_data["size"] = None if val == "0" else val
    await update.message.reply_text("📝 Введи описание товара (или напиши 0 если нет):")
    return WAIT_DESC

async def receive_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    context.user_data["description"] = None if val == "0" else val
    keyboard = [[InlineKeyboardButton(v, callback_data=f"badge_{k}")] for k, v in BADGES.items()]
    await update.message.reply_text("🏷 Выбери значок:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WAIT_BADGE

async def save_product(message, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    product = {
        "name": data.get("name", ""),
        "brand": data.get("brand", ""),
        "category": data.get("category", "summer"),
        "icon": data.get("icon", "👟"),
        "price": data.get("price", 0),
        "old_price": data.get("old_price"),
        "size": data.get("size"),
        "description": data.get("description"),
        "badge": data.get("badge"),
        "photo_url": data.get("photo_url", ""),
        "file_id": data.get("file_id", "")
    }
    ok = await add_product(product)
    if ok:
        old_text = f" (было {product['old_price']}₴)" if product.get("old_price") else ""
        size_text = f"\n📏 Размеры: {product['size']}" if product.get("size") else ""
        desc_text = f"\n📝 {product['description']}" if product.get("description") else ""
        await message.reply_text(
            f"✅ *Товар добавлен на сайт!*\n\n"
            f"{product['icon']} *{product['name']}*\n"
            f"🏷 {product['brand']}\n"
            f"💰 {product['price']}₴{old_text}"
            f"{size_text}{desc_text}",
            parse_mode="Markdown"
        )
    else:
        await message.reply_text("❌ Ошибка при сохранении. Попробуй ещё раз.")
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
            WAIT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_desc)],
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
