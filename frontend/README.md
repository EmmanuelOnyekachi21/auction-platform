# KaraKaja Frontend

React SPA for the KaraKaja live auction marketplace. Provides the full user-facing interface — authentication, wallet management, auction browsing, bidding, and seller tools.

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| React 18 | UI framework |
| Vite | Build tool and dev server |
| React Router v7 | Client-side routing |
| React Query v5 | Server state management and caching |
| Zustand | Client state (auth, user session) |
| React Hook Form + Zod | Form handling and validation |
| Axios | HTTP client |
| Bootstrap 5 | Utility CSS |
| react-icons | Icon library (Feather icons) |

---

## Project Structure

```
frontend/src/
├── api/                    # API call functions
│   ├── client.js           # Axios instance with auth interceptors
│   ├── auctions.js         # Auction and category API calls
│   └── wallet.js           # Wallet API calls
├── components/
│   ├── auctions/
│   │   └── AuctionCard.jsx # Reusable auction listing card
│   ├── common/
│   │   ├── Toast.jsx       # Toast notification system
│   │   ├── ProtectedRoute.jsx
│   │   └── PublicRoute.jsx
│   └── layout/
│       ├── MainLayout.jsx  # App shell with navbar and footer
│       ├── AuthLayout.jsx  # Centered card layout for auth pages
│       └── Navbar.jsx      # Top navigation bar
├── pages/
│   ├── auth/               # Login, Register, VerifyEmail, ResetPassword
│   ├── profile/            # MyProfile, BecomeSeller, PublicProfile
│   ├── wallet/             # WalletPage, TransactionsPage, PaymentConfirmPage
│   ├── auctions/           # HomePage (browse), AuctionDetailPage
│   ├── seller/             # SellerDashboard, CreateAuctionPage, SellerPending
│   └── admin/              # VerifySellersPage
├── store/
│   └── authStore.js        # Zustand store for auth state
├── App.jsx                 # Route definitions
└── main.jsx                # Entry point
```

---

## Prerequisites

- Node.js 18+
- npm or yarn
- Backend running on `http://localhost:8000`

---

## Local Setup

**1. Navigate to frontend directory**
```bash
cd frontend
```

**2. Install dependencies**
```bash
npm install
```

**3. Create environment file**
```bash
cp .env.example .env
```

Or create `.env` manually:
```env
VITE_API_URL=http://localhost:8000/api/v1
```

**4. Start development server**
```bash
npm run dev
```

App runs at http://localhost:5173

---

## Available Scripts

```bash
npm run dev        # Start dev server with hot reload
npm run build      # Production build to /dist
npm run preview    # Preview production build locally
```

---

## Pages & Routes

### Public Routes (no auth required)
| Route | Page | Description |
|-------|------|-------------|
| `/` | HomePage | Browse active auctions, category filters, sort |
| `/auctions` | HomePage | Same as `/` |
| `/auctions/:id` | AuctionDetailPage | Full auction detail, countdown, bid history |
| `/users/:id` | PublicProfilePage | Public seller profile |
| `/login` | LoginPage | Email/password login |
| `/register` | RegisterPage | New account registration |
| `/verify-email` | VerifyEmailPage | Email verification via token |
| `/reset-password` | ResetPasswordPage | Password reset |

### Protected Routes (auth required)
| Route | Page | Description |
|-------|------|-------------|
| `/dashboard` | Dashboard | Quick actions home |
| `/profile` | MyProfilePage | Edit profile, bank details |
| `/become-seller` | BecomeSellerPage | Seller registration form |
| `/seller/pending` | SellerPendingPage | Verification status page |
| `/seller/dashboard` | SellerDashboardPage | Auction stats, manage listings |
| `/seller/create-auction` | CreateAuctionPage | 4-step auction creation wizard |
| `/wallet` | WalletPage | Balance, fund, withdraw |
| `/wallet/transactions` | TransactionsPage | Transaction history |
| `/payment/:id/confirm` | PaymentConfirmPage | Post-payment confirmation |
| `/admin/verify-sellers` | VerifySellersPage | Admin seller verification |

---

## Key Components

### AuctionCard
Reusable card used on the homepage and seller dashboard. Reads from the API response structure:
- Primary image from `auction.items[0].item.images`
- Title from `auction.title` or `auction.items[0].item.title`
- Condition and category from `auction.items[0].item`
- Current bid from `auction.highest_bid.amount`
- Starting price from `auction.items[0].starting_price`
- Countdown from `auction.ends_at`

### CreateAuctionPage (4-step wizard)
1. **Item Details** — title, category, condition, description, weight, dimensions → `POST /items`
2. **Upload Images** — drag-and-drop, up to 8 images, primary selection → `POST /items/{id}/images`
3. **Auction Settings** — start/end dates, bid increment, reserve price → `POST /auctions` then `POST /auctions/{id}/items`
4. **Review & Publish** — summary card → `PATCH /auctions/{id}/publish`

### Navbar
Context-aware navigation:
- Shows wallet balance for authenticated users
- Shows "Seller Dashboard" for verified sellers, "Become a Seller" for others
- Admin link visible only to admin role users

---

## State Management

**Zustand (`authStore`)** — persists across page refreshes:
- `user` — current user object
- `accessToken` / `refreshToken`
- `isAuthenticated`
- `setAuth()`, `logout()`, `updateUser()`

**React Query** — server state:
- Auction lists with 30-second refetch intervals
- Wallet balance
- Categories (5-minute stale time)
- Automatic background refetching

**Axios interceptors** (`api/client.js`):
- Attaches `Authorization: Bearer <token>` to every request
- On 401 response, automatically attempts token refresh
- On refresh failure, logs user out

---

## Deployment

The frontend is deployed on **Vercel**. The `vercel.json` configures SPA routing:

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/" }]
}
```

Set `VITE_API_URL` in Vercel environment variables to point to your production backend URL.

```bash
npm run build   # outputs to /dist
```
