import json
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = Path("tasks.json")


def load_tasks() -> dict:
    if not DATA_FILE.exists():
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}


def save_tasks(tasks: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(tasks, file, ensure_ascii=False, indent=4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я Task Assistant Bot.\n\n"
        "Я помогу тебе управлять задачами.\n"
        "Используй /help, чтобы посмотреть доступные команды."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Доступные команды:\n\n"
        "/start — запустить бота\n"
        "/help — показать список команд\n"
        "/add <приоритет> <задача> — добавить новую задачу\n"
        "/tasks — показать список задач\n"
        "/done <номер> — отметить задачу выполненной\n"
        "/delete <номер> — удалить задачу"
    )


async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text(
            "Используй команду в формате:\n"
            "/add <приоритет> <задача>\n\n"
            "Доступные приоритеты:\n"
            "high — высокий\n"
            "medium — средний\n"
            "low — низкий\n\n"
            "Пример:\n"
            "/add high Подготовить презентацию"
        )
        return

    priority_input = context.args[0].lower()
    task_text = " ".join(context.args[1:])

    priorities = {
        "high": "высокий",
        "medium": "средний",
        "low": "низкий",
    }

    if priority_input not in priorities:
        await update.message.reply_text(
            "Неизвестный приоритет.\n"
            "Используй: high, medium или low."
        )
        return

    user_id = str(update.effective_user.id)
    tasks = load_tasks()

    if user_id not in tasks:
        tasks[user_id] = []

    tasks[user_id].append(
        {
            "text": task_text,
            "priority": priorities[priority_input],
            "done": False,
        }
    )

    save_tasks(tasks)

    await update.message.reply_text(
        f"✅ Задача добавлена:\n"
        f"{task_text}\n"
        f"Приоритет: {priorities[priority_input]}"
    )


async def done_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text(
            "Используй команду в формате:\n"
            "/done <номер задачи>\n\n"
            "Пример:\n"
            "/done 1"
        )
        return

    try:
        task_number = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "Номер задачи должен быть числом."
        )
        return

    user_id = str(update.effective_user.id)
    tasks = load_tasks()
    user_tasks = tasks.get(user_id, [])

    if task_number < 1 or task_number > len(user_tasks):
        await update.message.reply_text(
            "Задачи с таким номером нет."
        )
        return

    user_tasks[task_number - 1]["done"] = True
    save_tasks(tasks)

    await update.message.reply_text(
        f"✅ Задача №{task_number} отмечена выполненной."
    )



async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text(
            "Используй команду в формате:\n"
            "/delete <номер задачи>\n\n"
            "Пример:\n"
            "/delete 1"
        )
        return

    try:
        task_number = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "Номер задачи должен быть числом."
        )
        return

    user_id = str(update.effective_user.id)
    tasks = load_tasks()
    user_tasks = tasks.get(user_id, [])

    if task_number < 1 or task_number > len(user_tasks):
        await update.message.reply_text(
            "Задачи с таким номером нет."
        )
        return

    deleted_task = user_tasks.pop(task_number - 1)
    save_tasks(tasks)

    await update.message.reply_text(
        f"🗑 Задача удалена:\n{deleted_task['text']}"
    )


async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    tasks = load_tasks()

    user_tasks = tasks.get(user_id, [])

    if not user_tasks:
        await update.message.reply_text(
            "У тебя пока нет задач."
        )
        return

    message = "📋 Твои задачи:\n\n"

    for index, task in enumerate(user_tasks, start=1):
        status = "✅" if task["done"] else "⬜️"
        message += (
            f"{index}. {status} {task['text']}\n"
            f"Приоритет: {task['priority']}\n\n"
        )

    await update.message.reply_text(message)


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в файле .env")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_task))
    application.add_handler(CommandHandler("tasks", show_tasks))
    application.add_handler(CommandHandler("done", done_task))
    application.add_handler(CommandHandler("delete", delete_task))

    print("Бот запущен. Для остановки нажмите Ctrl+C.")
    application.run_polling()


if __name__ == "__main__":
    main()
