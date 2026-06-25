# KaraKaja — Live Auction Marketplace

![Status](https://img.shields.io/badge/status-in--progress-yellow)
![Phase](https://img.shields.io/badge/phase-6.7%20complete-blue)

A production-oriented live auction marketplace where users can list items, place bids in real time, and transact securely through a built-in wallet and escrow system. Built as a full-stack project following a structured phase-by-phase development approach.

---

## Tech Stack

**Backend**
- Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Alembic
- Celery + Redis (background tasks, scheduled jobs)
- Cloudinary (image storage)
- Paystack (payment gateway)
- fastapi-mail + SMTP (email notifications)
- Docker + Docker Compose

**Frontend**
- React 18, Vite
- React Router v7, React Query v5, Zustand
- React Hook Form + Zod
- Bootstrap 5, react-icons
- Axios

---

## Project Structure

```
/
├── backend/        # FastAPI application, Celery workers, DB migrations
├── frontend/       # React SPA
└── README.md
```

---

## Documentation

- [Backend README](./backend/README.md)
- [Frontend README](./frontend/README.md)

---

## Development Phases

| Phase | Description | Status |
|-------|-------------|--------|
| Pre-Phase | Repository & Deployment Foundation | ✅ Done |
| 6.1 | Developer Environment | ✅ Done |
| 6.2 | Database Foundation | ✅ Done |
| 6.3 | Application Foundation | ✅ Done |
| 6.4 | Authentication Module | ✅ Done |
| 6.5 | Users & Profiles Module | ✅ Done |
| 6.6 | Wallet Module | ✅ Done |
| 6.7 | Auctions & Items Module | ✅ Done |
| 6.8 | Bidding + Real-Time | ⏳ Next |
| 6.9 | Orders, Escrow & Disputes | ⏳ Planned |
| 6.10 | Notifications | ⏳ Planned |
| 6.11 | Admin Panel | ⏳ Planned |
| 6.12 | Testing Strategy | ⏳ Planned |
| 6.13 | Production Hardening & Deployment | ⏳ Planned |

---

## Key Features (Implemented)

- JWT authentication with access/refresh token rotation
- Email verification and password reset flows
- Seller registration and admin verification workflow
- Wallet system — fund via Paystack, withdraw via bank transfer, pessimistic locking on balance operations
- Auction creation — multi-step flow (item → images → settings → publish)
- Cloudinary image uploads with validation (type, size)
- Category-filtered, sortable auction browse
- Auction detail with live countdown timer
- Celery Beat settlement — automatically settles ended auctions every 60 seconds, creates Order and Escrow records, moves funds
- Seller dashboard with stats and auction management

---

## Getting Started

See [Backend README](./backend/README.md) and [Frontend README](./frontend/README.md) for setup instructions.
