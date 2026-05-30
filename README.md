# TomTires Telegram Bot

ШІ-консультант з підбору шин для Telegram.

## Деплой на Railway.app (безкоштовно)

### Крок 1 — Отримай Anthropic API ключ
1. Зайди на https://console.anthropic.com
2. Зареєструйся
3. Розділ "API Keys" → "Create Key"
4. Скопіюй ключ (починається з `sk-ant-...`)

### Крок 2 — Завантаж код на GitHub
1. Зайди на https://github.com → New repository
2. Назви: `tomtires-bot`
3. Завантаж всі файли з цієї папки

### Крок 3 — Деплой на Railway
1. Зайди на https://railway.app
2. "New Project" → "Deploy from GitHub repo"
3. Вибери `tomtires-bot`
4. Перейди в "Variables" і додай:
   - `TELEGRAM_TOKEN` = `8700458501:AAFkRMq6EeqMARtR-WJLXkIiBbLjsNtQm9U`
   - `ANTHROPIC_API_KEY` = твій ключ з кроку 1
5. Натисни "Deploy"

Готово! Бот запрацює за 1-2 хвилини.

## Локальний запуск (для тесту)

```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN=8700458501:AAFkRMq6EeqMARtR-WJLXkIiBbLjsNtQm9U
export ANTHROPIC_API_KEY=sk-ant-...
python bot.py
```
