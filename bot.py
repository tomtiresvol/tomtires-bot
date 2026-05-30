import os
import anthropic
import httpx
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ADMIN_URL = os.environ.get("ADMIN_URL", "https://mng.tomtires.com.ua")
ADMIN_LOGIN_1 = os.environ.get("ADMIN_LOGIN_1", "")
ADMIN_PASS_1 = os.environ.get("ADMIN_PASS_1", "")
ADMIN_LOGIN_2 = os.environ.get("ADMIN_LOGIN_2", "")
ADMIN_PASS_2 = os.environ.get("ADMIN_PASS_2", "")

admin_cookies = {}

async def admin_login() -> dict:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r1 = await client.post(
                f"{ADMIN_URL}/auth",
                data={"login": ADMIN_LOGIN_1, "password": ADMIN_PASS_1},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            r2 = await client.post(
                f"{ADMIN_URL}/auth",
                data={"login": ADMIN_LOGIN_2, "password": ADMIN_PASS_2},
                headers={"User-Agent": "Mozilla/5.0"}
            )
            return dict(client.cookies)
    except Exception as e:
        print(f"Login error: {e}")
        return {}

async def search_catalog(query: str) -> str:
    global admin_cookies
    try:
        if not admin_cookies:
            admin_cookies = await admin_login()

        async with httpx.AsyncClient(timeout=15, follow_redirects=True, cookies=admin_cookies) as client:
            r = await client.get(
                f"{ADMIN_URL}/catalog",
                params={"search": query},
                headers={"User-Agent": "Mozilla/5.0"}
            )

        soup = BeautifulSoup(r.text, "html.parser")

        results = []
        rows = soup.select("tr, .product-row, .catalog-row, .item-row")[:10]
        for row in rows:
            cells = row.select("td")
            if len(cells) >= 2:
                name = cells[0].get_text(strip=True)
                price = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                stock = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                if name and len(name) > 5:
                    line = f"• {name}"
                    if price:
                        line += f" — {price}"
                    if stock:
                        line += f" (в наявності: {stock})"
                    results.append(line)

        if results:
            return "Знайдено в каталозі:\n\n" + "\n".join(results[:8])

        items = soup.select("a, .name, .title, .product-name")[:10]
        for item in items:
            text = item.get_text(strip=True)
            if len(text) > 10 and any(c.isdigit() for c in text):
                results.append(f"• {text}")

        if results:
            return "Знайдено в каталозі:\n\n" + "\n".join(results[:8])

        return "Нічого не знайдено в каталозі за цим запитом."

    except Exception as e:
        print(f"Catalog search error: {e}")
        admin_cookies = {}
        return await search_tomtires_public(query)

async def search_tomtires_public(query: str) -> str:
    try:
        url = f"https://tomtires.com.ua/catalog/tyre/?search={query.replace(' ', '+')}"
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("a[href*='/catalog/tyre/v-']")[:8]
        results = []
        for card in cards:
            name = card.get_text(strip=True)
            href = card.get("href", "")
            if len(name) > 10:
                results.append(f"• {name}\n  https://tomtires.com.ua{href}")
        if results:
            return "Знайдено на tomtires.com.ua:\n\n" + "\n\n".join(results[:5])
        return "На сайті нічого не знайдено."
    except Exception as e:
        return f"Помилка пошуку: {e}"

SYSTEM_PROMPT = """Ти — ШІ-консультант інтернет-магазину шин ПП Терлецький / TomTires (Україна, Володимир-Волинський).

ПРІОРИТЕТ: завжди спочатку пропонуй шини від постачальника ПП Терлецький (Володимир-Волинський).

Ти допомагаєш клієнтам:
1. Підібрати шини для автомобіля або мотоцикла
2. Відповісти на питання про бренди: Michelin, Pirelli, Dunlop, Metzeler, BFGoodrich KO2/KO3/KM3
3. Оформити замовлення (збери: ПІБ, телефон, шина, розмір)

Коли отримуєш дані з каталогу — показуй клієнту реальні назви та ціни.
Умови: доставка по Україні.
Відповідай коротко, дружньо, українською мовою."""

user_histories = {}
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_histories[update.effective_user.id] = []
    await update.message.reply_text(
        "👋 Привіт! Я ШІ-консультант TomTires.\n\n"
        "🔹 Підберу шини для авто або мото\n"
        "🔹 Відповім на питання про бренди\n"
        "🔹 Оформлю замовлення\n\n"
        "Напишіть розмір шини (наприклад: 205 55 16) або задайте питання!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in user_histories:
        user_histories[user_id] = []

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    site_data = ""
    digits = [c for c in user_text if c.isdigit()]
    if len(digits) >= 3:
        await update.message.reply_text("🔍 Шукаю в каталозі...")
        site_data = await search_catalog(user_text)

    message_content = user_text
    if site_data:
        message_content = f"{user_text}\n\n[Дані з каталогу]:\n{site_data}"

    user_histories[user_id].append({"role": "user", "content": message_content})

    if len(user_histories[user_id]) > 20:
        user_histories[user_id] = user_histories[user_id][-20:]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=user_histories[user_id],
        )
        reply = response.content[0].text
        user_histories[user_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text(
            "Вибачте, технічна помилка. Телефонуйте: (098) 500 12 50"
        )
        print(f"Error: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущено...")
    app.run_polling()

if __name__ == "__main__":
    main()
