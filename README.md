## Running with Docker

The project can be started with Docker Compose using 3 services:

- `bot`: Python Telegram bot
- `mariadb`: pantry database
- `ollama`: local AI model server

### Required structure

```text
dispensa_telegram/
├── Dockerfile
├── docker-compose.yml
├── .env
├── requirements.txt
├── main.py
├── src/
└── database/
    └── schema.sql
```

### `.env` file

Example:

```env
TELEGRAM_BOT_TOKEN=your_token_here

OLLAMA_MODEL=llama3.2
OLLAMA_MODEL_VISION=llama3.2-vision
OLLAMA_URL=http://ollama:11434/api/chat

MYSQL_HOST=mariadb
MYSQL_PORT=3306
MYSQL_USER=dispensa
MYSQL_PASSWORD=dispensa_password
MYSQL_DATABASE=dispensa_db
```

Note: inside Docker, do not use `localhost` for MariaDB or Ollama. Use the Docker service name instead.

### Start the project

Make sure Docker Desktop is running, then from the project root run:

```bash
docker compose up --build
```

To check the running containers:

```bash
docker compose ps
```

You should see these services running:

```text
bot
mariadb
ollama
```

### Download Ollama models

Main text model:

```bash
docker compose exec ollama ollama pull llama3.2
```

Optional vision model for reading images/receipts:

```bash
docker compose exec ollama ollama pull llama3.2-vision
```

The vision model is heavier. If `llama3.2-vision` is not downloaded, the bot can still work with text messages.

### Stop the project

To stop the containers without deleting data and models:

```bash
docker compose down
```

Do not normally use:

```bash
docker compose down -v
```

because `-v` deletes Docker volumes, including the database and downloaded Ollama models.

### Data persistence

MariaDB stores data in this Docker volume:

```text
mariadb_data
```

Ollama stores downloaded models in this Docker volume:

```text
ollama_data
```

This means pantry data and Ollama models remain saved after stopping the containers.
