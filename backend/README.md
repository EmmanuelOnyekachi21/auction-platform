# KaraKaja Backend

FastAPI-based REST API for the KaraKaja live auction marketplace. Handles authentication, user profiles, wallet operations, auction lifecycle, image uploads, payment processing, and background job scheduling.

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.12 | Runtime |
| FastAPI | Web framework |
| SQLAlchemy 2.0 (async) | ORM |
| PostgreSQL 15 | Primary database |
| Alembic | Database migrations |
| Redis 7 | Message broker + Celery backend |
| Celery | Background task queue |
| Cloudinary | Image storage |
| Flutterwave | Payment gateway |
| fastapi-mail | Email delivery |
| Docker + Docker Compose | Local development environment |

---

## Project Structure

```
backend/
├── apps/
│   ├── authentication/     # JWT auth, login, register, token refresh
│   ├── users/              # User profiles, seller registration, admin verification
│   ├── wallet/             # Wallet balance, funding, withdrawals, transactions
│   ├── payments/           # Flutterwave integration, webhook handling
│   ├── auctions/           # Items, categories, auctions, Cloudinary, settlement tasks
│   ├── bids/               # Bid models and enums (Phase 6.8)
│   ├── orders/             # Order models (Phase 6.9)
│   ├── escrow/             # Escrow models (Phase 6.9)
│   ├── disputes/           # Dispute models (Phase 6.9)
│   ├── notifications/      # Email notification tasks
│   └── realtime/           # WebSocket infrastructure (Phase 6.8)
├── common/                 # Shared utilities: exceptions, pagination, middleware, schemas
├── config/                 # Settings, database, Celery, logging, model registry
├── alembic/                # Database migration scripts
├── scripts/                # Seed scripts (categories, etc.)
├── tests/                  # Test suite
├── logs/                   # Application logs
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── main.py                 # FastAPI app entry point
```

---

## Architecture

The backend follows a layered architecture:

```
Router → Service → Repository → Database
```

- **Routers** handle HTTP concerns only (request parsing, auth dependencies, response codes)
- **Services** contain all business logic and orchestration
- **Repositories** contain all database queries (SQLAlchemy)
- **Models** define ORM schema
- **Schemas** define Pydantic request/response contracts

---

## Prerequisites

- Docker and Docker Compose
- Python 3.12 (for running scripts outside Docker)

---

## Local Setup

**1. Clone and navigate**
```bash
git clone <repo-url>
cd backend
```

**2. Copy environment file**
```bash
cp .env.example .env
```

**3. Fill in `.env`**

Key variables:
```env
DATABASE_URL=postgresql+asyncpg://auction:auction@db:5432/auction_dev
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
CLOUDINARY_UPLOAD_PRESET=auction_items
FLUTTERWAVE_SECRET_KEY=your_flw_secret
FLUTTERWAVE_PUBLIC_KEY=your_flw_public
FLUTTERWAVE_WEBHOOK_SECRET=your_webhook_secret
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_FROM=your@gmail.com
FRONTEND_URL=http://localhost:5173
SERVER_URL=http://localhost:8000
APP_URL=http://localhost:5173
```

**4. Start all services**
```bash
docker-compose up --build
```

This starts:
- `app` — FastAPI on port 8000
- `db` — PostgreSQL on port 5432
- `redis` — Redis on port 6379
- `celery_worker` — Celery task worker
- `celery_beat` — Celery periodic task scheduler

**5. Run migrations**
```bash
docker-compose exec app alembic upgrade head
```

**6. Seed categories**
```bash
docker-compose exec app python scripts/seed_categories.py
```

---

## API Documentation

With the server running, visit:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

---

## API Overview

### Authentication — `/api/v1/auth`
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register new user |
| POST | `/login` | Login, returns JWT tokens |
| POST | `/refresh` | Refresh access token |
| POST | `/verify-email` | Verify email with token |
| POST | `/forgot-password` | Request password reset |
| POST | `/reset-password` | Reset password with token |

### Users — `/api/v1/users`
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/me` | Get current user profile |
| PATCH | `/me` | Update profile |
| POST | `/me/seller` | Register as seller |
| GET | `/sellers/pending` | List pending sellers (admin) |
| PATCH | `/{id}/seller-profile/verify` | Verify/reject seller (admin) |

### Wallet — `/api/v1/wallets`
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/me` | Get wallet balance |
| POST | `/fund` | Initiate Flutterwave payment |
| POST | `/webhook` | Flutterwave webhook handler |
| POST | `/withdraw` | Request withdrawal |
| GET | `/transactions` | Transaction history (paginated) |

### Auctions — `/api/v1`
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/categories` | List all categories |
| POST | `/items` | Create item |
| POST | `/items/{id}/images` | Upload item image |
| DELETE | `/items/{id}/images/{img_id}` | Delete item image |
| PATCH | `/items/{id}` | Update item |
| DELETE | `/items/{id}` | Delete item |
| GET | `/users/me/items` | Seller's items (paginated) |
| PATCH | `/admin/items/{id}/approve` | Approve item (admin) |
| PATCH | `/admin/items/{id}/reject` | Reject item (admin) |
| GET | `/admin/items/pending` | Pending items (admin) |
| GET | `/auctions` | Browse active auctions |
| GET | `/auctions/{id}` | Auction detail |
| POST | `/auctions` | Create auction (draft) |
| POST | `/auctions/{id}/items` | Attach item to auction |
| PATCH | `/auctions/{id}/publish` | Publish auction |
| PATCH | `/auctions/{id}` | Update draft auction |
| DELETE | `/auctions/{id}` | Cancel auction |
| GET | `/users/me/auctions` | Seller's auctions (paginated) |

---

## Background Jobs

### Celery Beat Schedule
| Task | Schedule | Description |
|------|----------|-------------|
| `settle_ended_auctions` | Every 60 seconds | Finds ended auctions and queues settlement |

### Settlement Flow
1. `settle_ended_auctions` — queries `status=ACTIVE AND ends_at <= now()`
2. For each auction, calls `claim_for_settlement` (atomic UPDATE, idempotency guard)
3. Dispatches `process_auction_settlement` per claimed auction
4. `process_auction_settlement` — if no bids: marks `ENDED_NO_BIDS`, returns items to `APPROVED`. If bids exist: creates Order, creates Escrow, moves winner's locked funds to escrow, marks bids won/lost, marks items sold, marks auction `SETTLED`, sends notifications.

---

## Useful Commands

```bash
# View logs
docker-compose logs -f app
docker-compose logs -f celery_worker

# Run tests
docker-compose exec app pytest

# Create a new migration
docker-compose exec app alembic revision --autogenerate -m "description"

# Apply migrations
docker-compose exec app alembic upgrade head

# Rollback one migration
docker-compose exec app alembic downgrade -1

# Open a DB shell
docker-compose exec db psql -U auction -d auction_dev

# Restart a single service
docker-compose restart celery_worker
```

---

## Environment Variables Reference

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL async connection string |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | JWT signing secret |
| `ALGORITHM` | JWT algorithm (default: HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary account cloud name |
| `CLOUDINARY_API_KEY` | Cloudinary API key |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret |
| `CLOUDINARY_UPLOAD_PRESET` | Cloudinary upload preset name |
| `FLUTTERWAVE_SECRET_KEY` | Flutterwave secret key |
| `FLUTTERWAVE_PUBLIC_KEY` | Flutterwave public key |
| `FLUTTERWAVE_WEBHOOK_SECRET` | Webhook verification secret |
| `MAIL_SERVER` | SMTP server host |
| `MAIL_PORT` | SMTP port (587 for TLS) |
| `MAIL_USERNAME` | SMTP username |
| `MAIL_PASSWORD` | SMTP password / app password |
| `MAIL_FROM` | Sender email address |
| `FRONTEND_URL` | Frontend base URL (for redirects) |
| `SERVER_URL` | Backend base URL |
| `APP_URL` | App URL used in email links |
| `CORS_ORIGINS` | Comma-separated allowed origins |
