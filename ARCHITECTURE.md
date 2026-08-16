# Architecture

The frontend is a Vite React single-page app. It uses cookie-based sessions and calls the FastAPI REST API with credentials included. The backend owns validation, group membership authorization, event completion, and all money calculations.

PostgreSQL is the local and production relational store. Amounts use `DECIMAL(12,2)`, while the split engine converts to integer cents for deterministic equal allocation. Expense events have one payer, many bills, and participant links per bill. Completed events are read-only during normal editing; an owner may explicitly delete a group, event, or bill after a confirmation prompt. Each bill share has a persisted manual confirmation timestamp and actor for payment tracking.

Group-only friends are represented as non-login contact identities in the group membership table. Their generated contact email is not exposed as an account credential; the UI labels them as friends and lets them participate in bill splits. Billing requests are separate records with pending, completed, and cancelled states.

Receipt metadata is stored on bills now; an object-storage adapter for private R2 uploads is planned for the next phase.
