import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "8********7:AAEIm5nF_-nm-9w0-C3n3Ud7Jp02wMIXb_s"      # Токен от @BotFather
CHAT_ID = 8*******9            # Твой числовой ID из @userinfobot
LATITUDE = 53.1959                # Координаты Самары (широта)
LONGITUDE = 50.1004               # Координаты Самары (долгота)
SEND_TIME_HOUR = 8                # Час отправки (по местному времени Самары)
TIMEZONE = ZoneInfo("Europe/Samara")

# Глобальная переменная для хранения ID чата (в реальном боте это лучше сохранять в файл/БД)
target_chat_id = None

# ================= ПОГОДА =================
# Словарь для расшифровки погодных кодов Open-Meteo (WMO)
def get_weather_emoji(code: int) -> str:
    if code == 0: return "☀️ Ясно"
    if code in [1, 2, 3]: return "⛅️ Переменная облачность"
    if code in [45, 48]: return "🌫️ Туман"
    if code in [51, 53, 55]: return "🌦️ Морось"
    if code in [61, 63, 65, 80, 81, 82]: return "🌧️ Дождь"
    if code in [71, 73, 75, 85, 86]: return "🌨️ Снег"
    if code in [95, 96, 99]: return "⛈️ Гроза"
    return "🌡️ Погода"

async def fetch_weather() -> str:
    """Асинхронный запрос к Open-Meteo API"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": ["temperature_2m_max", "temperature_2m_min", "weather_code"],
        "timezone": "Europe/Samara",
        "forecast_days": 1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
            
            # Достаем данные из ответа API
            max_temp = data["daily"]["temperature_2m_max"][0]
            min_temp = data["daily"]["temperature_2m_min"][0]
            weather_code = data["daily"]["weather_code"][0]
            date_str = data["daily"]["time"][0]
            
            # Форматируем дату в красивый вид
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d.%m.%Y")
            
            emoji = get_weather_emoji(weather_code)
            
            return (
                f"🌤 <b>Погода в Самаре на {formatted_date}</b>\n\n"
                f"{emoji}\n"
                f"🔺 Макс: +{max_temp}°C\n"
                f"🔻 Мин: +{min_temp}°C"
            )

# ================= ХЕНДЛЕРЫ (КОМАНДЫ) =================
async def cmd_start(message: types.Message):
    global target_chat_id
    target_chat_id = message.chat.id  # Запоминаем, кому слать погоду
    
    weather_text = await fetch_weather()
    await message.answer(
        f"Привет! Я бот погоды для Самары. 🌍\n\n"
        f"Я запомнил твой ID и теперь буду каждый день в {SEND_TIME_HOUR}:00 "
        f"присылать тебе прогноз.\n\n"
        f"А вот погода на сегодня:\n\n{weather_text}",
        parse_mode="HTML"
    )

async def cmd_weather(message: types.Message):
    """Команда для ручной проверки погоды"""
    weather_text = await fetch_weather()
    await message.answer(weather_text, parse_mode="HTML")

# ================= ФОНОВАЯ ЗАДАЧА =================
async def daily_weather_sender(bot: Bot):
    """Бесконечный цикл, который ждет нужного времени и отправляет погоду"""
    global target_chat_id
    
    while True:
        try:
            # Если пользователь еще не нажал /start, ждем 10 секунд и пробуем снова
            if target_chat_id is None:
                await asyncio.sleep(10)
                continue

            now = datetime.now(TIMEZONE)
            # Считаем, когда будет следующая отправка (сегодня или завтра в SEND_TIME_HOUR)
            target_time = now.replace(hour=SEND_TIME_HOUR, minute=0, second=0, microsecond=0)
            if now >= target_time:
                target_time += timedelta(days=1)
            
            # Считаем разницу в секундах и "засыпаем"
            sleep_seconds = (target_time - now).total_seconds()
            print(f"Следующая отправка погоды в {target_time.strftime('%d.%m.%Y %H:%M')}")
            await asyncio.sleep(sleep_seconds)
            
            # Когда время пришло - получаем погоду и отправляем
            weather_text = await fetch_weather()
            await bot.send_message(target_chat_id, weather_text, parse_mode="HTML")
            
        except Exception as e:
            print(f"Ошибка в фоновой задаче: {e}")
            await asyncio.sleep(60) # При ошибке ждем минуту перед новой попыткой

# ================= ЗАПУСК =================
async def main():
    # Включаем логирование, чтобы видеть ошибки
    logging.basicConfig(level=logging.INFO)
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрируем команды
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_weather, Command("weather"))
    
    # Запускаем фоновую задачу параллельно с ботом
    asyncio.create_task(daily_weather_sender(bot))
    
    # Запускаем "прослушку" сообщений (Polling)
    print("Бот запущен и ждет команд...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")
