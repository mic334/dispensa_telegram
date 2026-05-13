import json
import os
import traceback
from datetime import timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.dispensa_bot.llm import interpret_message, interpret_receipt_image
from src.dispensa_bot.db import DispensaDB


# Carica le variabili dal file .env
load_dotenv()

# Creazione oggetto database
db = DispensaDB()


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


def clean_receipt_items(items: list[dict]) -> list[dict]:
    blocked_words = [
        "grazie",
        "arrivederci",
        "subtotale",
        "totale",
        "totale complessivo",
        "iva",
        "prezzo",
        "descrizione",
        "pagamento",
        "carta",
        "bancomat",
        "contanti",
        "resto",
        "punti",
        "fidelity",
        "via ",
        "p.i.",
        "partita iva",
        "codice fiscale",
        "pam panorama",
        "s.p.a",
    ]

    cleaned = []

    for item in items:
        name = str(item.get("name", "")).strip()
        raw_line = str(item.get("raw_line", "")).strip()
        confidence = item.get("confidence")

        text = f"{name} {raw_line}".lower()

        if not name:
            continue

        if any(word in text for word in blocked_words):
            continue

        try:
            if confidence is not None and float(confidence) < 0.4:
                continue
        except (ValueError, TypeError):
            continue

        cleaned.append(item)

    return cleaned

def apply_shelf_life(item, message_date):
    shelf_life_days = item.get("shelf_life_days")

    if shelf_life_days is not None and not item.get("expiry_date"):
        try:
            days = int(float(shelf_life_days))
            base_date = message_date.astimezone(ZoneInfo("Europe/Rome")).date()
            item["expiry_date"] = (base_date + timedelta(days=days)).isoformat()
        except (ValueError, TypeError):
            pass

    item.pop("shelf_life_days", None)
    return item


def format_quantity(quantity):
    try:
        return f"{float(quantity):g}"
    except (ValueError, TypeError):
        return str(quantity)


# Funzione eseguita quando l'utente manda un messaggio di testo normale
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text
    normalized_text = user_text.strip().lower()
    
    if normalized_text in ["conferma", "annulla"]:
        chat_id = update.effective_chat.id
        receipt = db.get_last_draft_receipt(chat_id)

        if not receipt:
            await update.message.reply_text(
                "Non ho trovato nessuno scontrino da confermare o annullare."
            )
            return

        receipt_id = receipt["id"]
        label = receipt["label"]

        if normalized_text == "annulla":
            db.cancel_receipt(receipt_id)
            await update.message.reply_text(
                f'Ho annullato "{label}".'
            )
            return

        if normalized_text == "conferma":
            receipt_lines = db.get_receipt_lines(receipt_id)

            if not receipt_lines:
                await update.message.reply_text(
                    f'Lo scontrino "{label}" non contiene prodotti.'
                )
                return

            added_count = 0

            for row in receipt_lines:
                item = {
                    "name": row.get("name") or row.get("raw_name"),
                    "quantity": row.get("quantity") or 1,
                    "unit": row.get("unit") or "pezzo",
                    "price": row.get("line_price"),
                    "location": None,
                    "expiry_date": None,
                    "notes": f'Da {label}',
                }

                db.add_item(item)
                added_count += 1

            db.confirm_receipt(receipt_id)

            await update.message.reply_text(
                f'Ho confermato "{label}" e aggiunto {added_count} prodotti alla dispensa ✅'
            )
            return
    

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
                    await update.message.reply_text(
                        f"Non ho trovato prodotti in {location}."
                    )
                else:
                    await update.message.reply_text("La dispensa è vuota.")
                return

            await update.message.reply_text(db.format_items(rows))
            return

        if intent == "consume_item":
            items = result.get("items", [])

            if not items:
                await update.message.reply_text(
                    "Non ho capito quale prodotto hai consumato."
                )
                return

            messages = []

            for item in items:
                amount_fraction = item.get(
                    "amount_fraction",
                    result.get("amount_fraction"),
                )
                message = db.consume_item(item, amount_fraction)
                messages.append(message)

            await update.message.reply_text("\n".join(messages))
            return

        if intent == "discard_item":
            items = result.get("items", [])

            if not items:
                await update.message.reply_text(
                    "Non ho capito quale prodotto hai buttato."
                )
                return

            messages = []

            for item in items:
                amount_fraction = item.get(
                    "amount_fraction",
                    result.get("amount_fraction"),
                )
                message = db.discard_item(item, amount_fraction)
                messages.append(message)

            await update.message.reply_text("\n".join(messages))
            return

        if intent == "expiring_items":
            days = result.get("days", 3)
            rows = db.get_expiring_items(days)

            if not rows:
                await update.message.reply_text("Non ho trovato prodotti in scadenza.")
                return

            await update.message.reply_text(db.format_items(rows))
            return

        if intent == "pantry_value":
            value = db.get_pantry_value()
            await update.message.reply_text(f"La dispensa vale circa €{value:.2f}")
            return

        if intent == "waste_log":
            message = db.list_waste_log()
            await update.message.reply_text(message)
            return

        if intent == "add_items":
            message_date = update.message.date

            for item in result.get("items", []):
                item = apply_shelf_life(item, message_date)
                db.add_item(item)

            await update.message.reply_text("Prodotti aggiunti ✅")
            return

        # Se l'intent non è riconosciuto
        pretty_json = json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )

        await update.message.reply_text(
            "Non ho capito bene cosa fare.\n\n"
            f"Risultato ricevuto:\n{pretty_json}"
        )

    except Exception as error:
        await update.message.reply_text(
            "Errore mentre parlavo con Ollama.\n\n"
            f"Dettaglio: {error}"
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Leggo lo scontrino...")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    os.makedirs("tmp", exist_ok=True)
    image_path = f"tmp/receipt_{photo.file_unique_id}.jpg"

    await file.download_to_drive(image_path)

    try:
        result = await interpret_receipt_image(image_path)
        items = result.get("items", [])
        items = clean_receipt_items(items)
        if not items:
            await update.message.reply_text(
                "Non sono riuscito a leggere lo scontrino in modo affidabile. "
                "Ho trovato righe ambigue o prezzi non sicuri, quindi non aggiungo nulla."
            )
            return

        blocked_words = [
            "sconto",
            "subtotale",
            "iva",
            "pagamento",
            "carta",
            "bancomat",
            "contanti",
            "resto",
            "punti",
            "fidelity",
        ]

        items = [
            item
            for item in items
            if not any(
                word in item.get("name", "").lower()
                for word in blocked_words
            )
        ]

        if not items:
            await update.message.reply_text(
                "Non ho trovato prodotti nello scontrino."
            )
            return

        
        chat_id = update.effective_chat.id

        total_price = 0.0
        for item in items:
            price = item.get("price")
            if price is not None:
                try:
                    total_price += float(str(price).replace(",", "."))
                except (ValueError, TypeError):
                    pass

        receipt_id, label = db.create_receipt(
            chat_id=chat_id,
            total_price=total_price,
        )

        for item in items:
            db.add_receipt_line(receipt_id, item)

        lines = [f'Ho letto lo scontrino "{label}":']

        for_number = 1
        
        for item in items:
            name = item.get("name", "prodotto")
            quantity = item.get("quantity") or 1
            unit = item.get("unit") or "pezzo"
            price = item.get("price")
            #raw_line = item.get("raw_line")
            confidence = item.get("confidence")

            line = f"• {name} - {format_quantity(quantity)} {unit}"

            if price is not None:
                try:
                    line += f" - €{float(price):.2f}"
                except (ValueError, TypeError):
                    line += f" - €{price}"


            lines.append(line)
            for_number += 1

        lines.append("")
        lines.append(f"Totale letto: €{total_price:.2f}")
        lines.append("")
        lines.append("Vuoi aggiungere questo scontrino alla dispensa?")
        lines.append('Rispondi "conferma" oppure "annulla".')

        await update.message.reply_text("\n".join(lines))

    except Exception as error:
        print("ERRORE SCONTRINO:")
        print(traceback.format_exc())

        await update.message.reply_text(
            "Errore mentre leggevo lo scontrino.\n\n"
            f"Dettaglio: {repr(error)}"
        )

# Funzione principale che avvia il bot Telegram
def run_bot() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError("Manca TELEGRAM_BOT_TOKEN nel file .env")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot avviato. Premi CTRL+C per fermarlo.")

    app.run_polling()


if __name__ == "__main__":
    run_bot()