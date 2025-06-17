import phonenumbers
from phonenumbers import timezone, geocoder, carrier, number_type, PhoneNumberType, region_code_for_number, format_number, PhoneNumberFormat
import telebot
from telebot import types
from datetime import datetime, timedelta
import requests
import os
import time
import threading

# === НАСТРОЙКИ ===
BOT_TOKEN = "8104258718:AAGSc6fUduEs3DYic10PcGK27FwLTfHVCpQ"
CRYPTO_PAY_API = "415965:AAkEdx0gVcQSHpE3x0EWULFUbN2IvCFK2tW"
BOT_USERNAME = "LifeStanOsintBot"
CRYPTO_CURRENCY = "TON"
CRYPTO_AMOUNT = 20
ADMIN_IDS = [7956920182, 1623802164]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

for f in ["log.txt", "premium.txt", "leaks.txt", "invoices.txt", "user_requests.txt"]:
    if not os.path.exists(f): open(f, "w", encoding="utf-8").close()

# === УТИЛИТЫ ===
def is_premium(uid): return str(uid) in open("premium.txt", encoding="utf-8").read()
def add_premium(uid): open("premium.txt", "a", encoding="utf-8").write(f"{uid}\n")
def log(uid, txt): open("log.txt", "a", encoding="utf-8").write(f"[{datetime.now()}] {uid} -> {txt}\n")
def check_leaks(phone): return phone in open("leaks.txt", encoding="utf-8").read()
def log_request(uid): open("user_requests.txt", "a", encoding="utf-8").write(f"{uid}|{datetime.now()}\n")
def check_limit(uid):
    lines = open("user_requests.txt", encoding="utf-8").readlines()
    now = datetime.now()
    last_hour = [l for l in lines if l.startswith(str(uid)) and now - datetime.strptime(l.split("|")[1].strip(), '%Y-%m-%d %H:%M:%S.%f') < timedelta(hours=1)]
    return len(last_hour) < 3 or is_premium(uid)

# === КНОПКИ ===
@bot.message_handler(commands=["start"])
def start(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📱 Пробить номер", "💎 Купить премиум")
    kb.row("👤 Профиль", "🗑 Удалить данные")
    kb.row("❓ Помощь")
    bot.send_message(message.chat.id, "👋 Привет! Выбери действие:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help_handler(m):
    bot.send_message(m.chat.id, "📘 /start — меню\n📱 Пробей номер в формате +380...\n💎 Премиум — 3+ запроса в час")

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    total = sum(1 for l in open("log.txt", encoding="utf-8") if str(m.from_user.id) in l)
    bot.send_message(m.chat.id, f"👤 <b>Имя:</b> {m.from_user.first_name}\n🆔 <b>ID:</b> {m.from_user.id}\n💎 <b>Премиум:</b> {'Да' if is_premium(m.from_user.id) else 'Нет'}\n📊 <b>Проверок:</b> {total}")

@bot.message_handler(func=lambda m: m.text == "🗑 Удалить данные")
def delete(m):
    for f in ["log.txt", "premium.txt", "user_requests.txt"]:
        lines = open(f, encoding="utf-8").readlines()
        with open(f, "w", encoding="utf-8") as fw:
            fw.writelines([l for l in lines if str(m.from_user.id) not in l])
    bot.send_message(m.chat.id, "✅ Данные удалены.")

@bot.message_handler(func=lambda m: m.text == "💎 Купить премиум")
def buy(m):
    if is_premium(m.from_user.id):
        return bot.send_message(m.chat.id, "💎 У тебя уже есть премиум.")
    try:
        r = requests.post("https://pay.crypt.bot/createInvoice", json={
            "asset": CRYPTO_CURRENCY, "amount": CRYPTO_AMOUNT,
            "description": f"Премиум для {m.from_user.id}",
            "hidden_message": "Спасибо! Премиум активирован.",
            "paid_btn_name": "url", "paid_btn_url": f"https://t.me/{BOT_USERNAME}"
        }, headers={"Crypto-Pay-API-Token": CRYPTO_PAY_API, "Content-Type": "application/json"})
        data = r.json()
        if "result" in data:
            invoice_id = data["result"]["invoice_id"]
            pay_url = data["result"]["pay_url"]
            with open("invoices.txt", "a", encoding="utf-8") as f:
                f.write(f"{m.from_user.id}:{invoice_id}\n")
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("💸 Оплатить через CryptoBot", url=pay_url))
            bot.send_message(m.chat.id, f"💳 Сумма: {CRYPTO_AMOUNT} {CRYPTO_CURRENCY}\n💎 Премиум навсегда.\nПосле оплаты доступ активируется.", reply_markup=kb)
        else:
            bot.send_message(m.chat.id, "❌ Ошибка создания оплаты.")
    except Exception as e:
        bot.send_message(m.chat.id, f"⚠️ Ошибка оплаты: {e}")

@bot.message_handler(func=lambda m: m.text == "📱 Пробить номер")
def ask_number(m):
    bot.send_message(m.chat.id, "📲 Введи номер в формате +380...")

@bot.message_handler(content_types=["text"])
def check_number(m):
    if not m.text.startswith("+") or len(m.text) < 10:
        return
    if not check_limit(m.from_user.id):
        return bot.send_message(m.chat.id, "❌ Лимит 3 запроса в час. Купи 💎 премиум для безлимита.")
    try:
        num = phonenumbers.parse(m.text, None)
        if not phonenumbers.is_possible_number(num):
            return bot.send_message(m.chat.id, "❌ Неверный номер.")
        valid = phonenumbers.is_valid_number(num)
        national = format_number(num, PhoneNumberFormat.NATIONAL)
        region = geocoder.description_for_number(num, "ru")
        zone = ", ".join(timezone.time_zones_for_number(num))
        carrier_name = carrier.name_for_number(num, "ru")
        ccode = num.country_code
        ntype = {
            PhoneNumberType.MOBILE: "📱 Мобильный",
            PhoneNumberType.FIXED_LINE: "☎️ Стационарный",
            PhoneNumberType.VOIP: "🌐 IP",
        }.get(number_type(num), "❓ Неизвестен")
        leaks = check_leaks(m.text)
        msg = (
            f"📞 <b>Номер:</b> {m.text}\n"
            f"✅ <b>Валидный:</b> {'Да' if valid else 'Нет'}\n"
            f"📜 <b>Формат:</b> {national}\n"
            f"📟 <b>Тип:</b> {ntype}\n"
            f"🏢 <b>Оператор:</b> {carrier_name or 'Неизвестен'}\n"
            f"🌍 <b>Регион:</b> {region}\n"
            f"🕒 <b>Часовой пояс:</b> {zone}\n"
            f"🇺🇳 <b>Код страны:</b> +{ccode}\n"
            f"🕵️ <b>Утечка:</b> {'🔴 Найден!' if leaks else '🟢 Нет'}"
        )
        bot.send_message(m.chat.id, msg)
        log(m.from_user.id, m.text)
        log_request(m.from_user.id)

        # уведомление админам
        for admin in ADMIN_IDS:
            try:
                bot.send_message(admin, f"👁 Пользователь @{m.from_user.username or m.from_user.first_name} пробил номер {m.text}")
            except: pass
    except:
        bot.send_message(m.chat.id, "⚠️ Ошибка! Убедись, что номер корректен.")

# === ФОНОВАЯ ПРОВЕРКА ПЛАТЕЖЕЙ ===
def check_payments():
    while True:
        try:
            lines = open("invoices.txt", encoding="utf-8").readlines()
            new = []
            for line in lines:
                uid, invoice = line.strip().split(":")
                r = requests.get(f"https://pay.crypt.bot/getInvoices?invoice_ids={invoice}", headers={"Crypto-Pay-API-Token": CRYPTO_PAY_API})
                data = r.json()
                if "result" in data and data["result"] and data["result"][0]["status"] == "paid":
                    add_premium(uid)
                    bot.send_message(uid, "✅ Оплата прошла. Премиум активирован!")
                else:
                    new.append(line)
            with open("invoices.txt", "w", encoding="utf-8") as f:
                f.writelines(new)
        except Exception as e:
            print("Pay check error:", e)
        time.sleep(10)

threading.Thread(target=check_payments, daemon=True).start()

# === ЗАПУСК ===
bot.infinity_polling()
