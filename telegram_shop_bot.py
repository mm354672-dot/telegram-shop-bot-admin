
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Types
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Инициализация логирования и бота
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = "ВАШ_ТОКЕН_БОТА"
PAYMENTS_TOKEN = "ВАШ_ТОКЕН_ОПЛАТЫ"  # Токен ЮKassa/Сбербанка из BotFather
ADMIN_ID = 123456789  # Ваше Telegram ID для доступа к админке

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Имитация базы данных
DB_PRODUCTS = {
    "1": {"name": "Ключ Windows 11 Pro", "price": 450, "keys": ["WIN11-AAAA-BBBB", "WIN11-CCCC-DDDD"]},
    "2": {"name": "VPN Доступ (1 месяц)", "price": 150, "keys": ["VPN-KEY-USER123", "VPN-KEY-USER999"]}
}
USERS_COUNT = 42  # Для демонстрации в админке

# === КЛИЕНТСКАЯ ЧАСТЬ ===

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Главное меню магазина"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 Каталог товаров", callback_data="catalog")
    builder.button(text="ℹ️ Поддержка", callback_data="support")
    
    # Если пишет админ — добавляем кнопку админки
    if message.from_user.id == ADMIN_ID:
        builder.button(text="⚙️ Админ-панель", callback_data="admin_menu")
        
    builder.adjust(1)
    await message.answer(
        f"Привет, {message.from_user.full_name}! Добро пожаловать в автоматический магазин цифровых товаров.",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    """Отображение товаров"""
    builder = InlineKeyboardBuilder()
    for prod_id, info in DB_PRODUCTS.items():
        builder.button(text=f"{info['name']} — {info['price']}₽", callback_data=f"buy_{prod_id}")
    builder.button(text="⬅️ Назад", callback_data="to_main")
    builder.adjust(1)
    await callback.message.edit_text("Выберите интересующий товар из списка:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery):
    """Выставление счета на оплату"""
    prod_id = callback.data.split("_")[1]
    product = DB_PRODUCTS.get(prod_id)
    
    if not product or not product["keys"]:
        await callback.answer("Извините, товар закончился!", show_alert=True)
        return

    await callback.message.answer(
        text=f"Вы покупаете: {product['name']}\nЦена: {product['price']} руб.",
    )
    
    # Отправляем инвойс (счет на оплату) через Telegram Payments
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=product["name"],
        description=f"Автоматическая покупка и мгновенная выдача ключа",
        payload=f"payload_{prod_id}",
        provider_token=PAYMENTS_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label=product["name"], amount=product["price"] * 100)]  # Цена в копейках
    )
    await callback.answer()

# === ОБРАБОТКА ПЛАТЕЖЕЙ ===

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Проверка доступности товара перед списанием денег"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Выдача товара после успешной оплаты"""
    payload = message.successful_payment.invoice_payload
    prod_id = payload.split("_")[1]
    product = DB_PRODUCTS.get(prod_id)
    
    # Берем первый доступный ключ из нашей "базы"
    purchased_key = product["keys"].pop(0) if product and product["keys"] else "ОШИБКА-ОБРАТИТЕСЬ-В-ПОДДЕРЖКУ"
    
    await message.answer(
        f"🎉 Спасибо за оплату!\n\n"
        f"🎁 Ваш товар: **{product['name']}**\n"
        f"🔑 Ключ активации: `{purchased_key}`\n\n"
        f"Инструкция по активации отправлена вместе с ключом."
    )

# === АДМИН-ПАНЕЛЬ ===

@dp.callback_query(F.data == "admin_menu")
async def show_admin_menu(callback: CallbackQuery):
    """Интерфейс админки"""
    if callback.from_user.id != ADMIN_ID:
        return
        
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить товар", callback_data="admin_add")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="⬅️ В главное меню", callback_data="to_main")
    builder.adjust(2, 1)
    
    await callback.message.edit_text(
        "Панель администратора.\nЗдесь вы можете управлять продажами вашего бизнеса.",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "admin_stats")
async def show_admin_stats(callback: CallbackQuery):
    """Просмотр статистики бизнеса"""
    await callback.message.answer(
        f"📊 **Статистика магазина:**\n\n"
        f"👥 Всего пользователей: {USERS_COUNT}\n"
        f"💰 Успешных продаж сегодня: 14\n"
        f"📈 Выручка за 24 часа: 4,900 руб."
    )
    await callback.answer()

@dp.callback_query(F.data == "to_main")
async def to_main_menu(callback: CallbackQuery):
    """Возврат в меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 Каталог товаров", callback_data="catalog")
    builder.button(text="ℹ️ Поддержка", callback_data="support")
    if callback.from_user.id == ADMIN_ID:
        builder.button(text="⚙️ Admin Menu", callback_data="admin_menu")
    builder.adjust(1)
    await callback.message.edit_text("Главное меню магазина:", reply_markup=builder.as_markup())

async def main():
    print("[+] Бот успешно запущен и готов к продажам!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
