import sqlite3
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import asyncio
from datetime import datetime

# Configurar logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# Base de datos SQLite
db = sqlite3.connect("word_game.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    score INTEGER DEFAULT 0,
    last_attempt TEXT,
    has_scored_today INTEGER DEFAULT 0
)
""")
db.commit()

# Verificar si la columna "has_scored_today" existe y agregarla si falta
cursor.execute("PRAGMA table_info(users)")
columns = [col[1] for col in cursor.fetchall()]
if "has_scored_today" not in columns:
    cursor.execute("ALTER TABLE users ADD COLUMN has_scored_today INTEGER DEFAULT 0")
    db.commit()

# Palabra secreta (se debe cambiar manualmente)
SECRET_WORD = "ejemplo"

# Comando /start
async def start(update: Update, context: CallbackContext) -> None:
    if update.message:
        await update.message.reply_text("¡Bienvenido al juego de palabras! Envía una palabra para intentar adivinar.")

# Comando /rmk para cambiar la palabra secreta
async def change_secret_word(update: Update, context: CallbackContext) -> None:
    global SECRET_WORD
    if not context.args:
        await update.message.reply_text("Uso: /rmk nuevapalabra")
        return
    SECRET_WORD = " ".join(context.args).strip().lower()
    await update.message.reply_text(f"🔄 La palabra secreta ha sido cambiada a: {SECRET_WORD}")

# Manejar intentos de palabra
async def handle_message(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return
    
    user_id = update.message.from_user.id
    username = update.message.from_user.username or update.message.from_user.first_name or "Anon"
    word = update.message.text.strip().lower()
    today = datetime.now().date().isoformat()
    
    cursor.execute("SELECT score, last_attempt, has_scored_today FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result:
        score, last_attempt, has_scored_today = result
    else:
        cursor.execute("INSERT INTO users (user_id, username, score, last_attempt, has_scored_today) VALUES (?, ?, 0, '', 0)", (user_id, username))
        db.commit()
        score, last_attempt, has_scored_today = 0, "", 0
    
    if word == SECRET_WORD:
        if last_attempt == today and has_scored_today:
            await update.message.reply_text("Ya has adivinado la palabra hoy y sumado puntos. Inténtalo de nuevo mañana.")
            return
        score += 1
        cursor.execute("UPDATE users SET score = ?, last_attempt = ?, has_scored_today = 1 WHERE user_id = ?", (score, today, user_id))
        db.commit()
        await update.message.reply_text(f"¡Correcto! Has ganado 1 punto. Puntaje total: {score}")
    else:
        await update.message.reply_text("Palabra incorrecta. Inténtalo nuevamente.")

# Comando /puntos
async def show_leaderboard(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return
    
    cursor.execute("SELECT username, score FROM users ORDER BY score DESC LIMIT 10")
    ranking = cursor.fetchall()
    
    message = "🏆 Tabla de clasificación:\n"
    for i, (user, score) in enumerate(ranking, start=1):
        message += f"{i}. {user}: {score} puntos\n"
    
    await update.message.reply_text(message)

# Comando /darklud para limpiar la tabla de clasificación
async def clear_leaderboard(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return
    
    cursor.execute("DELETE FROM users")
    db.commit()
    await update.message.reply_text("🔄 La tabla de clasificación ha sido reiniciada.")

# Comando /user para cambiar el nombre de usuario
async def change_username(update: Update, context: CallbackContext) -> None:
    if not update.message or not context.args:
        await update.message.reply_text("Uso: /user nuevousuario")
        return
    
    user_id = update.message.from_user.id
    new_username = " ".join(context.args).strip()
    
    cursor.execute("SELECT user_id FROM users WHERE username = ?", (new_username,))
    if cursor.fetchone():
        await update.message.reply_text("⚠️ Ese nombre ya está en uso. Elige otro.")
        return
    
    cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (new_username, user_id))
    db.commit()
    await update.message.reply_text(f"✅ Tu nombre ha sido cambiado a {new_username}.")

# Configurar el bot
def main():
    TOKEN = "7778816951:AAEV2Sdr2DTElMsEjAwqQc7NZJrV7qFHkUQ"
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("puntos", show_leaderboard))
    app.add_handler(CommandHandler("darklud", clear_leaderboard))
    app.add_handler(CommandHandler("user", change_username))
    app.add_handler(CommandHandler("rmk", change_secret_word))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

if __name__ == "__main__":
    main()
