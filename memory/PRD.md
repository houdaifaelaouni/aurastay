# AuraStay — rental marketplace and agency workspace

## Original problem statement
The user requested a two-sided accommodation platform like Booking/Airbnb/Expedia/Idealista: a public property website where guests choose dates and pay a small €10–€30 non-refundable reservation fee, plus a private real-estate agency workspace. Agencies register properties with photos, availability, amenities and additional services; specify nightly prices and their commission percentage (normally 10–20%); track reservations, rented nights, profits, team members (managers, commercial agents, cleaners), and property expenses with reasons. The platform earns reservation fees and a 2% commission. All amounts are euros. The original reference to three dashboard pages expanded to five functional sections: Dashboard, Properties, Commissions, Team and Expenses.

## Approved requirements and decisions (static)
- English, responsive guest catalogue as first screen, not a marketing splash; working brand AuraStay.
- Multiple independent agencies. Platform owner oversees all agencies; agency administrators/managers access only their agency. Other team members are directory-only.
- Every listing is an entire individually bookable property. Arrival inclusive / departure exclusive. External bookings and owner/maintenance blocks are manually maintained. No channel synchronization initially.
- Fee-only online payment via Whop; rental balance and optional services payable separately to agency. Verified payment success is required for immediate confirmation; never trust redirect alone.
- Platform commission = **2% of full accommodation subtotal**, deducted from agency gross; NOT 2% of agency income. Services and reservation fees excluded from commission calculations.
- Example: €1,000 accommodation × 20% = €200 agency gross; €20 platform share; €180 agency retained; €800 owner allocation.
- Default fee = clamp(1% of accommodation + €1/night, minimum €10, maximum €30). Additional to rent; platform income. Editable for future bookings. Historical prices/rates remain snapshots.
- Public search by destination/dates/guests; amenities/max-price filters; price sorting. Detail/gallery, services, fee breakdown, guest name/email/phone, terms and private status page.
- Dashboard separates rent, agency commission, platform commission, fee collections/refunds, services and expenses. Completed stays earned; future confirmed stays projected. Settlements separate from earned amounts.
- Property create/edit/publish/unpublish/archive, photos/cover/order, calendar blocks, per-stay/per-night services.
- Commissions by booking/property, date/status filters, recorded settlement date/reference, CSV. No automatic commission collection or split payouts.
- Team directory, status, roles, assigned properties. Expense date/property/category/reason/amount/payer/reimbursement; edit/filter/CSV. Owner-paid or reimbursed costs excluded from agency net without double counting.
- Platform owner creates/disables agencies and manager access; configures fees. Public photos for published active listings; private photos for unpublished records. Storage removal is soft deletion, not physical erasure.

## Explicit user payment decision
User chose: **Keep real payments disabled until configured. Build the booking flow now; enable payments only after Whop credentials and merchant eligibility confirmation.** No further preferences supplied.
Whop accommodation-service merchant eligibility is unconfirmed. No Whop credentials were provided. No live checkout, webhook fulfillment or refund execution has been integrated or claimed as functional. `POST /api/properties/{id}/checkout` validates the quote then deliberately returns 503, without creating a booking or hold. UI permits dates, quotes, guest details and review, but clearly disables payment and does not create a fake confirmation. Completing real payment processing remains P0 dependent on user/Whop approval and credentials.

## Personas
1. Guest: browse a suitable entire home, inspect dates and price, reserve after fee payment when enabled, view private status.
2. Agency administrator/manager: manage portfolio, calendar, reservations, team and costs; understand earnings and settle platform payables.
3. Platform owner: oversee agencies, staff access, reservation-fee revenue and platform commissions.
4. Directory-only staff: represented in team records; no individual accounts in this version.

## Architecture
- React 19 + React Router, Shadcn button/dialog, Sonner, Lucide, Recharts. Guest routes `/`, `/saved`, `/stays/:id`, `/booking/:token`, `/login`; workspace `/workspace`, `/properties`, `/commissions`, `/team`, `/expenses`, `/agencies`, `/settings` under `/workspace`.
- FastAPI on supervisor-managed port 8001, MongoDB via existing `MONGO_URL` and `DB_NAME`. Frontend exclusively uses `REACT_APP_BACKEND_URL`.
- Backend modules: `core.py` scoped repository and authorization; `auth.py` verified JWT/bcrypt; `models.py` strict Pydantic validation; `finance.py` Decimal monetary math; `availability.py` single-document conditional calendar updates; `public.py`, `workspace.py`, `reports.py`, `platform_routes.py`, `media.py`, `jobs.py`, `seed.py`.
- Global identities in users; platform role and tenant membership role kept separate. Fresh DB identity/membership/agency checks each request enforce immediate revocation. Mandatory ScopedRepo predicates for workspace domains. Owner global read permitted; selected, logged agency context required for tenant writes.
- Collections: users, memberships, agencies, properties, calendars, bookings, blocks, team, expenses, files, settings, job_runs. UUID/string identifiers, `_id` excluded; inserted documents copied before responding. Booking quote snapshots preserve amounts/rates.
- Atomic availability: one calendar document per property; conditional update checks overlap before adding slot. Blocks and reservation slots share the same authoritative calendar. Expired holds excluded at read/acquisition and background cleanup.
- `.emergent/crons.yml`: 15-minute expired-hold cleanup endpoint with constant-time secret comparison, envelope validation, unique run ID and BackgroundTasks acknowledgement. Expiry infrastructure is prepared but checkout does not create holds while disabled.
- Persistent image storage uses platform object storage via authenticated backend; JPEG/PNG/WebP magic/type and 8MB checks; UUID paths; metadata source of truth in MongoDB. Public fetch depends on active agency/published property; otherwise verified agency auth. No direct provider URLs/secrets in browser.
- CSV exports tenant-filtered and formula-escaped. EUR reports are operational estimates, before taxes and unrecorded provider costs.
- Secrets only in backend `.env`; references (not secret values) in `/app/memory/test_credentials.md`.

## Implemented — 2026-09-15
- Photography-led responsive catalogue, destination/date/guest search, categories/amenities/price filters/sort, persistent saved stays.
- Property detail, photo lightbox, available-date quotes and optional services, transparent fee vs rental balance, guest-detail/terms review, honest Whop-disabled state, private booking-status page.
- Owner and agency JWT login, isolated workspace access, five management sections plus owner agency/access/settings routes.
- Dashboard reports/chart/property comparison/reservation detail, recorded rent received, completed-stay gating, cancellation with reason and calendar release.
- Property CRUD lifecycle, image uploads/reorder/cover/remove, services, calendar block management and conflict prevention.
- Booking/property commission reports, date/status filters, eligible settlement recording and CSV export.
- Team create/edit/contact/role/status/property assignments; expense create/edit/filter/payer/reimbursement and CSV.
- Owner agency contact/payment instructions/status, manager account creation/revocation, fee configuration.
- Eight sample properties, two sample agencies, sample staff/reservations/expenses. Sample records are illustration only, not actual transactions; dashboard is explicitly labeled Sample portfolio.

## Verification — 2026-09-15
- External API health, catalogue and dashboard verified; frontend production build succeeds.
- Testing agent report `/app/test_reports/iteration_1.json`; 20/20 backend regression cases pass. Covers search, fee math, checkout fail-closed, access denial, block overlap, agency visibility/revocation, media privacy, cron auth/idempotency, CSV.
- Desktop and mobile guest catalogue/detail/review/login and workspace flows exercised by testing agent.
- Tester found mobile workspace horizontal overflow; root causes were property-comparison grid min-content sizing and chart tooltip bounds. Fixed with minmax tracks and bounded chart container.
- Post-fix self-test: all five workspace pages at 390px have scrollWidth equal to viewport width (390). Chart initial-dimension warnings addressed. Follow-up final checks recorded separately.
- Final verification: production build **compiled successfully with no lint warnings**; existing 20-case external API regression suite rerun **20/20 passed** (`/app/test_reports/pytest/final_results.xml`).
- All five workspace routes verified at **320px, 390px and 768px** with no global horizontal overflow. Mobile sidebar navigation works after its entrance transition.
- Final quote/guest-detail/terms/review flow rechecked; disabled Whop payment remains disabled; no duplicate `data-testid` attributes in the active page/modal.
- Guest-count option labels simplified to eliminate instrumentation-related invalid nested HTML warnings. The known disposable `TEST UI Property` record created by the testing agent was removed; genuine/sample portfolio history was preserved.
- Final screenshots: `/app/test_reports/final-catalogue-desktop.jpg`, `/app/test_reports/final-booking-review.jpg`; build log `/app/test_reports/final-build.log`; verification `/app/test_reports/final_verification.json`.

## Prioritized remaining work
### P0 — before real bookings/payment launch
1. Obtain Whop written accommodation-service eligibility and merchant-country/account approval; finalized legal/cancellation/tax/supplier responsibilities.
2. Collect Whop business ID, API and webhook credentials; implement hosted dynamic EUR checkout, secure 15-minute holds, authoritative signed success events, idempotent payment ledger, return-state checks, late/duplicate/unfulfillable payment refunds and staff retry handling; verify sandbox end to end before enabling.
3. Replace sample portfolio and example contact/payment instructions with genuine agency data/photos. No actual fee payments or booking confirmations available currently.
### P1 — useful next iteration
1. External calendar synchronization (Airbnb/Booking/iCal), reducing manual availability maintenance.
2. Formal payment reconciliation/provider cost capture, refund exception workflow after payment integration.
3. Rich calendar month view and pagination for large portfolios; account password change/recovery.
### P2 — explicitly deferred scope
Seasonal pricing/discounts, maps, reviews, guest accounts, self-service changes, automated email/SMS, staff scheduling/tasks/payroll, receipt uploads, owner portals, online rent collection, automatic commission payouts, multilingual/multi-currency, tax invoicing/accounting integrations.

## Next tasks
Confirm business identity and real listing data; configure Whop only after eligibility/credentials; complete payment/refund lifecycle; then add calendar synchronization.