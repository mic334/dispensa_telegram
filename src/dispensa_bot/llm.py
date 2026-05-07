import json
import os

import httpx
from dotenv import load_dotenv


# Carica le variabili dal file .env
load_dotenv()


# URL dell'API di Ollama
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")

# Modello Ollama da usare
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


# Prompt principale: spiega all'LLM cosa deve fare
SYSTEM_PROMPT = """
Sei il cervello di un bot Telegram per gestire una dispensa domestica.

Leggi il messaggio dell'utente e trasformalo in JSON valido.

Regole principali:
- Rispondi SOLO con JSON valido
- Non scrivere spiegazioni
- Non usare markdown
- Non inventare prodotti non citati dall'utente
- Se non capisci, usa intent = "unknown"

Intent possibili:

1. add_items
Quando l'utente compra, aggiunge o mette via prodotti.
Esempi:
- ho comprato latte e pasta
- aggiungi 2 pacchi di riso
- metti in frigo 6 uova

2. consume_item
Quando l'utente consuma, beve, mangia, usa, toglie, riduce o finisce prodotti.
Esempi:
- ho bevuto mezzo litro di latte
- ho usato metà latte
- ho dimezzato il pacco di pasta
- ho consumato il 70 percento della pasta
- ho mangiato 300 grammi di pollo
- ho finito i biscotti

3. list_items
Quando l'utente vuole vedere tutti i prodotti.
Esempi:
- cosa ho?
- che cosa tengo?
- fammi vedere tutto
- mostrami i prodotti
- lista prodotti
- cosa c'è?

4. list_by_location
Quando l'utente vuole vedere i prodotti di una zona specifica.
Esempi:
- cosa ho in frigo?
- cosa tengo in dispensa?
- fammi vedere il congelatore
- che c'è nel frigo?
- mostrami la dispensa

5. move_item
Quando l'utente vuole spostare un prodotto.
Esempi:
- sposta il latte in frigo
- metti la pasta in dispensa

6. set_expiry
Quando l'utente indica o modifica una scadenza.
Esempi:
- il latte scade domani
- la pasta scade il 20 maggio

7. oldest_item
Quando l'utente chiede il prodotto più vecchio o vicino alla scadenza.
Esempi:
- cosa scade prima?
- qual è la cosa più vecchia?

8. unknown
Quando non capisci il messaggio.

Location possibili:
- frigo
- congelatore
- dispensa
- spezie
- olio
- bagno
- altro

Formato risposta:

{
  "intent": "...",
  "items": [
    {
      "name": "...",
      "quantity": null,
      "unit": null,
      "location": null,
      "expiry_date": null,
      "notes": null,
      "amount_fraction": null
    }
  ],
  "target_location": null,
  "amount_fraction": null,
  "question": null,
  "confidence": 0.0
}

Regole:

Intent:
- Se l'utente aggiunge, compra o mette via prodotti, usa intent = "add_items"
- Se l'utente consuma, beve, mangia, usa, toglie, dimezza o finisce prodotti, usa intent = "consume_item"
- Se l'utente chiede cosa ha in generale, usa intent = "list_items"
- Se l'utente chiede cosa ha in una zona specifica, usa intent = "list_by_location"

Consumo:
- Per consume_item metti sempre i prodotti dentro "items"
- Se ci sono più prodotti consumati, crea più oggetti dentro "items"
- Ogni prodotto consumato deve avere la sua quantity oppure il suo amount_fraction
- Se dice "metà", "mezza" o "dimezzato", amount_fraction = 0.5
- Se dice "un terzo", amount_fraction = 0.333
- Se dice "70 percento" o "70%", amount_fraction = 0.7
- Se dice "finito", "elimina", "cancella", "togli tutto", amount_fraction = 1
- Se non capisci quanto è stato consumato, quantity = null e amount_fraction = null

Unità e quantità:
- Se dice "300 gr", "300 g" o "300 grammi", quantity = 300 e unit = "grammi"
- Non convertire grammi in kg
- Non convertire litri in ml
- Se dice "un bicchiere" di una bevanda, quantity = 0.2 e unit = "litro"
- Se dice "mezzo bicchiere" di una bevanda, quantity = 0.1 e unit = "litro"
- Se dice "due bicchieri" di una bevanda, quantity = 0.4 e unit = "litro"
- Non usare "bicchiere" come unità nel JSON

Location:
- Se puoi intuire la location, mettila
- Latte, yogurt, carne, pollo, pesce, uova, affettati, birra, vino, bibite e acqua vanno in "frigo"
- Pasta, riso, biscotti e farina vanno in "dispensa"
- Spezie vanno in "spezie"
- Olio va in "olio"

Lista:
- Se l'utente chiede cosa ha, cosa tiene, cosa c'è o vuole vedere prodotti, usa list_items o list_by_location
"""


# Funzione che manda il testo dell'utente a Ollama
async def interpret_message(user_text: str) -> dict:
    # Corpo della richiesta da mandare a Ollama
    payload = {
        "model": OLLAMA_MODEL,
        "format": "json",
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_text,
            },
        ],
    }

    # Chiamata HTTP asincrona verso Ollama
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(OLLAMA_URL, json=payload)
        response.raise_for_status()

    # Leggiamo la risposta di Ollama
    data = response.json()
    content = data["message"]["content"]

    try:
        # Proviamo a convertire la risposta in dizionario Python
        return json.loads(content)

    except json.JSONDecodeError:
        # Se Ollama non risponde con JSON valido, torniamo un errore controllato
        return {
            "intent": "unknown",
            "items": [],
            "target_location": None,
            "amount_fraction": None,
            "question": user_text,
            "confidence": 0.0,
            "raw_response": content,
        } 