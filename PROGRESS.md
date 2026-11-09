# Progress

## Done
- Backend: FastAPI, SQLAlchemy models, 2 Alembic migrations, health endpoint, Dockerfile, CI (green)
- Auth: login with httpOnly cookie, role checks, 15 minute lockout after 5 failures
- CSV import: per-row validation, pincode/workload assignment, loans missing from the file marked cured
- Seed script (brief rows exact, ~22% roll rate) and sample CSVs in sample-data/
- 52 backend tests passing

## In progress
- Frontend: Next.js scaffold exists; officer and manager login screens and the import screen are not built yet

## Decisions
- Podman Postgres locally, uv with Python 3.13, monorepo (backend/ on Render, frontend/ on Vercel)
- Vercel rewrites /api to the backend so the session cookie stays first-party
- Manager sees all branches; officers only their own loans
- Re-import updates figures and keeps the officer; cured loans keep their history

## Next
- Frontend login and import screens, then the scoring module and officer priority list
