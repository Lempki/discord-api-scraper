# discord-api-scraper

This is a REST API that performs web scraping on behalf of Discord bots. It accepts a URL and a set of CSS or XPath selectors, runs a [Scrapy](https://scrapy.org/) spider in an isolated subprocess, and returns structured data as JSON. Bots call this API to retrieve content from external websites such as news feeds, game scores, or any other structured page without bundling a scraping stack locally. This project is based on the [discord-api-template](https://github.com/Lempki/discord-api-template) repository, which provides the core architecture.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/scrape` | Start a scrape job for a single URL. Returns a job ID immediately. |
| `POST` | `/scrape/batch` | Start scrape jobs for multiple URLs at once. Returns a job ID for each. |
| `GET` | `/scrape/{job_id}` | Poll the status and results of a previously submitted job. |
| `GET` | `/health` | Returns the service name and version. Used for uptime monitoring. |

All endpoints except `/health` require a bearer token in the `Authorization` header.

### POST /scrape

```json
{
  "url": "https://yle.fi/uutiset",
  "selectors": {
    "title": "h3.card__heading",
    "link": "a.card__link[href]"
  },
  "selector_type": "css",
  "follow_links": false,
  "max_items": 20,
  "encoding_hint": "utf-8"
}
```

`selector_type` accepts `"css"` or `"xpath"`. The response includes a `job_id` and an initial `status` of `"pending"` or `"running"`. Poll `GET /scrape/{job_id}` until the status is `"complete"` or `"failed"`.

### POST /scrape/batch

Accepts the same fields as `/scrape` except `url` is replaced with `urls`, a list of up to 20 URLs. Each URL gets its own job and its own `job_id` in the response array.

### GET /scrape/{job_id}

Returns the job status and, once complete, the scraped items.

```json
{
  "job_id": "...",
  "status": "complete",
  "url": "https://yle.fi/uutiset",
  "scraped_at": "2026-04-18T14:30:00",
  "item_count": 12,
  "items": [
    { "title": ["Uutinen 1"], "link": ["/uutiset/3-12345"] }
  ]
}
```

Completed jobs are kept in memory for one hour by default, then evicted.

## Prerequisites

* [Docker](https://docs.docker.com/get-docker/) and Docker Compose.

Running without Docker requires Python 3.12 or newer.

## Setup

Copy the environment template and fill in the required values:

```bash
cp .env.example .env
```

Start the service:

```bash
docker-compose up --build
```

The API listens on port `8003` by default.

To run without Docker:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn scraper_api.main:app --port 8003
```

## Configuration

All configuration is read from environment variables or from a `.env` file in the project root.

| Variable | Required | Default | Description |
|---|---|---|---|
| `DISCORD_API_SECRET` | Yes | — | Shared bearer token. All Discord bots must send this value in the `Authorization` header. |
| `LOG_LEVEL` | No | `INFO` | Log verbosity. Accepts standard Python logging levels. |
| `SCRAPER_MAX_ITEMS` | No | `100` | Upper limit on items returned per job regardless of what the request specifies. |
| `SCRAPER_JOB_TTL` | No | `3600` | How long completed job results are kept in memory before being evicted, in seconds. |
| `SCRAPER_USER_AGENT` | No | `discord-api-scraper/1.0` | The User-Agent string sent with all scrape requests. |

## Notes on site compatibility

Scrapy respects `robots.txt` by default. Sites that block scrapers via `robots.txt` will not be crawled. The `SCRAPER_USER_AGENT` variable can be used to identify requests from your deployment.

Each scrape job runs Scrapy in a separate subprocess. This isolates the Twisted reactor that Scrapy uses internally from the FastAPI event loop. Jobs time out after 60 seconds.

## Project structure

```
discord-api-scraper/
├── src/scraper_api/
│   ├── main.py                 # FastAPI application and route definitions.
│   ├── config.py               # Environment variable reader.
│   ├── auth.py                 # Bearer token dependency.
│   ├── models.py               # Pydantic request and response models.
│   ├── jobs.py                 # In-memory job store with TTL eviction.
│   ├── runner.py               # Scrapy subprocess launcher.
│   └── spiders/
│       └── generic_spider.py   # Reusable Scrapy spider driven by selector config.
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```
