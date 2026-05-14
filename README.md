# Dispensa Telegram Bot

A Telegram bot for managing a home pantry using natural language, MariaDB, and a local LLM powered by Ollama.

The bot allows users to add, consume, discard, list, and track food products directly from Telegram. It interprets free-text messages such as “I bought milk and pasta”, “I used half of the chicken”, or “What is expiring this week?” and converts them into structured database operations.

This project is designed as a practical example of local AI-assisted automation: a conversational Telegram interface, a relational database, and a local language model working together without relying on external cloud LLM APIs.

---

## Features

- Natural-language pantry management through Telegram
- Local LLM-based intent recognition with Ollama
- MariaDB/MySQL persistence for pantry items
- Automatic shelf-life estimation for common food products
- Expiry-date tracking
- Product consumption and quantity update
- Waste logging for discarded or expired food
- Pantry value estimation based on product price and remaining quantity
- Receipt-image parsing using a vision-capable Ollama model
- Support for multiple storage locations:
  - fridge
  - freezer
  - pantry
  - spices
  - oil
  - bathroom
  - other

---

## Example Interactions

```text
User:
I bought milk, pasta and chicken

Bot:
Products added successfully.
```

```text
User:
What do I have in the fridge?

Bot:
Products found:
- milk - 1 bottle - fridge - expires on 2026-01-14
- chicken - 500 grams - fridge - expires on 2026-01-11
```

```text
User:
I used half of the chicken

Bot:
Updated chicken: from 500 grams to 250 grams.
```

```text
User:
What is expiring this week?

Bot:
Products expiring soon:
- milk - 1 bottle - fridge - expires on 2026-01-14
```

```text
User:
I threw away the fish

Bot:
Registered fish as discarded. Estimated wasted value: €3.20.
```

---

## Project Goals

The goal of this project is to build a practical assistant for domestic food management while exploring a local-first AI architecture.

The bot is intended to help with:

- reducing food waste
- keeping track of products and expiry dates
- estimating the value of available food
- logging discarded items
- interacting with a database using simple natural language
- extracting product information from grocery receipts

From a technical perspective, the project demonstrates how to combine:

- Telegram Bot API
- Python asynchronous handlers
- local LLM inference with Ollama
- structured JSON generation
- MariaDB persistence
- receipt-image interpretation
- rule-based post-processing
- environment-based configuration

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python |
| Bot interface | python-telegram-bot |
| Database | MariaDB / MySQL |
| Database driver | PyMySQL |
| LLM backend | Ollama |
| Text model | llama3.2 or compatible |
| Vision model | llama3.2-vision or compatible |
| HTTP client | httpx |
| Environment variables | python-dotenv |

---

## Repository Structure

```text
dispensa_telegram/
├── main.py
├── requirements.txt
├── src/
│   └── dispensa_bot/
│       ├── bot.py
│       ├── db.py
│       ├── llm.py
│       └── prompt.py
└── tmp/
```

### Main Files

| File | Description |
|---|---|
| `main.py` | Entry point used to start the Telegram bot |
| `src/dispensa_bot/bot.py` | Telegram command and message handlers |
| `src/dispensa_bot/db.py` | Database connection and pantry operations |
| `src/dispensa_bot/llm.py` | Ollama API integration for text and image interpretation |
| `src/dispensa_bot/prompt.py` | System prompts used to force structured JSON output |
| `requirements.txt` | Python dependencies |

---

## How It Works

The application follows a simple processing pipeline.

```text
Telegram message
      |
      v
Python Telegram handler
      |
      v
Ollama local LLM
      |
      v
Structured JSON intent
      |
      v
Python business logic
      |
      v
MariaDB database operation
      |
      v
Telegram response
```

For example, the message:

```text
I bought 1 liter of milk for 1.49 euros
```

can be interpreted as structured JSON:

```json
{
  "intent": "add_items",
  "items": [
    {
      "name": "milk",
      "quantity": 1,
      "unit": "liter",
      "location": "fridge",
      "expiry_date": null,
      "shelf_life_days": 5,
      "price": 1.49,
      "notes": null,
      "amount_fraction": null
    }
  ],
  "target_location": null,
  "amount_fraction": null,
  "days": null,
  "question": null,
  "confidence": 0.95
}
```

The bot then computes the expiry date if needed, stores the product in MariaDB, and sends a confirmation message to the user.

---

## Supported Intents

The LLM prompt is designed to classify user messages into structured intents.

| Intent | Description |
|---|---|
| `add_items` | Add one or more products to the pantry |
| `consume_item` | Reduce the quantity of an existing product |
| `discard_item` | Register a product as discarded or wasted |
| `list_items` | List all available products |
| `list_by_location` | List products in a specific location |
| `expiring_items` | Show products expiring within a given number of days |
| `pantry_value` | Estimate the current value of the pantry |
| `waste_log` | Show recently discarded products |
| `unknown` | Fallback when the message cannot be interpreted reliably |

---

## Database Model

The current implementation expects two main tables:

- `items`
- `waste_log`

A suggested database schema is shown below.

```sql
CREATE TABLE items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    quantity DECIMAL(10, 3) NULL,
    initial_quantity DECIMAL(10, 3) NULL,
    unit VARCHAR(50) NULL,
    location VARCHAR(100) NULL,
    expiry_date DATE NULL,
    notes TEXT NULL,
    price DECIMAL(10, 2) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE waste_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NULL,
    name VARCHAR(255) NOT NULL,
    quantity DECIMAL(10, 3) NULL,
    unit VARCHAR(50) NULL,
    estimated_value DECIMAL(10, 2) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES items(id)
        ON DELETE SET NULL
);
```

---

## Requirements

Before running the bot, make sure you have:

- Python 3.10 or newer
- MariaDB or MySQL
- Ollama installed locally
- A Telegram bot token from BotFather
- At least one Ollama text model
- Optionally, one Ollama vision model for receipt parsing

---

## Installation

Clone the repository:

```bash
git clone https://github.com/mic334/dispensa_telegram.git
cd dispensa_telegram
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file in the project root.

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=dispensa

OLLAMA_URL=http://localhost:11434/api/chat
OLLAMA_MODEL=llama3.2
OLLAMA_MODEL_VISION=llama3.2-vision
```

Do not commit the `.env` file to GitHub.

---

## Ollama Setup

Install Ollama and pull the required models.

For text interpretation:

```bash
ollama pull llama3.2
```

For receipt-image interpretation:

```bash
ollama pull llama3.2-vision
```

Start Ollama:

```bash
ollama serve
```

Depending on your installation, Ollama may already be running as a background service.

You can check the available models with:

```bash
ollama list
```

---

## Database Setup

Create the database:

```sql
CREATE DATABASE dispensa CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then create the required tables using the schema shown in the “Database Model” section.

Make sure the credentials in your `.env` file match your MariaDB or MySQL configuration.

---

## Running the Bot

Start the bot with:

```bash
python main.py
```

If everything is configured correctly, the bot will start polling Telegram updates.

```text
Bot started.
Press CTRL+C to stop.
```

Open Telegram, search for your bot, and send:

```text
/start
```

---

## Available Commands

| Command | Description |
|---|---|
| `/start` | Shows a short introduction and usage examples |

Most interactions are handled through normal text messages rather than explicit commands.

---

## Usage Examples

### Add Products

```text
I bought milk, pasta and chicken
```

```text
Add 6 eggs in the fridge
```

```text
I bought pasta for 0.89 euros
```

```text
Add 1 kg of apples
```

---

### Consume Products

```text
I used half of the chicken
```

```text
I drank one glass of milk
```

```text
I finished the biscuits
```

```text
Use 200 grams of rice
```

---

### List Products

```text
What do I have?
```

```text
Show me everything
```

```text
What is in the fridge?
```

```text
Show products in the freezer
```

---

### Track Expiry Dates

```text
What expires today?
```

```text
What expires tomorrow?
```

```text
What should I consume this week?
```

```text
Show me products expiring in the next 3 days
```

---

### Track Waste

```text
I threw away the milk
```

```text
The fish went bad
```

```text
Show me what I wasted
```

```text
Register the expired yogurt as wasted
```

---

### Estimate Pantry Value

```text
How much is my pantry worth?
```

```text
What is the value of the products?
```

```text
Estimate the value of my food
```

---

### Read a Receipt

Send a photo of a grocery receipt to the bot.

The bot will attempt to extract product names, quantities, units, and prices from the image.

---

## Receipt Parsing

The bot supports receipt-image interpretation through a vision-capable Ollama model.

The receipt parser is designed to:

- extract only food or pantry-related products
- ignore totals, subtotals, VAT, payment methods, discounts, fidelity points, and card information
- return structured JSON
- normalize missing quantities to `1`
- normalize missing units to `piece`
- preserve detected prices when available

Example output:

```json
{
  "intent": "add_items",
  "items": [
    {
      "name": "milk",
      "quantity": 1,
      "unit": "piece",
      "price": 1.49
    },
    {
      "name": "pasta",
      "quantity": 2,
      "unit": "piece",
      "price": 0.89
    }
  ]
}
```

At the current stage, receipt parsing is mainly used to preview the extracted items. A future improvement could add a confirmation workflow before saving them to the database.

---

## Local-First AI Approach

This project uses Ollama to run language models locally.

This approach has several advantages:

- no external LLM API key is required
- user messages are not sent to commercial cloud LLM providers
- the system can be customized with different local models
- prompts can be iterated quickly
- the bot can run on a personal machine or local server

The main trade-off is that response quality depends on the local model used and on the available hardware.

---

## Configuration Reference

| Variable | Description | Example |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token generated by BotFather | `123456:ABC...` |
| `MYSQL_HOST` | MariaDB/MySQL host | `localhost` |
| `MYSQL_PORT` | MariaDB/MySQL port | `3306` |
| `MYSQL_USER` | Database username | `root` |
| `MYSQL_PASSWORD` | Database password | `password` |
| `MYSQL_DATABASE` | Database name | `dispensa` |
| `OLLAMA_URL` | Ollama chat API endpoint | `http://localhost:11434/api/chat` |
| `OLLAMA_MODEL` | Text model used for intent parsing | `llama3.2` |
| `OLLAMA_MODEL_VISION` | Vision model used for receipt parsing | `llama3.2-vision` |

---

## Suggested `.gitignore`

```gitignore
.env
.venv/
__pycache__/
*.pyc
tmp/
.DS_Store
.idea/
.vscode/
```

---

## Current Limitations

This project is under active development and has some known limitations:

- The database schema is not yet provided as a dedicated migration file.
- Receipt parsing currently extracts items but does not implement a full confirmation-and-save workflow.
- User authentication is not yet implemented.
- Destructive actions should require confirmation before execution.
- Matching products by name is approximate and may need improvement.
- Unit normalization is intentionally simple.
- Test coverage is not yet included.
- Docker Compose is not yet provided.

---

## Suggested Improvements

Recommended future improvements:

- Add a `schema.sql` file for database initialization
- Add a `.env.example` file
- Add Docker Compose for MariaDB and the bot
- Add unit tests for:
  - quantity parsing
  - price parsing
  - intent handling
  - database operations
- Add user authorization by Telegram user ID
- Add confirmation for destructive actions
- Add receipt confirmation flow:
  - read receipt
  - show extracted products
  - ask for confirmation
  - save to database
- Add product categories
- Add fuzzy matching for product names
- Add a web dashboard for pantry analytics
- Add export to CSV
- Add statistics on waste and saved value

---

## Development Notes

A suggested development setup could include:

```bash
pip install black ruff pytest
```

Format code:

```bash
black .
```

Lint code:

```bash
ruff check .
```

Run tests:

```bash
pytest
```

These tools are not required by the current version, but they are recommended for future development.

---

## Security Notes

Do not commit secrets to GitHub.

The following values should always remain private:

- Telegram bot token
- database password
- production database credentials
- private server addresses

Use `.env` for local configuration and provide only a sanitized `.env.example` in the repository.

For production or shared usage, it is recommended to add:

- Telegram user ID allowlist
- confirmation for destructive actions
- structured logging
- database backups
- error reporting
- stricter validation of LLM-generated JSON

---

## Troubleshooting

### Missing Telegram Token

If you see an error related to `TELEGRAM_BOT_TOKEN`, check that your `.env` file exists and contains:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

---

### Cannot Connect to MariaDB

Check that:

- MariaDB or MySQL is running
- the database exists
- the user and password are correct
- the port is correct
- the tables have been created

You can test the connection manually with:

```bash
mysql -u your_mysql_user -p -h localhost dispensa
```

---

### Ollama Connection Error

Check that Ollama is running:

```bash
ollama serve
```

Then verify that the configured model is available:

```bash
ollama list
```

If the model is missing, pull it:

```bash
ollama pull llama3.2
```

---

### Vision Model Not Working

Make sure that:

- `OLLAMA_MODEL_VISION` is set in `.env`
- the vision model is installed
- the model supports image input
- the image file is valid and readable

---

## Roadmap

Possible roadmap for future versions:

- [ ] Add `schema.sql`
- [ ] Add `.env.example`
- [ ] Add Docker Compose
- [ ] Add test suite
- [ ] Add user authorization
- [ ] Add receipt confirmation workflow
- [ ] Add product categories
- [ ] Add fuzzy product matching
- [ ] Add CSV export
- [ ] Add pantry statistics
- [ ] Add web dashboard

---

## Author

Developed by [Michele Orza](https://github.com/mic334).

This project combines Python backend development, workflow automation, local LLM integration, and database-driven application design.

---


## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
