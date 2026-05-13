import json
import os

#import for llama3.2-vision
import base64


import httpx
from dotenv import load_dotenv
from .prompt import SYSTEM_PROMPT
from .prompt import RECEIPT_VISION_PROMPT


# Carica le variabili dal file .env
load_dotenv()


# URL dell'API di Ollama
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")

# Modello Ollama da usare
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_MODEL_VISION = os.getenv("OLLAMA_MODEL_VISION", "llama3.2-vision")


# Prompt principale: spiega all'LLM cosa deve fare

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
        
        
        
async def interpret_receipt_image(image_path: str) -> dict:

    model = os.getenv("OLLAMA_MODEL_VISION")
    url = os.getenv("OLLAMA_URL")
    
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    payload = {
        "model": model,
        "format": "json",
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": RECEIPT_VISION_PROMPT,
                "images": [image_base64],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()

    data = response.json()
    content = data["message"]["content"]

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "intent": "unknown",
            "items": [],
            "raw_response": content,
        }