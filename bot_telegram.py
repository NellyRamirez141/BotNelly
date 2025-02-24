import os
import logging
import sqlite3
import random
import asyncio
from rapidfuzz import process
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Base de datos SQLite
conn = sqlite3.connect("bot_memory.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute(
    "CREATE TABLE IF NOT EXISTS responses (user_message TEXT, bot_response TEXT)"
)  
conn.commit()

# Variables de control
target_word = "stnelly141"
learning_mode = False
current_question = None

async def handle_message(update: Update, context: CallbackContext) -> None:
    global learning_mode, current_question

    user_message = update.message.text.lower()
    
    # Inicializar user_data si no existe
    if "waiting_confirmation" not in context.user_data:
        context.user_data["waiting_confirmation"] = False

    # Confirmación de aprendizaje
    if context.user_data["waiting_confirmation"]:
        if user_message == "sí":
            await update.message.reply_text("Ingresa otra respuesta para la misma pregunta:")
            return
        elif user_message == "no":
            current_question = None
            await update.message.reply_text(f"Pregunta finalizada. Ingresa una nueva pregunta o usa '{target_word}' para salir del modo aprendizaje.")
            context.user_data["waiting_confirmation"] = False
            return

    # Activar o desactivar modo aprendizaje
    if user_message == target_word:
        learning_mode = not learning_mode
        state = "activado" if learning_mode else "desactivado"
        await update.message.reply_text(f"Modo aprendizaje {state}.")
        return
    
    # Modo aprendizaje activo
    if learning_mode:
        if current_question is None:
            current_question = user_message
            await update.message.reply_text("¿Cómo debería responder a esto?")
        else:
            cursor.execute(
                "INSERT INTO responses (user_message, bot_response) VALUES (?, ?)", 
                (current_question, user_message)
            )
            conn.commit()
            await update.message.reply_text("Respuesta guardada. ¿Quieres agregar otra respuesta para la misma pregunta? (sí/no)")
            context.user_data["waiting_confirmation"] = True
        return

    # Buscar coincidencias en la base de datos
    cursor.execute("SELECT DISTINCT user_message FROM responses")
    known_questions = [row[0] for row in cursor.fetchall()]
    
    # Verificar si hay coincidencias con RapidFuzz
    best_match = None
    if known_questions:
        result = process.extractOne(user_message, known_questions, score_cutoff=75)
        if result:
            best_match, score, _ = result

    if best_match:
        cursor.execute("SELECT bot_response FROM responses WHERE user_message = ?", (best_match,))
        results = cursor.fetchall()
        if results:
            response = random.choice(results)[0]
            await update.message.reply_text(response)
            return
    
    await update.message.reply_text("No te entendí bb.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("Bot en funcionamiento...")
    app.run_polling()

if __name__ == "__main__":
    main()
