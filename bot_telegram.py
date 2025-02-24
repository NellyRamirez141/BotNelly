import os
import logging
import sqlite3
import random
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
import pickle

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Configurar logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Base de datos SQLite
conn = sqlite3.connect("bot_memory.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS responses (user_message TEXT, bot_response TEXT)")
conn.commit()

# Modo aprendizaje
learning_mode = False
current_question = None

# Inicializar el modelo
vectorizer = TfidfVectorizer()
clf = MultinomialNB()

# Cargar datos de entrenamiento
def cargar_datos():
    cursor.execute("SELECT user_message, bot_response FROM responses")
    data = cursor.fetchall()
    if data:
        preguntas, respuestas = zip(*data)
        return list(preguntas), list(respuestas)
    return [], []

# Entrenar modelo
def entrenar_modelo():
    preguntas, respuestas = cargar_datos()
    if preguntas:
        X_train = vectorizer.fit_transform(preguntas)
        clf.fit(X_train, respuestas)
        with open("modelo.pkl", "wb") as f:
            pickle.dump((vectorizer, clf), f)
    else:
        logging.warning("No hay datos suficientes para entrenar el modelo.")

# Cargar modelo desde archivo
def cargar_modelo():
    global vectorizer, clf
    try:
        with open("modelo.pkl", "rb") as f:
            vectorizer, clf = pickle.load(f)
    except FileNotFoundError:
        entrenar_modelo()

# Predecir respuesta
def predecir_respuesta(pregunta):
    if not hasattr(clf, "classes_"):
        return "No tengo suficiente información aún. Enséñame más."
    X_input = vectorizer.transform([pregunta])
    return clf.predict(X_input)[0]

async def handle_message(update: Update, context: CallbackContext) -> None:
    global learning_mode, current_question
    user_message = update.message.text.lower()

    if user_message == "stnelly141":
        learning_mode = not learning_mode
        state = "activado" if learning_mode else "desactivado"
        await update.message.reply_text(f"Modo aprendizaje {state}.")
        return
    
    if learning_mode:
        if current_question is None:
            current_question = user_message
            await update.message.reply_text("¿Cómo debería responder a esto?")
        else:
            cursor.execute("INSERT INTO responses (user_message, bot_response) VALUES (?, ?)", (current_question, user_message))
            conn.commit()
            entrenar_modelo()
            await update.message.reply_text("Respuesta guardada. ¿Quieres agregar otra respuesta para la misma pregunta? (sí/no)")
            context.user_data["waiting_confirmation"] = True
    else:
        cursor.execute("SELECT bot_response FROM responses WHERE user_message = ?", (user_message,))
        results = cursor.fetchall()
        if results:
            response = random.choice(results)[0]
        else:
            response = predecir_respuesta(user_message)
        await update.message.reply_text(response)

async def confirm_learning(update: Update, context: CallbackContext) -> None:
    global current_question
    user_message = update.message.text.lower()
    if context.user_data.get("waiting_confirmation", False):
        if user_message == "sí":
            await update.message.reply_text("Ingresa la siguiente respuesta para la pregunta.")
        elif user_message == "no":
            current_question = None
            await update.message.reply_text("Pregunta finalizada. Ingresa una nueva pregunta o usa 'stnelly141' para salir del modo aprendizaje.")
            context.user_data["waiting_confirmation"] = False
        return

def main():
    cargar_modelo()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_learning))
    logging.info("Bot en funcionamiento...")
    app.run_polling()

if __name__ == "__main__":
    main()
