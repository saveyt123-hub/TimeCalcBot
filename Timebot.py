import asyncio
import logging
import os
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# ===== НАСТРОЙКА ТОКЕНА =====
API_TOKEN = os.getenv('BOT_TOKEN')

if not API_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Добавь переменную окружения в настройках Render")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# ===== ФУНКЦИЯ ПАРСИНГА ВРЕМЕНИ =====
def parse_time_expression(text):
    """
    Парсит выражения времени в различных форматах.
    Возвращает кортеж (часы, минуты, delta_hours, delta_minutes) или None
    """
    text = text.strip().lower()
    
    # === 1. Парсим основное время ===
    time_pattern = r"(\d{1,2})[:\-\.\s](\d{1,2})"
    time_match = re.search(time_pattern, text)
    
    if not time_match:
        return None
    
    hours = int(time_match.group(1))
    minutes = int(time_match.group(2))
    
    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
        return None
    
    # === 2. Парсим добавляемое время ===
    delta_hours = 0
    delta_minutes = 0
    
    hours_patterns = [r"(\d+)\s*(?:час|ч|hour|h|hours)"]
    minutes_patterns = [r"(\d+)\s*(?:мин|м|min|m|minutes)"]
    
    for pattern in hours_patterns:
        hours_match = re.search(pattern, text)
        if hours_match:
            delta_hours = int(hours_match.group(1))
            break
    
    for pattern in minutes_patterns:
        minutes_match = re.search(pattern, text)
        if minutes_match:
            delta_minutes = int(minutes_match.group(1))
            break
    
    if delta_hours == 0 and delta_minutes == 0:
        delta_pattern = r"([+-])\s*(\d+)"
        delta_match = re.search(delta_pattern, text)
        if delta_match:
            sign = delta_match.group(1)
            value = int(delta_match.group(2))
            
            if 'час' in text or 'ч' in text or 'hour' in text or 'h' in text:
                if delta_hours == 0:
                    delta_hours = value
            else:
                delta_minutes = value
            
            if sign == '-':
                delta_hours = -delta_hours
                delta_minutes = -delta_minutes
    
    operator_match = re.search(r"([+-])\s*(.+)", text)
    if operator_match:
        sign = operator_match.group(1)
        delta_text = operator_match.group(2)
        
        delta_hours = 0
        delta_minutes = 0
        
        delta_hours_match = re.search(r"(\d+)\s*(?:час|ч|hour|h|hours)", delta_text)
        if delta_hours_match:
            delta_hours = int(delta_hours_match.group(1))
        
        delta_minutes_match = re.search(r"(\d+)\s*(?:мин|м|min|m|minutes)", delta_text)
        if delta_minutes_match:
            delta_minutes = int(delta_minutes_match.group(1))
        
        if delta_hours == 0 and delta_minutes == 0:
            numbers = re.findall(r"\d+", delta_text)
            if numbers:
                if len(numbers) == 2:
                    delta_hours = int(numbers[0])
                    delta_minutes = int(numbers[1])
                elif len(numbers) == 1:
                    delta_minutes = int(numbers[0])
        
        if sign == '-':
            delta_hours = -delta_hours
            delta_minutes = -delta_minutes
    
    return (hours, minutes, delta_hours, delta_minutes)


# ===== ПРИВЕТСТВИЕ ПО КОМАНДЕ /start =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 *Привет! Я Time Calculator Bot*\n\n"
        "⏰ *Я умею считать время!*\n\n"
        "📝 *Примеры использования:*\n"
        "• `18:10 + 45 мин` → `18:55`\n"
        "• `18-10 + 1час 30 минут` → `19:40`\n"
        "• `18.10 - 30 мин` → `17:40`\n"
        "• `18 10 + 45` → `18:55`\n\n"
        "🔧 *Поддерживаемые форматы:*\n"
        "• Разделители: `:`, `-`, `.`, пробел\n"
        "• Единицы: `мин`, `м`, `час`, `ч`, `min`, `hour`\n"
        "• Операции: `+` (прибавить), `-` (отнять)\n\n"
        "💡 *Просто напиши мне выражение и я посчитаю!*",
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="📚 Примеры",
                        callback_data="examples"
                    ),
                    types.InlineKeyboardButton(
                        text="⚙️ О боте",
                        callback_data="about"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="🔗 Добавить в чат",
                        url=f"https://t.me/{(await bot.get_me()).username}?startgroup=true"
                    )
                ]
            ]
        )
    )


# ===== ОБРАБОТКА КНОПОК =====
@dp.callback_query()
async def process_callback(callback: types.CallbackQuery):
    await callback.answer()  # Убираем "часики" загрузки
    
    if callback.data == "examples":
        await callback.message.edit_text(
            "📚 *Примеры использования:*\n\n"
            "1️⃣ *Простое сложение:*\n"
            "`18:10 + 45 мин` → `18:55`\n\n"
            "2️⃣ *С часами и минутами:*\n"
            "`14:00 + 1час 30 минут` → `15:30`\n\n"
            "3️⃣ *Вычитание:*\n"
            "`20:00 - 45 мин` → `19:15`\n\n"
            "4️⃣ *Разные разделители:*\n"
            "`18-10 + 30м` → `18:40`\n"
            "`18.10 + 1ч` → `19:10`\n"
            "`18 10 + 45` → `18:55`\n\n"
            "↩️ Напиши /start чтобы вернуться",
            parse_mode="Markdown"
        )
    
    elif callback.data == "about":
        await callback.message.edit_text(
            "⚙️ *О боте:*\n\n"
            "🤖 *Time Calculator Bot*\n"
            "Версия: 1.0\n\n"
            "💡 Этот бот помогает быстро считать время,\n"
            "прибавляя или отнимая минуты и часы.\n\n"
            "🛠 *Технологии:*\n"
            "• Python 3.13\n"
            "• aiogram 3.x\n"
            "• Хостинг: Render\n\n"
            "↩️ Напиши /start чтобы вернуться",
            parse_mode="Markdown"
        )


# ===== ПРИВЕТСТВИЕ ПРИ ПЕРВОМ СООБЩЕНИИ =====
@dp.message(lambda message: message.text and not message.text.startswith('/'))
async def first_message_greeting(message: types.Message):
    """Приветствует пользователя при первом сообщении"""
    result = parse_time_expression(message.text)
    
    if result is None:
        await message.answer(
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            "Я *Time Calculator Bot* ⏰\n\n"
            "Похоже, ты написал не команду для расчёта времени.\n"
            "Напиши /start чтобы узнать как мной пользоваться!",
            parse_mode="Markdown"
        )
        return
    
    await calculate_time(message)


# ===== ОСНОВНАЯ ЛОГИКА РАСЧЁТА =====
@dp.message()
async def calculate_time(message: types.Message):
    user_text = message.text.strip()
    result = parse_time_expression(user_text)
    
    if result:
        hours, minutes, delta_hours, delta_minutes = result
        
        try:
            start_time = datetime.now().replace(
                hour=hours, minute=minutes, second=0, microsecond=0
            )
            
            total_minutes = delta_hours * 60 + delta_minutes
            result_time = start_time + timedelta(minutes=total_minutes)
            final_answer = result_time.strftime("%H:%M")
            
            delta_text = ""
            if delta_hours != 0 or delta_minutes != 0:
                parts = []
                if delta_hours != 0:
                    parts.append(f"{abs(delta_hours)} ч")
                if delta_minutes != 0:
                    parts.append(f"{abs(delta_minutes)} мин")
                sign = "+" if (delta_hours * 60 + delta_minutes) >= 0 else "-"
                delta_text = f" ({sign} {' '.join(parts)})"
            
            await message.answer(
                f"⏰ *Результат:* `{final_answer}`{delta_text}",
                parse_mode="Markdown"
            )
            
        except ValueError as e:
            await message.answer(f"❌ Ошибка в формате времени: {e}")
    else:
        await message.answer(
            "🤔 Я не понял формат. Попробуй один из этих вариантов:\n\n"
            "• `18:10 + 45 мин`\n"
            "• `18-10 + 45м`\n"
            "• `18.10 + 1час 30 минут`\n"
            "• `18 10 + 45`\n"
            "• `18:10 - 30 мин`",
            parse_mode="Markdown"
        )


# ===== HTTP СЕРВЕР ДЛЯ RENDER =====
async def handle_health(request):
    """Обработчик для проверки здоровья бота"""
    return web.json_response({
        "status": "ok",
        "bot": "running",
        "message": "Time Calculator Bot is alive!"
    })

async def handle_root(request):
    """Главная страница"""
    return web.Response(
        text="<h1>⏰ Time Calculator Bot</h1><p>Bot is running successfully!</p>",
        content_type="text/html"
    )

async def start_http_server():
    """Запускаем HTTP сервер на порту 8080"""
    app = web.Application()
    app.router.add_get('/', handle_root)
    app.router.add_get('/health', handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    logging.info("✅ HTTP server started on port 8080")
    logging.info("🔍 Health check available at: /health")
    
    return runner


# ===== ЗАПУСК =====
async def main():
    """Основная функция запуска"""
    logging.info("🚀 Starting Time Calculator Bot...")
    
    http_runner = await start_http_server()
    
    try:
        logging.info("🤖 Starting bot polling...")
        await dp.start_polling(bot)
    finally:
        await http_runner.cleanup()
        await bot.session.close()
        logging.info("👋 Bot stopped")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("⌨️ Stopped by user")
