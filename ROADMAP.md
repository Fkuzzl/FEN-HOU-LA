# Roadmap

## Done in vertical slice

- Auth with secure password hashing and cookie session
- Group creation and membership authorization
- Multi-bill expense completion
- Per-bill participant selection and equal split preview
- Completed event history
- Decimal-friendly amount entry
- Group-only friends without accounts
- Completed event detail modal
- Billing request tracking
- Date-only bill entry (DD/MM/YYYY display/input)
- Percentage and fixed/remaining per-bill splits
- Aggregated per-recipient totals across all bills
- Copy/share/print invoice-style messages for each recipient
- Expiring 7-day group invite links with authenticated acceptance
- Multi-event net settlement with deterministic cent-based transfer suggestions
- Docker, migrations, CI, responsive Traditional Chinese UI
- Manual per-share payment confirmation with persisted audit timestamps
- Clear registered-account versus unregistered-friend labels
- Confirmation-gated deletion for groups, participants, events, and bills

## Audit status

The original vertical-slice target is complete, including registration, group selection, multi-bill equal splitting, persistence, reload, history, and responsive entry. Post-MVP security and lifecycle foundations are also implemented. Explicit deletion is owner-only and confirmation-gated; historical participants referenced by bills remain protected.

## Remaining next phases

- R2/provider adapter for receipt storage (local default and configured private production bucket are complete; public-host secret injection remains)
- Hosted deployment verification
