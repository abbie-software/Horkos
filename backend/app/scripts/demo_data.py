"""The demo data from docs/api-contract.md section 4 and frontend/src/lib/mock-data.ts.

Payment and job numbers match the contract's IDs: payment 1003 is "pay_1003",
job 2003 is "job_2003", so the screens look the same with the real server.
"""

from app.schemas.payments import SIGNAL_CODES

DEMO_USER = {"email": "amara@example.com", "name": "Amara"}
# The login shown in the API contract. Change it for anything shared.
DEMO_PASSWORD = "demo-password"

# One login per demo seller, so the seller page can run on real accounts.
SELLER_LOGINS = [
    {"slug": "sel_nova", "email": "nova@example.com"},
    {"slug": "sel_kip", "email": "kip@example.com"},
    {"slug": "sel_zed", "email": "zed@example.com"},
    {"slug": "sel_quick", "email": "quick@example.com"},
]

DEMO_OATH = (
    "Spend up to $50 per job and $100 per day. Only on coding work. "
    "Ask me before anything over $30, and always ask me about a seller "
    "I have not used before."
)

SELLERS = [
    {
        "slug": "sel_nova",
        "name": "Nova Scripts",
        "paypal_email": "nova-seller@example.com",
        "trust_score": 82,
        "limit_cents": 5000,
        "jobs_completed": 5,
        "jobs_failed": 0,
        "last_activity_at": "2026-10-20T09:12:41Z",
    },
    {
        "slug": "sel_kip",
        "name": "Kip Codes",
        "paypal_email": "kip-seller@example.com",
        "trust_score": 46,
        "limit_cents": 2500,
        "jobs_completed": 2,
        "jobs_failed": 0,
        "last_activity_at": "2026-10-20T09:30:05Z",
    },
    {
        "slug": "sel_zed",
        "name": "Zed Dev",
        "paypal_email": "zed-seller@example.com",
        "trust_score": 0,
        "limit_cents": 1000,
        "jobs_completed": 0,
        "jobs_failed": 0,
        "last_activity_at": None,
    },
    {
        "slug": "sel_quick",
        "name": "QuickPay Dev",
        "paypal_email": "quick-seller@example.com",
        "trust_score": 9,
        "limit_cents": 500,
        "jobs_completed": 1,
        "jobs_failed": 2,
        "last_activity_at": "2026-10-19T16:20:00Z",
    },
]

JOBS = [
    {
        "id": 2001,
        "seller": "sel_nova",
        "request_text": "Write a Python function that validates an email address.",
        "status": "completed",
        "tests": ["Accepts a valid address", "Rejects a missing @", "Rejects an empty string"],
        "created_at": "2026-10-20T09:00:00Z",
    },
    {
        "id": 2002,
        "seller": "sel_kip",
        "request_text": "Write a Python function that reverses the words in a sentence.",
        "status": "awaiting_work",
        "tests": ["Reverses a simple sentence", "Keeps single words as they are", "Handles an empty string"],
        "test_code": (
            "from solution import reverse_words\n"
            "\n"
            "def test_reverses_a_simple_sentence():\n"
            "    assert reverse_words('one two three') == 'three two one'\n"
            "\n"
            "def test_keeps_a_single_word():\n"
            "    assert reverse_words('hello') == 'hello'\n"
            "\n"
            "def test_handles_an_empty_string():\n"
            "    assert reverse_words('') == ''\n"
        ),
        "created_at": "2026-10-20T09:30:00Z",
    },
    {
        "id": 2003,
        "seller": "sel_zed",
        "request_text": "Write a Python function that converts a CSV file into JSON.",
        "status": "open",
        "tests": [
            "Converts a simple CSV with a header row",
            "Handles empty fields",
            "Raises a clear error on an empty file",
        ],
        "created_at": "2026-10-20T10:00:00Z",
    },
    {
        "id": 2004,
        "seller": "sel_zed",
        "request_text": "Write a small Python script that renames files in a folder.",
        "status": "cancelled",
        "tests": ["Renames every file", "Leaves other folders alone", "Reports files it could not rename"],
        "created_at": "2026-10-20T10:20:00Z",
    },
    {
        "id": 2005,
        "seller": "sel_nova",
        "request_text": "Write a Python function that merges two sorted lists.",
        "status": "cancelled",
        "tests": ["Merges two sorted lists", "Handles an empty list", "Keeps duplicates"],
        "created_at": "2026-10-20T10:40:00Z",
    },
    {
        "id": 2006,
        "seller": "sel_quick",
        "request_text": "Write a Python function that removes duplicates from a list.",
        "status": "failed",
        "tests": ["Removes duplicates", "Keeps the original order", "Handles an empty list"],
        "created_at": "2026-10-19T16:00:00Z",
    },
]


def decision(verdict, score, level, reason, hard_rule=None, hits=None):
    """Build a Guard decision with all six signals, like the contract requires."""
    hits = hits or {}
    return {
        "verdict": verdict,
        "risk_score": score,
        "risk_level": level,
        "reason": reason,
        "hard_rule": hard_rule,
        "signals": [
            {
                "code": code,
                "triggered": code in hits,
                "detail": hits.get(code, "No concern found."),
            }
            for code in SIGNAL_CODES
        ],
    }


PAYMENTS = [
    {
        "id": 1001,
        "job": 2001,
        "seller": "sel_nova",
        "amount_cents": 2000,
        "status": "released",
        "decision": decision(
            "approve", 6, "low",
            "Approved: $20.00 is within your limits, the job matches your request, "
            "and Nova Scripts has 5 clean deliveries.",
        ),
        "history": [
            ("proposed", "2026-10-20T09:00:00Z", "Buyer Agent proposed paying $20.00 to Nova Scripts."),
            ("approved", "2026-10-20T09:00:02Z", "Guard approved (low risk)."),
            ("held", "2026-10-20T09:00:05Z", "Funds secured."),
            ("verified", "2026-10-20T09:12:30Z", "8 of 8 tests passed."),
            ("released", "2026-10-20T09:12:41Z", "Nova Scripts was paid."),
        ],
        "funding_ref": "MOCK-FUND-1001",
        "payout_ref": "MOCK-PAYOUT-1001",
        "refund_ref": None,
        "created_at": "2026-10-20T09:00:00Z",
        "updated_at": "2026-10-20T09:12:41Z",
    },
    {
        "id": 1002,
        "job": 2002,
        "seller": "sel_kip",
        "amount_cents": 1500,
        "status": "held",
        "decision": decision(
            "approve", 14, "low",
            "Approved: $15.00 is within Kip Codes's current limit of $25.00, "
            "and they have 2 clean deliveries.",
        ),
        "history": [
            ("proposed", "2026-10-20T09:30:00Z", "Buyer Agent proposed paying $15.00 to Kip Codes."),
            ("approved", "2026-10-20T09:30:02Z", "Guard approved (low risk)."),
            ("held", "2026-10-20T09:30:05Z", "Funds secured. Waiting for the work."),
        ],
        "funding_ref": "MOCK-FUND-1002",
        "payout_ref": None,
        "refund_ref": None,
        "created_at": "2026-10-20T09:30:00Z",
        "updated_at": "2026-10-20T09:30:05Z",
    },
    {
        "id": 1003,
        "job": 2003,
        "seller": "sel_zed",
        "amount_cents": 2500,
        "status": "awaiting_user",
        "decision": decision(
            "ask", 48, "medium",
            "I need your approval: Zed Dev is new with no delivery history, "
            "and $25.00 is above their current limit of $10.00.",
            hits={
                "unproven_seller": "Zed Dev has no completed jobs yet.",
                "edge_of_limit": "Amount is 2.5 times this seller's current limit.",
            },
        ),
        "history": [
            ("proposed", "2026-10-20T10:00:00Z", "Buyer Agent proposed paying $25.00 to Zed Dev."),
            ("awaiting_user", "2026-10-20T10:00:03Z", "Guard asked the user to decide."),
        ],
        "funding_ref": None,
        "payout_ref": None,
        "refund_ref": None,
        "created_at": "2026-10-20T10:00:00Z",
        "updated_at": "2026-10-20T10:00:03Z",
    },
    {
        "id": 1004,
        "job": 2004,
        "seller": "sel_zed",
        "amount_cents": 50000,
        "status": "blocked",
        "decision": decision(
            "block", 92, "high",
            "Blocked: $500.00 is above your $50.00 per-job cap. This rule has no exceptions.",
            hard_rule="over_cap",
            hits={
                "intent_mismatch": "The request was for a small script, not a $500.00 service.",
                "pressure_language": "The message said 'pay immediately, no need to review'.",
            },
        ),
        "history": [
            ("proposed", "2026-10-20T10:20:00Z", "Buyer Agent proposed paying $500.00 to Zed Dev."),
            ("blocked", "2026-10-20T10:20:01Z", "Guard blocked: over the per-job cap."),
        ],
        "funding_ref": None,
        "payout_ref": None,
        "refund_ref": None,
        "created_at": "2026-10-20T10:20:00Z",
        "updated_at": "2026-10-20T10:20:01Z",
    },
    {
        "id": 1005,
        "job": 2005,
        "seller": "sel_nova",
        "amount_cents": 2000,
        "status": "blocked",
        "decision": decision(
            "block", 97, "high",
            "Blocked: the recipient changed from Nova Scripts to a different account "
            "in the middle of the job.",
            hard_rule="recipient_changed",
            hits={
                "recipient_changed": "Payout account differs from the one agreed at the start of the job.",
                "pressure_language": "The message asked to skip the review.",
            },
        ),
        "history": [
            ("proposed", "2026-10-20T10:40:00Z", "Buyer Agent proposed paying $20.00 (recipient changed)."),
            ("blocked", "2026-10-20T10:40:01Z", "Guard blocked: recipient changed mid-job."),
        ],
        "funding_ref": None,
        "payout_ref": None,
        "refund_ref": None,
        "created_at": "2026-10-20T10:40:00Z",
        "updated_at": "2026-10-20T10:40:01Z",
    },
    {
        "id": 1006,
        "job": 2006,
        "seller": "sel_quick",
        "amount_cents": 2000,
        "status": "refunded",
        "decision": decision(
            "approve", 22, "low",
            "Approved: $20.00 was within QuickPay Dev's limit at the time "
            "and the job matched your request.",
        ),
        "history": [
            ("proposed", "2026-10-19T16:00:00Z", "Buyer Agent proposed paying $20.00 to QuickPay Dev."),
            ("approved", "2026-10-19T16:00:02Z", "Guard approved (low risk)."),
            ("held", "2026-10-19T16:00:05Z", "Funds secured."),
            ("refunded", "2026-10-19T16:20:00Z", "3 of 8 tests passed. You were refunded."),
        ],
        "funding_ref": "MOCK-FUND-1006",
        "payout_ref": None,
        "refund_ref": "MOCK-REFUND-1006",
        "created_at": "2026-10-19T16:00:00Z",
        "updated_at": "2026-10-19T16:20:00Z",
    },
]


# The audit trail from frontend/src/lib/mock-data.ts, so the Audit Trail screen
# is not empty on a fresh database. (id, payment, time, actor, action, verdict, reason, details)
AUDIT = [
    (1, 1001, "2026-10-20T09:00:00Z", "buyer_agent", "Proposed a payment", None,
     "Proposed $20.00 to Nova Scripts for the CSV script job.", {"amount_cents": 2000}),
    (2, 1001, "2026-10-20T09:00:02Z", "guard", "Reviewed the payment", "approve",
     "Within limits, matches the request, trusted seller.", {"risk_score": 6}),
    (3, 1001, "2026-10-20T09:00:05Z", "system", "Secured funds", None,
     "Funds secured in escrow.", {}),
    (4, 1001, "2026-10-20T09:12:30Z", "verifier", "Checked the work", None,
     "8 of 8 tests passed.", {"passed": 8, "total": 8}),
    (5, 1001, "2026-10-20T09:12:41Z", "system", "Released payment", None,
     "Nova Scripts was paid $20.00.", {}),
    (6, 1003, "2026-10-20T10:00:00Z", "buyer_agent", "Proposed a payment", None,
     "Proposed $25.00 to Zed Dev.", {"amount_cents": 2500}),
    (7, 1003, "2026-10-20T10:00:03Z", "guard", "Reviewed the payment", "ask",
     "New seller with no history, and the amount is above their limit.", {"risk_score": 48}),
    (8, 1004, "2026-10-20T10:20:01Z", "guard", "Reviewed the payment", "block",
     "$500.00 is above the $50.00 per-job cap.", {"hard_rule": "over_cap"}),
    (9, 1005, "2026-10-20T10:40:01Z", "guard", "Reviewed the payment", "block",
     "Recipient changed mid-job.", {"hard_rule": "recipient_changed"}),
    (10, 1006, "2026-10-19T16:20:00Z", "verifier", "Checked the work", None,
     "3 of 8 tests passed. The work did not meet the agreed tests.", {"passed": 3, "total": 8}),
    (11, 1006, "2026-10-19T16:20:01Z", "system", "Refunded the buyer", None,
     "Payment refunded to Amara.", {}),
    (12, 1006, "2026-10-19T16:20:02Z", "system", "Lowered trust", None,
     "QuickPay Dev's trust score dropped from 31 to 9 and the limit fell to $5.00.",
     {"old_score": 31, "new_score": 9}),
]
