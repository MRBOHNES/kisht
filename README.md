# Kisht

Kisht is a field collections app for an NBFC in Indore. Each morning, field officers open it on their phone and see which overdue borrowers to visit first and why. They log what happened in three taps, even without network. Branch managers import the daily overdue CSV, see roll rates by branch against a 16% target, and can pin a loan to the top of an officer's list. Officer screens default to Hindi, manager screens to English, with a toggle on every screen.

- App: https://kisht-flame.vercel.app (managers: https://kisht-flame.vercel.app/manager/login)
- API health: https://kisht-api.onrender.com/health

Demo logins: `officer@demo.in` and `manager@demo.in`. Password: see [deployment.md](deployment.md). All data is sample data.

## Core features
- Priority list: a 0-100 risk score from DPD, broken promises, days since payment, unreachable attempts and promises due today, weighted by amount at risk. Each loan shows its top three reasons with points, in Hindi and English.
- Outcome logging in three taps: paid, promise (EMI chips, date defaults to today + 3), not reachable, dispute. GPS when allowed.
- Contact window 08:00-19:00 IST enforced on the server: calls outside it are blocked and every attempt is recorded.
- Promise tracking: kept when paid on time, broken when the date passes without payment.
- Offline: outcomes are saved on the phone first and synced in batches. The server ignores repeats and flags logs made outside contact hours.
- CSV import with per-row errors and fixes, and assignment by pincode and officer workload. Loans missing from the day's file are marked cured.
- Manager dashboard: roll rate by month and branch, broken promises, same-day logging, untouched loans, disputes, and pins with a reason.
- Login with an httpOnly cookie and roles from the account. Officers only see their own loans. Accounts lock for 15 minutes after 5 failed logins.

## Tech stack
- Backend: Python 3.13, FastAPI, SQLAlchemy 2.0 (async, asyncpg), Alembic, Pydantic v2, pytest
- Frontend: Next.js (App Router), TypeScript, Tailwind, IndexedDB, service worker; charts are plain SVG
- Database: PostgreSQL (Neon in production, Podman/Docker locally)
- Hosting: Render (API, Docker), Vercel (frontend); GitHub Actions runs the tests on every push

## Tests
```
cd backend
uv run pytest
```
The tests need a local Postgres with a `kisht_test` database; see [deployment.md](deployment.md). Frontend checks: `cd frontend && npx eslint app lib components && npx tsc --noEmit`.

## More
- [deployment.md](deployment.md): run locally, how it is deployed, environment variables, demo logins
- [docs/assumptions.md](docs/assumptions.md): everything not stated in the brief, and known limits
