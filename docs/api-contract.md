# Horkos API contract

**Status: DRAFT v1.** Written by the frontend. The backend should read it, change anything that doesn't fit, and then both of you treat it as the agreement. If you change it, change this file in the same commit and tell the other person.

The TypeScript types in `frontend/src/lib/types.ts` and the fake data in `frontend/src/lib/mock-data.ts` match this document exactly.

---

## 1. Conventions

| Topic | Rule |
|---|---|
| Base URL | `http://localhost:8000` (local) |
| Format | JSON in, JSON out, `Content-Type: application/json` |
| Money | **Integer cents** in fields ending `_cents`. Never floats. `currency` is always `"USD"`. |
| Time | ISO 8601 in UTC, for example `2026-10-20T09:00:00Z` |
| IDs | Strings with a prefix: `usr_`, `oath_`, `sel_`, `job_`, `pay_`, `aud_`, `evt_`, `sub_`, `atk_` |
| Auth | `Authorization: Bearer <token>` on every endpoint except `POST /auth/login` |
| Lists | `{ "items": [...], "total": 12 }` (no pagination for the hackathon) |
| Field names | `snake_case` everywhere |

### Errors

Every error uses the same shape:

```json
{ "error": { "code": "invalid_state", "message": "This payment has already been decided." } }
```

| HTTP | `code` | When |
|---|---|---|
| 401 | `unauthorized` | Missing or bad token |
| 404 | `not_found` | Unknown ID |
| 409 | `invalid_state` | Action not allowed in the current status |
| 422 | `validation_error` | Bad input |
| 500 | `server_error` | Anything else |

> FastAPI returns its own `{"detail": [...]}` shape for validation errors by default. Add an exception handler so they use the shape above.

---

## 2. Values everyone must use

**Verdict:** `approve`, `block`, `ask`

**Risk level:** `low` (score 0-33), `medium` (34-66), `high` (67-100)

**Payment status:** `proposed`, `awaiting_user`, `approved`, `held`, `verified`, `released`, `refunded`, `blocked`

Allowed moves:

```
proposed -> approved | awaiting_user | blocked
awaiting_user -> approved | blocked
approved -> held
held -> verified | refunded
verified -> released
```

**Seller tier:** `new`, `building`, `trusted`, `restricted`

**Hard rule codes** (set in `decision.hard_rule` when a hard rule decided the outcome, otherwise `null`):
`recipient_changed`, `over_cap`, `excluded_category`, `blocklisted_or_low_trust`

**Signal codes** (every decision lists all six, triggered or not):
`intent_mismatch`, `recipient_changed`, `edge_of_limit`, `velocity`, `unproven_seller`, `pressure_language`

**Attack types:** `recipient_change`, `over_limit`, `edge_of_limit`, `rapid_retries`, `pressure_language`, `bad_work`

**Actors** (audit trail): `user`, `buyer_agent`, `guard`, `verifier`, `system`

**Job status:** `open`, `awaiting_work`, `verifying`, `completed`, `failed`, `cancelled`

---

## 3. Endpoints

| Screen | Method and path | Purpose |
|---|---|---|
| Login | `POST /auth/login` | Demo login |
| Oath | `GET /oath`, `PUT /oath` | Read and save the user's rules |
| Start a job | `POST /jobs` | User makes a request; the Buyer Agent proposes a payment |
| Money Tracker | `GET /payments`, `GET /payments/{id}` | List payments, and one payment with its history |
| Ask pop-up | `POST /payments/{id}/decision` | User approves or rejects an "ask" |
| Seller page | `POST /jobs/{id}/submission` | Seller hands in work |
| Trust Board | `GET /sellers` | Trust score and limit for each seller |
| Audit Trail | `GET /audit` | Every decision, with reasons |
| Live Feed | `GET /events` | Server-Sent Events stream |
| Demo controls | `POST /demo/attack/{type}`, `POST /demo/reset` | Red Team button and reset |

---

### 3.1 `POST /auth/login`

Request:
```json
{ "email": "amara@example.com", "password": "demo-password" }
```
Response `200`:
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": { "id": "usr_amara", "name": "Amara", "email": "amara@example.com" }
}
```

---

### 3.2 `GET /oath` and `PUT /oath`

`PUT` request (the user types plain English):
```json
{ "raw_text": "Spend up to $50 per job and $100 per day. Only on coding work. Ask me before anything over $30, and always ask me about a seller I have not used before." }
```
Response `200` (both `GET` and `PUT`). `policy` is what Horkos understood, shown back to the user to confirm:
```json
{
  "id": "oath_1",
  "raw_text": "Spend up to $50 per job and $100 per day. Only on coding work. Ask me before anything over $30, and always ask me about a seller I have not used before.",
  "policy": {
    "per_job_cap_cents": 5000,
    "daily_cap_cents": 10000,
    "ask_threshold_cents": 3000,
    "allowed_categories": ["coding"],
    "blocked_categories": [],
    "ask_for_new_sellers": true
  },
  "updated_at": "2026-10-20T08:55:00Z"
}
```

---

### 3.3 `POST /jobs`

The user describes what they want. The Buyer Agent picks a seller (or uses `seller_id` if given), proposes a payment, and the Guard decides. The response already contains the Guard's decision.

Request:
```json
{ "request_text": "Write a Python function that converts a CSV file into JSON.", "seller_id": "sel_zed" }
```
`seller_id` is optional.

Response `201`:
```json
{
  "job": {
    "id": "job_2003",
    "request_text": "Write a Python function that converts a CSV file into JSON.",
    "category": "coding",
    "status": "open",
    "seller_id": "sel_zed",
    "payment_id": "pay_1003",
    "acceptance_tests": [
      "Converts a simple CSV with a header row",
      "Handles empty fields",
      "Raises a clear error on an empty file"
    ],
    "created_at": "2026-10-20T10:00:00Z"
  },
  "payment": { "...": "a full Payment object, see 3.4" }
}
```

---

### 3.4 The Payment object

Returned by `GET /payments`, `GET /payments/{id}` and inside `POST /jobs`.

```json
{
  "id": "pay_1003",
  "job_id": "job_2003",
  "seller_id": "sel_zed",
  "seller_name": "Zed Dev",
  "amount_cents": 2500,
  "currency": "USD",
  "status": "awaiting_user",
  "decision": {
    "verdict": "ask",
    "risk_score": 48,
    "risk_level": "medium",
    "reason": "I need your approval: Zed Dev is new with no delivery history, and $25.00 is above their current limit of $10.00.",
    "hard_rule": null,
    "signals": [
      { "code": "intent_mismatch",   "triggered": false, "detail": "No concern found." },
      { "code": "recipient_changed", "triggered": false, "detail": "No concern found." },
      { "code": "edge_of_limit",     "triggered": true,  "detail": "Amount is 2.5 times this seller's current limit." },
      { "code": "velocity",          "triggered": false, "detail": "No concern found." },
      { "code": "unproven_seller",   "triggered": true,  "detail": "Zed Dev has no completed jobs yet." },
      { "code": "pressure_language", "triggered": false, "detail": "No concern found." }
    ]
  },
  "history": [
    { "status": "proposed",      "at": "2026-10-20T10:00:00Z", "note": "Buyer Agent proposed paying $25.00 to Zed Dev." },
    { "status": "awaiting_user", "at": "2026-10-20T10:00:03Z", "note": "Guard asked the user to decide." }
  ],
  "paypal": { "funding_ref": null, "payout_ref": null, "refund_ref": null },
  "created_at": "2026-10-20T10:00:00Z",
  "updated_at": "2026-10-20T10:00:03Z"
}
```

A blocked payment looks the same, with `status: "blocked"`, `decision.verdict: "block"` and `decision.hard_rule` set, for example:
```json
{ "verdict": "block", "risk_score": 97, "risk_level": "high",
  "reason": "Blocked: the recipient changed from Nova Scripts to a different account in the middle of the job.",
  "hard_rule": "recipient_changed", "signals": [ "...all six..." ] }
```

`GET /payments` response: `{ "items": [Payment, ...], "total": 6 }`, newest first. Optional query: `?status=held`.

---

### 3.5 `POST /payments/{id}/decision`

Used by the "Ask" pop-up. Only allowed when `status` is `awaiting_user`, otherwise `409 invalid_state`.

Request:
```json
{ "decision": "approve" }
```
`decision` is `"approve"` or `"reject"`. Response `200`: the updated Payment. Approving moves it to `approved` and then `held`; rejecting moves it to `blocked`.

---

### 3.6 `POST /jobs/{id}/submission`

The seller hands in their work. Verification takes a while, so the call returns immediately and the result arrives through the Live Feed and `GET /payments/{id}`.

Request:
```json
{
  "seller_id": "sel_kip",
  "content": "def csv_to_json(path):\n    ...\n"
}
```
Response `202`:
```json
{ "submission_id": "sub_3001", "status": "verifying", "payment_id": "pay_1002" }
```

Test results are described by this object, which appears in the `verification.result` event payload and in the audit trail `details`:
```json
{ "passed": 8, "failed": 0, "total": 8, "duration_ms": 1840, "output_excerpt": "8 passed in 1.84s" }
```

---

### 3.7 `GET /sellers`

```json
{
  "items": [
    {
      "id": "sel_nova",
      "name": "Nova Scripts",
      "paypal_email": "nova-seller@example.com",
      "trust_score": 82,
      "tier": "trusted",
      "limit_cents": 5000,
      "jobs_completed": 5,
      "jobs_failed": 0,
      "last_activity_at": "2026-10-20T09:12:41Z"
    }
  ],
  "total": 4
}
```
`trust_score` is 0 to 100. `last_activity_at` is `null` for a seller with no activity. `paypal_email` is a **sandbox** account.

---

### 3.8 `GET /audit`

Optional query: `?payment_id=pay_1001`. Newest first.

```json
{
  "items": [
    {
      "id": "aud_007",
      "payment_id": "pay_1003",
      "at": "2026-10-20T10:00:03Z",
      "actor": "guard",
      "action": "Reviewed the payment",
      "verdict": "ask",
      "reason": "New seller with no history, and the amount is above their limit.",
      "details": { "risk_score": 48 }
    }
  ],
  "total": 12
}
```
`verdict` is `null` for entries that are not Guard decisions. `details` is a free-form object.

---

### 3.9 `GET /events` (Live Feed, Server-Sent Events)

The browser's `EventSource` **cannot send an Authorization header**, so for this endpoint the token goes in the query string: `GET /events?token=<access_token>`.

Content type is `text/event-stream`. **Use unnamed events** (no `event:` line) and put the type inside the data. This lets the frontend use a single `onmessage` handler.

```
data: {"id":"evt_002","type":"payment.verdict","at":"2026-10-20T11:00:02Z","payment_id":"pay_1007","seller_id":"sel_kip","message":"Guard approved the payment (low risk).","payload":{"verdict":"approve","risk_level":"low","risk_score":14}}

```
(Each event ends with a blank line. Send a comment line such as `: ping` every 15 seconds to keep the connection open.)

Event object:

| Field | Meaning |
|---|---|
| `id` | `evt_...` |
| `type` | One of the types below |
| `at` | Time of the event |
| `payment_id`, `seller_id` | Related IDs, or `null` |
| `message` | **A ready-to-display sentence.** The frontend shows this text as is. |
| `payload` | Extra data, shaped per type |

| `type` | When | `payload` |
|---|---|---|
| `payment.proposed` | Buyer Agent proposes a payment | `{ "amount_cents": 1500 }` |
| `payment.verdict` | Guard decides | `{ "verdict": "approve", "risk_level": "low", "risk_score": 14 }` (blocked ones also include `"hard_rule"`) |
| `payment.status_changed` | Any status change | `{ "from": "approved", "to": "held" }` |
| `verification.result` | Tests finished | `{ "passed": true, "tests_passed": 8, "tests_total": 8 }` |
| `trust.updated` | A seller's score changed | `{ "old_score": 46, "new_score": 58, "new_limit_cents": 3000 }` |
| `demo.attack_started` | Red Team button pressed | `{ "attack": "recipient_change" }` |
| `demo.reset` | Demo was reset | `{}` |

---

### 3.10 Demo controls

`POST /demo/attack/{type}` where `type` is one of the attack types in section 2. Returns `202`:
```json
{ "attack_id": "atk_4001", "type": "recipient_change", "status": "started" }
```
The outcome arrives through the Live Feed (a `demo.attack_started` event, then `payment.verdict` and so on).

`POST /demo/reset` returns `204` with no body. It restores the seeded demo data (users, sellers, oath, example payments) and sends a `demo.reset` event.

| Attack type | Expected outcome |
|---|---|
| `recipient_change` | Block (`hard_rule: recipient_changed`) |
| `over_limit` | Block (`hard_rule: over_cap`) |
| `edge_of_limit` | Ask or block, depending on risk |
| `rapid_retries` | Velocity signal triggered |
| `pressure_language` | Pressure-language signal triggered |
| `bad_work` | Tests fail, buyer refunded, trust drops |

---

## 4. Seed data (what `POST /demo/reset` restores)

- **User:** Amara (`usr_amara`, `amara@example.com`)
- **Oath:** $50 per job, $100 per day, coding only, ask above $30, ask for new sellers
- **Sellers:**

| ID | Name | Trust | Tier | Limit |
|---|---|---|---|---|
| `sel_nova` | Nova Scripts | 82 | trusted | $50.00 |
| `sel_kip` | Kip Codes | 46 | building | $25.00 |
| `sel_zed` | Zed Dev | 0 | new | $10.00 |
| `sel_quick` | QuickPay Dev | 9 | restricted | $5.00 |

The frontend's `mock-data.ts` shows the same data as complete payments, audit entries and events.

---

