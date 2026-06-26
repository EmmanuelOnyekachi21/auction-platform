# KaraKaja Production Smoke Test

Run this checklist before every production deployment and after every merge to `main`.

This document defines "working." If all items pass, the platform is ready for users.

---

## Authentication

- [ ] Register new account
- [ ] Verification email received
- [ ] Email verified successfully
- [ ] Login returns valid tokens
- [ ] Token refresh works
- [ ] Logout invalidates token

---

## Wallet

- [ ] Wallet balance shows correctly
- [ ] Fund wallet via Paystack test mode
- [ ] Balance updates after payment
- [ ] Transaction appears in history
- [ ] Tier 1 withdrawal blocked
- [ ] BVN verification upgrades to Tier 2
- [ ] Withdrawal succeeds after Tier 2

---

## Auctions

- [ ] Create item with images
- [ ] Create auction with duration pill
- [ ] Attach item to auction
- [ ] Set reserve price
- [ ] Publish auction
- [ ] Auction appears in browse page
- [ ] Reserve met indicator shows correctly

---

## Bidding

- [ ] Place bid locks correct funds
- [ ] Outbid unlocks previous bidder funds
- [ ] Below minimum bid rejected
- [ ] Seller cannot bid own auction
- [ ] KYC tier limit enforced on bid

---

## Settlement

- [ ] Auction ends and settles correctly
- [ ] Order created with correct amounts
- [ ] Escrow funded correctly
- [ ] Commission calculated correctly (5%)
- [ ] Winner and seller notified

---

## Orders

- [ ] Seller marks as shipped
- [ ] Buyer confirms delivery
- [ ] Escrow releases to seller
- [ ] Commission deducted correctly
- [ ] Auto-release after 48 hours

---

## Disputes

- [ ] Buyer raises dispute
- [ ] Evidence submitted
- [ ] Admin resolves in buyer favour
- [ ] Buyer refunded correctly
- [ ] Admin resolves in seller favour
- [ ] Seller paid correctly

---

## Admin

- [ ] Admin panel accessible
- [ ] User management working
- [ ] Item approval working
- [ ] Dispute resolution working
- [ ] Financial audit read-only

---

## Infrastructure

- [ ] `/health` endpoint returns 200
- [ ] Database connection verified
- [ ] Redis connection verified
- [ ] Celery worker processing tasks
- [ ] Celery beat scheduling tasks
- [ ] Logs appearing correctly
- [ ] Sentry capturing errors (if configured)

---

## Performance

- [ ] Browse auctions page loads < 2 seconds
- [ ] Auction detail page loads < 1 second
- [ ] Bid placement completes < 1 second
- [ ] Wallet funding flow completes within 30 seconds

---

## Notes

- Run this on **production** with real (test-mode) payment credentials
- Use a fresh test account each time — don't reuse old test data
- Document any failures in GitHub Issues immediately
- After fixing, re-run the full checklist from the top
- This checklist grows as new features are added

Last updated: 2026-06-25
