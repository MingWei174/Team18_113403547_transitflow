# Train Ticket Booking System — Mock Data

This dataset models a fictional public transit system comprising two networks: a **city metro** and a **national rail** service. It is intended for database design and modelling exercises.

## Networks

**City Metro** — an urban network with 4 lines and 20 stations. Tickets are purchased on the day of travel; no advance booking or seat assignment is involved. Some stations are interchange points between metro lines or between the metro and national rail.

**National Rail** — an intercity network with 2 lines and 10 stations. Tickets can be booked in advance with seat assignment. Two service types operate on each line. Fares vary by fare class and journey length.

## Data Domains

**Infrastructure** — the physical stations and the scheduled services that run between them for both networks.

**Users** — registered passengers who can make bookings and purchases.

**Transactions** — how passengers interact with the system differs between networks. National rail involves advance bookings with seat reservations; metro travel is recorded as same-day tap-in trips. All transactions are associated with a payment record. Passengers may leave feedback after travelling.

**Policies and Rules** — documents covering ticket types, refund eligibility, booking rules, and passenger conduct policies for both networks.

## Files

| File | Description |
|---|---|
| `metro_stations.json` | Metro station data |
| `national_rail_stations.json` | National rail station data |
| `metro_schedules.json` | Metro line schedules and fare structure |
| `national_rail_schedules.json` | National rail schedules and fare structure |
| `national_rail_seat_layouts.json` | Coach and seat layout templates for national rail |
| `registered_users.json` | Registered passenger accounts |
| `bookings.json` | National rail advance bookings |
| `metro_travel_history.json` | Metro tap-in travel records |
| `payments.json` | Payment records for all transactions |
| `feedback.json` | Post-travel ratings and comments |
| `ticket_types.json` | Ticket type definitions and rules |
| `refund_policy.json` | Refund eligibility by network, ticket type, and cancellation window |
| `booking_rules.json` | Booking and modification rules |
| `travel_policies.json` | Passenger conduct and luggage policies |

## Custom additions already annotated from prior commits

The following notes summarize the user-added mock-data extensions that were introduced in earlier commits, so the dataset stays readable without changing the original JSON structure:

- `booking_rules.json`: adds refund-processing timing, change-confirmation messaging, and extra service-cancellation / fare-adjustment guidance for both rail and metro flows.
- `refund_policy.json`: adds extra refund-method and exception notes, plus the new RF006 and RF007 policy rules for duplicate bookings and missed-connection compensation.
- `ticket_types.json`: adds cancellation instructions, transferability notes, refund notes, return-extension rules, activation guidance, and exceptional-refund notes for ticket types.
- `travel_policies.json`: adds accessibility guidance and updated travel-policy metadata for metro and national rail.
- `registered_users.json`: the password fields were updated to bcrypt hashes in the later user-data commit, which is why the demo account records now store secure password values instead of plain text.
