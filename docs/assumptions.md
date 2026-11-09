# Assumptions and known limits

Anything here is not stated in the client brief. It was decided for this build and can be changed.

## Priority score
- Weights and thresholds are as specified in the build decisions and live in one dict, `SCORING` in `backend/app/scoring.py`.
- The broken-promise window includes day 90.
- "Last 7 days" (not reachable, self-cure) means today plus the 6 days before it.
- DPD above 30 (already rolled) gets the full 35 roll-risk points.
- An open promise whose date has passed counts as broken.
- Amount factor: log scale from Rs 50,000 (0.8) to Rs 10,00,000 (1.2), clamped outside that range.
- A payment the officer logs counts as a payment straight away, before the next CSV import.

## Data and import
- CSV columns: `loan_id, business_name, business_type, phone, pincode, outstanding, emi, dpd, last_payment_date` and an optional `address` (blank allowed). Address is not in the brief.
- The brief's sample "Promise Date" and "Officer" columns come from the app (promises logged by officers, officers assigned by the app), not from the loan-system export.
- Assignment: pincode -> branch -> the officer in that branch with the fewest open loans (ties go to the lowest id).
- Re-import updates outstanding, EMI, DPD and last payment and keeps the officer. Loans missing from the day's file are marked cured and leave officer lists; their history stays. A file with no valid rows cures nothing.
- The demo manager acts as head of collections across all branches. Per-branch scoping is a next step. Officers only see and act on their own loans.

## Contact window and outcomes
- Contact window is 08:00 to 19:00 India time (Asia/Kolkata), start inclusive, end exclusive.
- Calls outside the window are blocked by the server and the attempt is stored. The full phone number is only sent for an allowed call.
- Outcomes logged outside the window are stored and flagged for the manager, not rejected.
- The outcome time is the phone's clock. Up to 5 minutes ahead is accepted; a phone set back in time is not detected.
- Promise default date is today + 3 days. A promise date must be between the day it was logged and 30 days after.
- A promise is kept by any payment logged on or before its date (partial payments count). It is broken once its date passes with no payment. A payment that reaches the server late still keeps a promise it met in time.

## Manager view
- Roll rate: of the loans 1 to 30 days past due in one month's snapshot, the share above 30 in the next. A loan missing from the next snapshot counts as not rolled. Target 16%.
- The seed has four monthly snapshots, so the dashboard shows three month-to-month roll rates. The CSV import does not write snapshots; a real system would take one at each month end.
- "Visits logged same day": share of outcomes in the last 30 days that reached the server on the day they were logged (India time). Target 95%.
- "Untouched": active loans with no outcome and no call attempt in the last 7 days.
- "About to roll": active loans at 25 to 30 days past due, largest outstanding first.
- A pin puts the loan first in its officer's list with the manager's reason. If the loan moves to another officer, the pin no longer applies. Only one pin per loan.
- The roll-rate card on the manager login page is an illustration with sample numbers; real figures need sign-in.
- Import error messages ("problem" and "how to fix") come from the server in English only.

## Offline
- Outcomes are saved to the phone (IndexedDB) first and sent in batches of up to 100. The server ignores a repeated outcome id.
- The contact window is checked against the time on the phone when the outcome was logged, not when it reached the server.
- The Today list, promises and opened loans are kept on the phone for offline reading and removed on sign-out. Unsent outcomes stay on the phone after sign-out; if a different officer signs in on that phone, the server rejects them because the loans are not theirs.
- A service worker keeps visited pages openable offline. It never caches API responses. A page never opened online shows a short offline notice.
- Logging an outcome from the Today list works offline. Opening a loan's detail offline works only if it was opened online before.

## Seed data
- Branch names (Vijay Nagar, Palasia, Rajwada) are real Indore areas; pincodes are sample.
- Rahul Chouhan, Neha Solanki and Imran Qureshi are from the brief. The other seven officers, both managers, companies E to K and all generated traders are sample data.
- The brief gives no payment dates, so the three brief loans have fixed last payments: LN-10293 on 28 Sep (its 5 Nov promise was not kept), LN-10871 on 13 Sep (27 days overdue, about to roll), LN-11930 on 21 Sep (its 31 Oct promise broke).

## Known security limits
- Signing out or a lockout does not end sessions already issued; a token stays valid for its 12 hours. Fix: a `token_version` column on users, bumped on sign-out and lock and checked on every request.
- The lockout reveals which emails exist: only a real account can reach the "locked" response. Fix: count failures per email for unknown emails too and answer them the same way.
- There is no per-IP rate limit, so anyone who knows an officer's email can lock the account for 15 minutes. Fix: rate limiting at the proxy or in the API.
