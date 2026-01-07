# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a high-performance URL shortener service built with Flask, PostgreSQL, and Redis. The architecture is designed for speed and scalability with a two-tier caching strategy and buffered analytics writes.

## Core Architecture

### Database Models (models.py)

Two main tables work together:

- `Url`: Stores shortened URL mappings with id, code (base62 or custom alias), original_url, created_at, expires_at, and is_active
- `URLStats`: Aggregates click counts per URL with url_id (FK to urls.id), total_clicks, and last_flushed

### Two-Tier Performance Strategy

**Redis Cache Layer (cache.py)**:
- Code-to-URL lookups are cached in Redis with configurable TTL (default 3600s)
- Cache key format: `code:{short_code}` stores JSON payload with url_id, original_url, expires_at, is_active
- Click increments are buffered in Redis hash `clicks` with url_id as key
- Set `clicks_pending` tracks which url_ids have pending buffered counts

**Analytics Buffer Pattern**:
- Clicks are first incremented in Redis (`increment_click_redis`) to avoid DB write on every redirect
- A background job (not included in this repo) periodically calls `read_and_clear_clicks_atomic()` to flush buffered counts to `URLStats` table
- This pattern dramatically reduces database write load on hot URLs

### URL Resolution Flow (app.py:110-147)

The `/<code>` endpoint implements a fast-path/cold-path pattern:

1. **Fast path**: Check Redis cache for code. If hit and valid, increment Redis buffer and redirect immediately
2. **Cold path**: On cache miss, query database, populate cache, increment buffer, then redirect
3. Expiry checks happen in both paths before redirecting

### Code Generation (utils.py)

- Auto-generated codes use base62 encoding (`encode_base62`) of the database ID
- Custom aliases are validated: alphanumeric, max 32 chars, stored directly as code
- Base62 alphabet: `0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ`

### URL Normalization (utils.py:23-40)

`normalize_url()` canonicalizes URLs before storage:
- Enforces http/https schemes only
- Lowercases hostname
- Strips default ports (:80 for http, :443 for https)
- Removes utm_* tracking parameters from query string

## Development Commands

### Environment Setup

```bash
# Activate virtual environment
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Unix/Mac

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Set environment variables (or use .env file with python-dotenv)
export DATABASE_URL="postgresql://user:pass@localhost:5432/urls"
export REDIS_URL="redis://localhost:6379/0"
export HOST="localhost:8000"
export CACHE_TTL="3600"

# Run Flask development server
flask --app app:create_app run
```

### Database Initialization

Database tables are auto-created on first app startup via `init_db()` in the app context. For production, use Alembic migrations (alembic is in requirements but no migrations/ directory exists yet).

## Configuration via Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://postgres:pass@db:5432/urls`)
- `REDIS_URL`: Redis connection string (default: `redis://redis:6379/0`)
- `HOST`: Domain for short URLs in responses (default: `localhost:8000`)
- `CACHE_TTL`: Redis cache TTL in seconds (default: `3600`)

## API Endpoints

### POST /shorten
Creates shortened URL. Request body:
```json
{
  "url": "https://example.com",
  "custom": "optional-alias",
  "expires_at": "2024-12-31T23:59:59"
}
```

Returns `code`, `short_url`, and `qr_base64` (base64-encoded PNG QR code).

### GET /<code>
Redirects to original URL. Returns 302 redirect, 404 if not found, or 410 if expired.

### GET /<code>/qr.png
Returns PNG image of QR code pointing to short URL.

### GET /healthz
Health check endpoint for load balancers (returns "OK" 200).

### GET /stats
Returns `{"total_urls": N, "buffered_clicks": M}` - total URL count and current Redis-buffered click count.

## Key Implementation Details

**Database Session Management**: Sessions are created per-request via `get_session()` and must be explicitly closed. Pattern: get session, use it, close in finally block.

**Custom Alias Flow**: When custom code is provided, it's used directly as the code. For auto-generated codes, a temporary code "tmp" is inserted, then after flush the ID is base62-encoded and updated.

**QR Code Generation**: `qr_png_base64()` returns base64-encoded PNG. The `/qr.png` endpoint decodes this back to bytes for send_file.

**Bug in db.py:7**: `os.environ['DATABASE_URL', ...]` should be `os.environ.get('DATABASE_URL', ...)` - the dict lookup syntax is incorrect and will cause runtime error.
