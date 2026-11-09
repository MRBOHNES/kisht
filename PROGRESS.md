# Progress

## Done
- Backend: FastAPI, models, migrations, health endpoint, Dockerfile, CI
- Auth: httpOnly cookie, role checks, 15 minute lockout; review fixes for import crashes, bcrypt length and insecure defaults
- CSV import with per-row validation, pincode/workload assignment and the cured rule; seed and sample CSVs
- Priority score (pure function, boundary tests), officer Today list and loan detail with ownership checks
- Group 1: outcome logging in 3 taps with server-side validation, contact window enforced on the server (calls blocked and recorded), Call and Map buttons, promise kept/broken rules, promises screen with tabs, bottom tab bar
- Officer screens: login, Today, loan detail, outcome sheet, promises (Hindi default, English toggle)

## Next
- Group 2: offline outbox and /sync, sync screen
- Group 3: manager login, import screen, roll-rate view, pins

## Decisions
- Podman Postgres locally, uv with Python 3.13, monorepo (backend/ on Render, frontend/ on Vercel)
- Vercel rewrites /api to the backend so the session cookie stays first-party
- See docs/assumptions.md for everything not in the brief

## Notes
- Commit e403941 says "logins, import screen and hindi/english strings" but only contains the Next.js scaffold; the login and strings came in 6fe1ba7. History left as is.
