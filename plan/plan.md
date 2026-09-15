# Rental marketplace and agency management platform

## Purpose
Create a two-sided platform: a public accommodation-booking website and a private workspace for real-estate agencies. Guests pay a small reservation fee online to confirm a stay; agencies manage properties, reservations, commissions, teams, and expenses. The platform owner can see reservation-fee income and the commissions agencies owe.

## Confirmed decisions
- All prices, payments, expenses, and financial reports use euros.
- Guests book individual properties for selected dates and pay only the reservation fee online. The rental balance is paid separately to the agency.
- Successful reservation-fee payment immediately confirms the booking; agency approval is not required.
- The platform's commission is **2% of the full rental price**, deducted from the agency's commission—not 2% of the agency's earnings.
- Reservation-fee payments use **Whop**.
- Each property has a nightly price and its own agency commission rate, normally between 10% and 20%.
- The management workspace has five main sections: Dashboard, Properties, Commissions, Team, and Expenses. This follows all the requested functions despite the initial reference to three pages.

## Public booking experience
- The first screen is a usable property catalogue, with photographs, location, nightly price, and availability search—not a separate marketing landing page.
- Search by destination, arrival/departure dates, and guest count. Filter by price and amenities and sort by price.
- Property pages show a photo gallery, description, capacity, bedrooms, amenities, availability, optional services, and booking terms.
- Guests choose dates and optional services, enter their name, email, and phone number, and review a clear price breakdown before paying through Whop.
- The breakdown separates accommodation, optional services, the reservation fee payable now, and the rental balance payable separately. Agency-specific payment instructions explain how and when that balance is due.
- After verified successful payment, show the confirmed reservation, reference number, dates, amounts, payment instructions, and a private booking-status link. Guest accounts are not required in the first version.
- Pending or unsuccessful payments do not produce a confirmation. The private status page supports returning after payment without making a second charge.
- Agency-recorded cancellations release availability. Voluntary guest cancellation normally forfeits the reservation fee, subject to applicable consumer law. Guests contact the agency to request cancellation; self-service changes are outside the initial scope.

## Suggested reservation-fee rule
The exact formula was not specified. The proposed starting rule is:

**Reservation fee = 1% of accommodation subtotal + €1 per night, with a €10 minimum and €30 maximum, rounded to cents.**

For five nights totalling €1,000, the fee is €15. The guest pays €15 online and pays the €1,000 rental balance separately, plus any selected services.

The platform owner can adjust the percentage, per-night amount, minimum, and maximum for future bookings. Existing bookings retain their original quote. The fee is additional to the rent, belongs to the platform, and is separate from the platform's 2% commission. These are proposed assumptions for approval.

## Availability and booking protection
- Each listing represents one entire, individually bookable property, not several interchangeable units.
- Agencies maintain the authoritative calendar, including external bookings and owner/maintenance blocks. There is no automatic Airbnb, Booking.com, or other channel synchronization in the first version.
- Arrival is inclusive and departure exclusive, allowing a departure and a new arrival on the same day.
- A proposed 15-minute hold protects the dates while the guest pays. Unpaid holds expire and dates become available again.
- Overlapping bookings are prevented. If payment arrives after the hold expires, the reservation is confirmed only if those dates can still be secured; otherwise the fee is refunded and no booking is confirmed.
- Duplicate payments and payments for stays the agency/platform cannot honour are refunded. Refund failures remain clearly flagged for staff follow-up. The non-refundable label does not override these exceptions or mandatory legal rights.

## Agency workspace

### 1. Dashboard
- Date-filtered totals for properties, confirmed reservations, booked nights, occupancy, rental value, agency commission, platform commission, expenses, and estimated agency net earnings.
- Reservation-fee collections and refunds appear separately from rent and commission income.
- Charts show booking and earnings trends, with property-level comparisons.
- A reservation view inside this section shows guest details, dates, services, fee-payment status, and rental-payment status. Agencies can record separately received rent, complete stays, cancel bookings, and review refund issues.
- Future confirmed stays are reported as projected earnings; completed stays are reported as earned commission. Collected fees and settled commissions are distinguished from amounts still owed.

### 2. Properties
- Create, edit, publish, unpublish, and archive properties without losing reservation or financial history.
- Manage photos and cover image, location, description, capacity, bedrooms, amenities, nightly price, and agency commission percentage.
- Manage calendar blocks and inspect confirmed reservations. Manual external reservations block availability but do not generate marketplace fees or platform commissions by default.
- Add optional services such as guest accompaniment, transfer, or additional cleaning, with per-stay or per-night prices.
- Initial pricing uses one base nightly rate per property; seasonal pricing and promotional discounts are deferred.

### 3. Commissions
- Show accommodation value, agency gross commission, platform commission, and agency retained commission for each booking and property, filterable by date and status.
- For a €1,000 accommodation subtotal and a 20% agency rate: agency gross commission is €200; platform commission is €20; agency retains €180 before expenses. The property-owner allocation is €800 before owner-related adjustments.
- Accommodation subtotal means nightly price multiplied by nights. Optional services and the reservation fee are excluded from both commission calculations in the first version.
- Agency rates must cover the platform's 2% share. Historic reservations retain the rate and price agreed when booked.
- Record platform commissions as outstanding or settled, including settlement date and reference. Provide downloadable CSV summaries.
- The 2% amount is tracked as payable by the agency; it is **not automatically collected or split through Whop** in this version.

### 4. Team
- Maintain a directory with name, contact details, role, active/inactive status, and assigned properties.
- Support roles such as manager, commercial agent, and cleaning staff.
- Agency administrators and managers have private workspace accounts. Other team members are directory records without individual sign-in in the first version.
- Payroll, staff scheduling, task dispatch, and team messaging are outside the initial scope.

### 5. Expenses
- Log expenses against a property with amount, date, category, description/reason, payer, and owner-reimbursement status.
- Edit entries, filter by property/date/category, and download CSV summaries for discussions with property owners.
- Show agency-paid costs separately from owner-paid or reimbursed expenses. Agency net earnings deduct agency-borne costs without counting an owner reimbursement twice.
- Expense receipt uploads, owner billing, and formal accounting integration are deferred.

## Platform-owner access and financial meaning
- Support multiple agencies under one public marketplace. Each agency sees and manages only its own properties, guests, reservations, team, and financial records.
- The platform owner can create/disable agencies and manager access, oversee listings, configure reservation fees, and view totals across agencies.
- Platform income reports separate collected reservation fees from the 2% commissions earned, outstanding, and settled.
- Rent is not platform revenue. The same commission is not counted twice, and optional-service revenue is shown separately.
- Earnings figures are operational estimates before tax and any unrecorded payment-provider costs, not statutory accounts. Automatic tax calculation and invoicing are not included.

## Whop requirements and limits
Research indicates that Whop supports hosted one-time EUR checkouts with variable prices, booking references, payment notifications, and refunds. Confirmation must follow verified payment success, not merely a return from checkout.

**Accommodation-related merchant eligibility is not established.** Before enabling real payments, the platform owner must obtain confirmation from Whop that this accommodation-reservation service, merchant country, and business model are accepted. EUR checkout availability does not by itself guarantee EUR settlement or account eligibility.

Whop account access, business identification, payment credentials, and payment-notification credentials are required during configuration. No credentials are needed to approve this proposal. If Whop declines this use case, a different payment provider requires a new decision rather than an unannounced substitution.

The platform is assumed to collect only its own reservation fees. Agencies receive rental payments separately. Connected agency payment accounts, rental collection, and automatic commission payouts are not included. The business owner must finalize cancellation wording, tax treatment, supplier responsibilities, and rental-balance instructions before taking real bookings.

Relevant findings:
- One-time checkout and EUR: https://docs.whop.com/api-reference/checkout-configurations/create-checkout-configuration
- Hosted payments: https://docs.whop.com/developer/guides/accept-payments
- Payment notifications: https://docs.whop.com/developer/guides/webhooks
- Refunds: https://docs.whop.com/api-reference/payments/refund-payment
- Merchant eligibility: https://whop.com/seller-terms/ and https://whop.com/prohibited-products-and-services/

## Presentation and photo handling
- Responsive, English-language guest website and management workspace, with clear euro formatting and property photography as the main visual focus.
- A working brand can be replaced when the business supplies its name and identity.
- Agency managers can upload and reorder property photos. Published listing photos are public; unpublished photos and editing controls remain private.
- Persistent photo storage is included without requiring a separate external storage-provider account. Removing a photo hides it from the application; the proposed storage does not offer permanent file deletion, which is a limitation if permanent erasure is required.

## First-version boundaries and possible next additions
Included: the searchable marketplace, Whop reservation-fee booking flow subject to eligibility, authoritative availability, multi-agency access, the five management sections, platform-wide reporting, photo uploads, and CSV exports.

Not included initially: collecting rent online, automatic 2% collection/payouts, external calendar synchronization, map search, guest reviews, guest accounts, automated email/SMS, staff scheduling, owner portals, seasonal prices, multi-currency, multilingual content, or tax invoicing. Confirmations are available on-screen and through the private booking-status link rather than automatically emailed.

A useful next addition is external calendar synchronization, reducing manual updates and double-booking risk for agencies listing properties on several websites.

## Decisions most worth reviewing
1. The proposed €10–€30 formula and the assumption that reservation fees belong to the platform.
2. Whop eligibility and account requirements for accommodation-related fees.
3. Manual calendars with immediate confirmation, and the proposed 15-minute payment hold.
4. Tracking—but not automatically collecting—the platform's 2% commission.
5. Commission calculations excluding optional services and external reservations.
6. Manager accounts versus a directory-only first version for other staff, and on-screen rather than emailed booking confirmations.