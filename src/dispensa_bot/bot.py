import json
import os
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.dispensa_bot.llm import interpret_message
from src.dispensa_bot.db import DispensaDB

#obj creation
db = DispensaDB()

# Carica le variabili dal file .env
load_dotenv()


# Funzione eseguita quando l'utente scrive /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Ciao! Scrivimi cosa hai comprato o consumato.\n\n"
        "Esempi:\n"
        "- ho comprato latte, pasta e pollo\n"
        "- ho finito il latte\n"
        "- ho usato metà del pollo\n"
        "- cosa ho in frigo?"
    )


# Funzione eseguita quando l'utente manda un messaggio di testo normale
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Prendiamo il testo scritto dall'utente su Telegram
    user_text = update.message.text
    normalized_text = user_text.strip().lower()

    if normalized_text == "pulisci tutto":
        deleted_count = db.delete_all_items()
        await update.message.reply_text(
            f"Dispensa svuotata. Ho eliminato {deleted_count} prodotti."
        )
        return
        
    try:
    # Mandiamo il testo all'LLM, che prova a trasformarlo in JSON
        result = await interpret_message(user_text)
        
        intent = result.get("intent")

        if intent in ["list_items", "list_by_location"]:

            location = result.get("target_location")

            if intent == "list_items":
                location = None

            rows = db.list_items(location)

            if not rows:
                if location:
                    await update.message.reply_text(f"Non ho trovato prodotti in {location}.")
                else:
                    await update.message.reply_text("La dispensa è vuota.")
                return

            await update.message.reply_text(db.format_items(rows))
            return
        
        
        if intent == "consume_item":
            items = result.get("items", [])

            if not items:
                await update.message.reply_text("Non ho capito quale prodotto hai consumato.")
                return

            messages = []  
            for item in items:
                amount_fraction = item.get("amount_fraction", result.get("amount_fraction"))
                message = db.consume_item(item, amount_fraction)
                messages.append(message)

            await update.message.reply_text("\n".join(messages))
            return
                

        # Se l'intent è add_items, salviamo ogni prodotto nel database
        if result.get("intent") == "add_items":
            for item in result.get("items", []):
                db.add_item(item)

        # Rendiamo il JSON più leggibile da mostrare in chat
        pretty_json = json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )

    except Exception as error:
        # Se qualcosa va storto, mostriamo l'errore
        await update.message.reply_text(
            "Errore mentre parlavo con Ollama.\n\n"
            f"Dettaglio: {error}"
        )


# Funzione principale che avvia il bot Telegram
def run_bot() -> None:
    # Leggiamo il token del bot dal file .env
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    # Se il token manca, fermiamo il programma
    if not token:
        raise RuntimeError("Manca TELEGRAM_BOT_TOKEN nel file .env")

    # Creiamo l'app Telegram usando il token
    app = ApplicationBuilder().token(token).build()

    # Colleghiamo il comando /start alla funzione start
    app.add_handler(CommandHandler("start", start))

    # Colleghiamo tutti i messaggi di testo alla funzione handle_text
    # Escludiamo i comandi, perché quelli iniziano con /
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Messaggio nel terminale per sapere che il bot è partito
    print("Bot avviato. Premi CTRL+C per fermarlo.")

    # Avvia il bot e resta in ascolto dei messaggi Telegram
    app.run_polling()
