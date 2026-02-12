# AutoRia Scraper

An asynchronous web scraper for collecting car listings from **auto.ria.com** with automatic storage in PostgreSQL, database migrations via Alembic, and containerized execution using Docker.

---

## 🚀 Features

* Asynchronous scraping of listing pages
* Anti-blocking protection (random delays + retries)
* Duplicate prevention (URL uniqueness)
* Bulk inserts into PostgreSQL
* Structured logging
* Automatic database migrations
* Dockerized environment
* Scheduler support for timed execution

---

## 🧱 Tech Stack

* Python 3.13+
* aiohttp
* BeautifulSoup4
* SQLAlchemy (Async ORM)
* PostgreSQL
* Alembic
* Docker + Docker Compose

---

## 📁 Project Structure

```
project/
│
├── src/
│   ├── scraper.py
│   ├── main.py
│   ├── models/
│   ├── utils/
│   └── settings.py
│
├── migrations/
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```

---

## ⚙️ Environment Variables

Create a `.env` file in the project root:

```
POSTGRESQL_DSN=postgresql+asyncpg://postgres:postgres@db:5432/autoria
START_URL=https://auto.ria.com/uk/car/used/
SCRAPE_TIME=12:00
```

---

## 🐳 Run with Docker

### First run

```
docker compose up --build
```

### Run in background

```
docker compose up -d --build
```

---

## 🗄 Database Migrations

Migrations are executed automatically through the **migrations service**.

Manual run:

```
docker compose run --rm migrations
```

Check migration status:

```
docker exec -it autoria_db psql -U postgres -d autoria
SELECT * FROM alembic_version;
```

---

## 📊 Check Database Records

```
docker exec -it autoria_db psql -U postgres -d autoria
SELECT COUNT(*) FROM car;
```

---

## 🧪 Logs

```
docker compose logs -f app
docker compose logs -f migrations
docker compose logs -f db
```

---

## 🛑 Stop Services

```
docker compose down
```

Reset database completely:

```
docker compose down -v
```

---

## ⚠️ Technical Notes

* AutoRia is a SPA website → many fields are stored inside JSON state, not static HTML
* Scraper uses randomized delays and retry logic to avoid blocking
* Table must contain a UNIQUE constraint on `url`
* Docker environment uses internal hostname `db` instead of `localhost`

---

## 📈 Container Startup Flow

```
Postgres
   ↓
Migrations
   ↓
Application
```

The app will not start until migrations finish successfully.

---

## 🧠 Performance Optimizations

The scraper implements:

* concurrency limiting via semaphore
* retry strategy with backoff
* randomized request delay
* async HTTP requests
* async database driver
* bulk insert operations

---

## 🧾 Data Model

| Field          | Type     |
| -------------- | -------- |
| url            | string   |
| title          | string   |
| price_usd      | integer  |
| odometer       | integer  |
| username       | string   |
| phone_number   | string   |
| image_url      | string   |
| images_count   | integer  |
| car_number     | string   |
| car_vin        | string   |
| datetime_found | datetime |

---

## 🏗 Architecture Overview

```
Scraper → Parser → Validation → Database → Scheduler
```

**Flow explanation**

1. Scraper loads listing page
2. Extracts car URLs
3. Fetches each car page asynchronously
4. Parses data
5. Filters duplicates
6. Inserts batch into DB

---

## 🔒 Anti-Blocking Strategy

The scraper reduces detection risk using:

* randomized delays
* realistic headers
* retry with exponential backoff
* limited concurrency
* human-like request pattern

---

## 🧪 Development Mode (without Docker)

```
pip install -r requirements.txt
alembic upgrade head
python -m src.main
```

---

## 🧩 Troubleshooting

### Database connection fails

Check `.env` DSN and container logs.

### Tables missing

Run:

```
docker compose run --rm migrations
```

### Port already in use

Remove port mapping from Postgres or change host port.

---

## 👨‍💻 Author

Roman Popov
