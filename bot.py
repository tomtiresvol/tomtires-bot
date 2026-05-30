import os
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """Ти — ШІ-консультант інтернет-магазину шин "ПП Терлецький" / TomTires (Україна).

Ти допомагаєш клієнтам:
1. Підібрати шини для автомобіля або мотоцикла за їхніми параметрами
2. Відповісти на питання про бренди:
   - Мотошини: Michelin, Pirelli, Dunlop, Metzeler, Shinko, Anlas
   - Автошини: BFGoodrich KO2, KO3, KM3, Trail-Terrain
3. Оформити заявку або замовлення (збери: ПІБ, телефон, бажана шина, розмір)
4. Розповісти про умови: доставка по Україні, розстрочка до 12 місяців

При підборі шин обов'язково запитуй:
- Тип транспорту (авто / мото)
- Марку і модель
- Розмір шини (якщо знає)
- Сезон (літо/зима/всесезон)
- Бюджет

Відповідай коротко, по справі, дружньо. Мова — українська.
Якщо питання не стосується шин — ввічливо поверни до теми магазину.
Не вигадуй ціни — скажи що уточниш або дай посилання tomtires.com.ua"""

# Зберігаємо історію чату для кожного користувача
user_histories = {}

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text(
        "👋 Привіт! Я ШІ-консультант магазину шин TomTires.\n\n"
        "Допоможу:\n"
        "🔹 Підібрати шини для авто або мото\n"
        "🔹 Відповім на питання про бренди\n"
        "🔹 Оформлю замовлення\n\n"
        "З чого починаємо?"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": user_text})

    # Обмежуємо історію до 20 повідомлень щоб не перевищити ліміт токенів
    if len(user_histories[user_id]) > 20:
        user_histories[user_id] = user_histories[user_id][-20:]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=user_histories[user_id],
        )

        reply = response.content[0].text
        user_histories[user_id].append({"role": "assistant", "content": reply})

        await update.message.reply_text(reply)

    except Exception as e:
        await update.message.reply_text(
            "Вибачте, виникла технічна помилка. Спробуйте ще раз або зателефонуйте: (098) 500 12 50"
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
