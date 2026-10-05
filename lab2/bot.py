import os
import sqlite3

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_FILE = "tasks.db"


def init_db() -> None:
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                priority TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я Task Assistant Bot.\n\n"
        "В этой версии задачи хранятся в SQLite.\n"
        "Используй /help, чтобы посмотреть доступные команды."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Доступные команды:\n\n"
        "/start — запустить бота\n"
        "/help — показать список команд\n"
        "/add <приоритет> <задача> — добавить задачу\n"
        "/tasks — показать задачи\n"
        "/done <номер> — отметить задачу выполненной\n"
        "/delete <номер> — удалить задачу\n"
        "/stats — показать статистику задач"
    )


async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) < 2:
        await update.message.reply_text(
            "Используй формат:\n"
            "/add <приоритет> <задача>\n\n"
            "Приоритеты: high, medium, low\n"
            "Пример: /add high Подготовить презентацию"
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
            "Неизвестный приоритет. Используй high, medium или low."
        )
        return

    user_id = update.effective_user.id

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (user_id, text, priority) VALUES (?, ?, ?)",
            (user_id, task_text, priorities[priority_input]),
        )
        conn.commit()

    await update.message.reply_text(
        f"✅ Задача добавлена в базу данных:\n"
        f"{task_text}\n"
        f"Приоритет: {priorities[priority_input]}"
    )


async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, text, priority, done
            FROM tasks
            WHERE user_id = ?
            ORDER BY id
            """,
            (user_id,),
        )
        tasks = cursor.fetchall()

    if not tasks:
        await update.message.reply_text("У тебя пока нет задач в базе данных.")
        return

    message = "📋 Твои задачи из SQLite:\n\n"

    for index, task in enumerate(tasks, start=1):
        _, text, priority, done = task
        status = "✅" if done else "⬜️"
        message += (
            f"{index}. {status} {text}\n"
            f"Приоритет: {priority}\n\n"
        )

    await update.message.reply_text(message)


def get_user_tasks(user_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, text, priority, done
            FROM tasks
            WHERE user_id = ?
            ORDER BY id
            """,
            (user_id,),
        )
        return cursor.fetchall()


async def done_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text(
            "Используй: /done <номер задачи>"
        )
        return

    try:
        task_number = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Номер задачи должен быть числом.")
        return

    user_id = update.effective_user.id
    tasks = get_user_tasks(user_id)

    if task_number < 1 or task_number > len(tasks):
        await update.message.reply_text("Задачи с таким номером нет.")
        return

    task_id = tasks[task_number - 1][0]

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET done = 1 WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        )
        conn.commit()

    await update.message.reply_text(
        f"✅ Задача №{task_number} отмечена выполненной."
    )


async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text(
            "Используй: /delete <номер задачи>"
        )
        return

    try:
        task_number = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Номер задачи должен быть числом.")
        return

    user_id = update.effective_user.id
    tasks = get_user_tasks(user_id)

    if task_number < 1 or task_number > len(tasks):
        await update.message.reply_text("Задачи с таким номером нет.")
        return

    task_id = tasks[task_number - 1][0]
    task_text = tasks[task_number - 1][1]

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        )
        conn.commit()

    await update.message.reply_text(
        f"🗑 Задача удалена из базы данных:\n{task_text}"
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ?",
            (user_id,),
        )
        total = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND done = 1",
            (user_id,),
        )
        completed = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND done = 0",
            (user_id,),
        )
        active = cursor.fetchone()[0]

    await update.message.reply_text(
        "📊 Статистика задач:\n\n"
        f"Всего: {total}\n"
        f"Активных: {active}\n"
        f"Выполненных: {completed}"
    )


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в файле .env")

    init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_task))
    application.add_handler(CommandHandler("tasks", show_tasks))
    application.add_handler(CommandHandler("done", done_task))
    application.add_handler(CommandHandler("delete", delete_task))
    application.add_handler(CommandHandler("stats", stats))

    print("Бот Lab2 запущен. Используется база данных SQLite.")
    application.run_polling()


if __name__ == "__main__":
    main()
