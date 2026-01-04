# 🐦 Twitter SaaS Idea Finder

Twitter'dan (X) validated SaaS fikirlerini bulan, analiz eden ve skorlayan bir microservice.

## ✨ Features

- 🔍 Twitter'dan MRR/ARR/Revenue içeren tweet'leri toplama
- 💰 MRR/ARR/Revenue rakamlarını otomatik parse etme
- 🔗 Ürün URL'lerini çıkarma ve doğrulama
- 📊 4 filtreli scoring sistemi (Traction, Growth, Traffic, Simplicity)
- 💾 PostgreSQL ile persistent storage
- 🌐 FastAPI REST API + Next.js Dashboard
- ⏰ Celery ile scheduled scraping (30 dakikada bir)
- 🐳 Docker Compose ile tam stack deployment
- 🌸 Flower ile Celery monitoring

## 📁 Project Structure

```
├── saas_finder/           # Main Python package
│   ├── api.py             # FastAPI application
│   ├── celery_app.py      # Celery configuration & schedules
│   ├── config.py          # Configuration management
│   ├── finder.py          # Main finder logic
│   ├── tasks.py           # Celery tasks
│   ├── extractors/        # Revenue & URL extraction
│   ├── parsers/           # MRR/URL parsing
│   ├── scoring/           # Idea scoring system
│   ├── storage/           # Database models & operations
│   └── twitter/           # Twitter scraping clients
│       └── scrapers/      # Apify, twscrape clients
├── config/                # Configuration files
│   ├── accounts.txt       # Twitter credentials (gitignored)
│   └── accounts.txt.example
├── docker/                # Docker configuration
│   └── Dockerfile         # Python services image
├── scripts/               # Utility scripts
│   ├── analyze_tweets.py  # CLI for tweet analysis
│   ├── seed_data.py       # Seed sample data
│   └── migrate_to_postgres.py
├── tests/                 # Test suite
├── web/                   # Next.js frontend dashboard
│   ├── Dockerfile         # Next.js standalone build
│   └── src/app/           # React components
├── data/                  # Data output directory
├── docker-compose.yml     # Full stack orchestration
└── requirements.txt       # Python dependencies
```

## 🛠 Tech Stack

| Component       | Technology                    |
| --------------- | ----------------------------- |
| Language        | Python 3.11+                  |
| Primary Scraper | Apify (apidojo/tweet-scraper) |
| Database        | PostgreSQL 16                 |
| Cache/Broker    | Redis 7                       |
| Task Queue      | Celery                        |
| API             | FastAPI                       |
| Frontend        | Next.js 14                    |
| Monitoring      | Flower                        |
| Container       | Docker Compose                |

## 🚀 Quick Start with Docker

```bash
# 1. Clone repository
git clone <repo>
cd space

# 2. Environment variables
cp .env.example .env
# Edit .env and add APIFY_API_TOKEN

# 3. Start all services (7 containers)
docker compose up -d

# 4. Check status
docker compose ps

# 5. View API logs
docker compose logs -f api
```

### Services & Ports

| Service       | Port | Description               |
| ------------- | ---- | ------------------------- |
| postgres      | 5432 | PostgreSQL database       |
| redis         | 6379 | Message broker & cache    |
| api           | 8000 | FastAPI backend           |
| web           | 3000 | Next.js dashboard         |
| flower        | 5555 | Celery monitoring UI      |
| celery_worker | -    | Background task processor |
| celery_beat   | -    | Scheduled task runner     |

## 🔑 API Keys Setup

### Apify (Required)

1. Sign up at [apify.com](https://apify.com)
2. Subscribe to [apidojo/tweet-scraper](https://apify.com/apidojo/tweet-scraper)
3. Get your API token from Settings
4. Add to `.env`:

```
APIFY_API_TOKEN=apify_api_xxx
```

## 📡 API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Scraper status
curl http://localhost:8000/api/scraper/status

# List all ideas
curl "http://localhost:8000/api/ideas?limit=10"

# Dashboard stats
curl http://localhost:8000/api/stats

# Manual scrape with specific queries
curl -X POST http://localhost:8000/api/scraper/search \
  -H "Content-Type: application/json" \
  -d '{"queries": ["\"$5k MRR\"", "\"$10k MRR\""], "limit_per_query": 20, "min_mrr": 0}'

# Trigger background scrape
curl -X POST http://localhost:8000/api/scraper/trigger
```

## ⏰ Scheduled Tasks

| Task                | Schedule          | Description                         |
| ------------------- | ----------------- | ----------------------------------- |
| scan_revenue_tweets | Every 30 min      | Scans for MRR/ARR tweets            |
| scan_hashtags       | Every hour        | Scans #buildinpublic, #indiehackers |
| deep_scan           | Daily 3 AM        | Deep scan across all queries        |
| rescore_ideas       | Every 6 hours     | Updates idea scores                 |
| cleanup_old_data    | Weekly (Sun 4 AM) | Cleans old data                     |

## 📊 Revenue Detection Patterns

The system automatically detects:

- `$10,000 MRR` / `$10K MRR`
- `$50,000 ARR` / `$50K ARR`
- `$5,000/month` / `$5K per month`
- `"hit $10K"` / `"crossed $50,000"`
- `"5 figure MRR"` / `"6 figure revenue"`
- Stripe screenshot indicators

## 🧪 Running Tests

```bash
# Using Docker
docker compose exec api pytest tests/ -v

# Or locally
pytest tests/ -v --cov=saas_finder
```

## 📋 VS Code Tasks

The project includes pre-configured VS Code tasks:

- **Start Docker Services** - `docker compose up -d`
- **Start API Server** - Local uvicorn server
- **Run Tests** - pytest with verbose output
- **Analyze Tweets** - Run tweet analysis script
- **Seed Sample Data** - Populate database with samples
- **Check Scraper Status** - Query API for scraper health

## 🔧 Environment Variables

```bash
# Required
APIFY_API_TOKEN=apify_api_xxx

# Database (defaults work with Docker)
DATABASE_URL=postgresql://saas_finder:saas_finder@postgres:5432/saas_finder
REDIS_URL=redis://redis:6379/0

# Optional
MIN_MRR_THRESHOLD=500
MAX_TWEETS_PER_QUERY=100
SCRAPE_INTERVAL_HOURS=4
```

## 📝 License

MIT
