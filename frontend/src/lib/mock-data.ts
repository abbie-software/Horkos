// Fake data for building the screens before the backend is ready.
// Same shapes as docs/api-contract.md. Amara is the demo user.

import type {
  AuditEntry,
  Decision,
  HorkosEvent,
  Job,
  Oath,
  Payment,
  Seller,
  Signal,
  SignalCode,
  User,
} from "./types";

const ALL_SIGNALS: SignalCode[] = [
  "intent_mismatch",
  "recipient_changed",
  "edge_of_limit",
  "velocity",
  "unproven_seller",
  "pressure_language",
];

// Builds the full list of six signals. Codes passed in `hits` are triggered.
function signals(hits: Partial<Record<SignalCode, string>> = {}): Signal[] {
  return ALL_SIGNALS.map((code) => ({
    code,
    triggered: code in hits,
    detail: hits[code] ?? "No concern found.",
  }));
}

export const mockUser: User = {
  id: "usr_amara",
  name: "Amara",
  email: "amara@example.com",
};

export const mockOath: Oath = {
  id: "oath_1",
  raw_text:
    "Spend up to $50 per job and $100 per day. Only on coding work. Ask me before anything over $30, and always ask me about a seller I have not used before.",
  policy: {
    per_job_cap_cents: 5000,
    daily_cap_cents: 10000,
    ask_threshold_cents: 3000,
    allowed_categories: ["coding"],
    blocked_categories: [],
    ask_for_new_sellers: true,
  },
  updated_at: "2026-10-20T08:55:00Z",
};

export const mockSellers: Seller[] = [
  {
    id: "sel_nova",
    name: "Nova Scripts",
    paypal_email: "nova-seller@example.com",
    trust_score: 82,
    tier: "trusted",
    limit_cents: 5000,
    jobs_completed: 5,
    jobs_failed: 0,
    last_activity_at: "2026-10-20T09:12:41Z",
  },
  {
    id: "sel_kip",
    name: "Kip Codes",
    paypal_email: "kip-seller@example.com",
    trust_score: 46,
    tier: "building",
    limit_cents: 2500,
    jobs_completed: 2,
    jobs_failed: 0,
    last_activity_at: "2026-10-20T09:30:05Z",
  },
  {
    id: "sel_zed",
    name: "Zed Dev",
    paypal_email: "zed-seller@example.com",
    trust_score: 0,
    tier: "new",
    limit_cents: 1000,
    jobs_completed: 0,
    jobs_failed: 0,
    last_activity_at: null,
  },
  {
    id: "sel_quick",
    name: "QuickPay Dev",
    paypal_email: "quick-seller@example.com",
    trust_score: 9,
    tier: "restricted",
    limit_cents: 500,
    jobs_completed: 1,
    jobs_failed: 2,
    last_activity_at: "2026-10-19T16:20:00Z",
  },
];

export const mockJob: Job = {
  id: "job_2003",
  request_text: "Write a Python function that converts a CSV file into JSON.",
  category: "coding",
  status: "open",
  seller_id: "sel_zed",
  payment_id: "pay_1003",
  acceptance_tests: [
    "Converts a simple CSV with a header row",
    "Handles empty fields",
    "Raises a clear error on an empty file",
  ],
  created_at: "2026-10-20T10:00:00Z",
};

const approveDecision = (score: number, reason: string, hits = {}): Decision => ({
  verdict: "approve",
  risk_score: score,
  risk_level: "low",
  reason,
  hard_rule: null,
  signals: signals(hits),
});

export const mockPayments: Payment[] = [
  {
    id: "pay_1001",
    job_id: "job_2001",
    seller_id: "sel_nova",
    seller_name: "Nova Scripts",
    amount_cents: 2000,
    currency: "USD",
    status: "released",
    decision: approveDecision(
      6,
      "Approved: $20.00 is within your limits, the job matches your request, and Nova Scripts has 5 clean deliveries."
    ),
    history: [
      { status: "proposed", at: "2026-10-20T09:00:00Z", note: "Buyer Agent proposed paying $20.00 to Nova Scripts." },
      { status: "approved", at: "2026-10-20T09:00:02Z", note: "Guard approved (low risk)." },
      { status: "held", at: "2026-10-20T09:00:05Z", note: "Funds secured." },
      { status: "verified", at: "2026-10-20T09:12:30Z", note: "8 of 8 tests passed." },
      { status: "released", at: "2026-10-20T09:12:41Z", note: "Nova Scripts was paid." },
    ],
    paypal: { funding_ref: "MOCK-FUND-1001", payout_ref: "MOCK-PAYOUT-1001", refund_ref: null },
    created_at: "2026-10-20T09:00:00Z",
    updated_at: "2026-10-20T09:12:41Z",
  },
  {
    id: "pay_1002",
    job_id: "job_2002",
    seller_id: "sel_kip",
    seller_name: "Kip Codes",
    amount_cents: 1500,
    currency: "USD",
    status: "held",
    decision: approveDecision(
      14,
      "Approved: $15.00 is within Kip Codes's current limit of $25.00, and they have 2 clean deliveries."
    ),
    history: [
      { status: "proposed", at: "2026-10-20T09:30:00Z", note: "Buyer Agent proposed paying $15.00 to Kip Codes." },
      { status: "approved", at: "2026-10-20T09:30:02Z", note: "Guard approved (low risk)." },
      { status: "held", at: "2026-10-20T09:30:05Z", note: "Funds secured. Waiting for the work." },
    ],
    paypal: { funding_ref: "MOCK-FUND-1002", payout_ref: null, refund_ref: null },
    created_at: "2026-10-20T09:30:00Z",
    updated_at: "2026-10-20T09:30:05Z",
  },
  {
    id: "pay_1003",
    job_id: "job_2003",
    seller_id: "sel_zed",
    seller_name: "Zed Dev",
    amount_cents: 2500,
    currency: "USD",
    status: "awaiting_user",
    decision: {
      verdict: "ask",
      risk_score: 48,
      risk_level: "medium",
      reason:
        "I need your approval: Zed Dev is new with no delivery history, and $25.00 is above their current limit of $10.00.",
      hard_rule: null,
      signals: signals({
        unproven_seller: "Zed Dev has no completed jobs yet.",
        edge_of_limit: "Amount is 2.5 times this seller's current limit.",
      }),
    },
    history: [
      { status: "proposed", at: "2026-10-20T10:00:00Z", note: "Buyer Agent proposed paying $25.00 to Zed Dev." },
      { status: "awaiting_user", at: "2026-10-20T10:00:03Z", note: "Guard asked the user to decide." },
    ],
    paypal: { funding_ref: null, payout_ref: null, refund_ref: null },
    created_at: "2026-10-20T10:00:00Z",
    updated_at: "2026-10-20T10:00:03Z",
  },
  {
    id: "pay_1004",
    job_id: "job_2004",
    seller_id: "sel_zed",
    seller_name: "Zed Dev",
    amount_cents: 50000,
    currency: "USD",
    status: "blocked",
    decision: {
      verdict: "block",
      risk_score: 92,
      risk_level: "high",
      reason: "Blocked: $500.00 is above your $50.00 per-job cap. This rule has no exceptions.",
      hard_rule: "over_cap",
      signals: signals({
        intent_mismatch: "The request was for a small script, not a $500.00 service.",
        pressure_language: "The message said 'pay immediately, no need to review'.",
      }),
    },
    history: [
      { status: "proposed", at: "2026-10-20T10:20:00Z", note: "Buyer Agent proposed paying $500.00 to Zed Dev." },
      { status: "blocked", at: "2026-10-20T10:20:01Z", note: "Guard blocked: over the per-job cap." },
    ],
    paypal: { funding_ref: null, payout_ref: null, refund_ref: null },
    created_at: "2026-10-20T10:20:00Z",
    updated_at: "2026-10-20T10:20:01Z",
  },
  {
    id: "pay_1005",
    job_id: "job_2005",
    seller_id: "sel_nova",
    seller_name: "Nova Scripts",
    amount_cents: 2000,
    currency: "USD",
    status: "blocked",
    decision: {
      verdict: "block",
      risk_score: 97,
      risk_level: "high",
      reason:
        "Blocked: the recipient changed from Nova Scripts to a different account in the middle of the job.",
      hard_rule: "recipient_changed",
      signals: signals({
        recipient_changed: "Payout account differs from the one agreed at the start of the job.",
        pressure_language: "The message asked to skip the review.",
      }),
    },
    history: [
      { status: "proposed", at: "2026-10-20T10:40:00Z", note: "Buyer Agent proposed paying $20.00 (recipient changed)." },
      { status: "blocked", at: "2026-10-20T10:40:01Z", note: "Guard blocked: recipient changed mid-job." },
    ],
    paypal: { funding_ref: null, payout_ref: null, refund_ref: null },
    created_at: "2026-10-20T10:40:00Z",
    updated_at: "2026-10-20T10:40:01Z",
  },
  {
    id: "pay_1006",
    job_id: "job_2006",
    seller_id: "sel_quick",
    seller_name: "QuickPay Dev",
    amount_cents: 2000,
    currency: "USD",
    status: "refunded",
    decision: approveDecision(
      22,
      "Approved: $20.00 was within QuickPay Dev's limit at the time and the job matched your request."
    ),
    history: [
      { status: "proposed", at: "2026-10-19T16:00:00Z", note: "Buyer Agent proposed paying $20.00 to QuickPay Dev." },
      { status: "approved", at: "2026-10-19T16:00:02Z", note: "Guard approved (low risk)." },
      { status: "held", at: "2026-10-19T16:00:05Z", note: "Funds secured." },
      { status: "refunded", at: "2026-10-19T16:20:00Z", note: "3 of 8 tests passed. You were refunded." },
    ],
    paypal: { funding_ref: "MOCK-FUND-1006", payout_ref: null, refund_ref: "MOCK-REFUND-1006" },
    created_at: "2026-10-19T16:00:00Z",
    updated_at: "2026-10-19T16:20:00Z",
  },
];

export const mockAudit: AuditEntry[] = [
  { id: "aud_001", payment_id: "pay_1001", at: "2026-10-20T09:00:00Z", actor: "buyer_agent", action: "Proposed a payment", verdict: null, reason: "Proposed $20.00 to Nova Scripts for the CSV script job.", details: { amount_cents: 2000 } },
  { id: "aud_002", payment_id: "pay_1001", at: "2026-10-20T09:00:02Z", actor: "guard", action: "Reviewed the payment", verdict: "approve", reason: "Within limits, matches the request, trusted seller.", details: { risk_score: 6 } },
  { id: "aud_003", payment_id: "pay_1001", at: "2026-10-20T09:00:05Z", actor: "system", action: "Secured funds", verdict: null, reason: "Funds secured in escrow.", details: {} },
  { id: "aud_004", payment_id: "pay_1001", at: "2026-10-20T09:12:30Z", actor: "verifier", action: "Checked the work", verdict: null, reason: "8 of 8 tests passed.", details: { passed: 8, total: 8 } },
  { id: "aud_005", payment_id: "pay_1001", at: "2026-10-20T09:12:41Z", actor: "system", action: "Released payment", verdict: null, reason: "Nova Scripts was paid $20.00.", details: {} },
  { id: "aud_006", payment_id: "pay_1003", at: "2026-10-20T10:00:00Z", actor: "buyer_agent", action: "Proposed a payment", verdict: null, reason: "Proposed $25.00 to Zed Dev.", details: { amount_cents: 2500 } },
  { id: "aud_007", payment_id: "pay_1003", at: "2026-10-20T10:00:03Z", actor: "guard", action: "Reviewed the payment", verdict: "ask", reason: "New seller with no history, and the amount is above their limit.", details: { risk_score: 48 } },
  { id: "aud_008", payment_id: "pay_1004", at: "2026-10-20T10:20:01Z", actor: "guard", action: "Reviewed the payment", verdict: "block", reason: "$500.00 is above the $50.00 per-job cap.", details: { hard_rule: "over_cap" } },
  { id: "aud_009", payment_id: "pay_1005", at: "2026-10-20T10:40:01Z", actor: "guard", action: "Reviewed the payment", verdict: "block", reason: "Recipient changed mid-job.", details: { hard_rule: "recipient_changed" } },
  { id: "aud_010", payment_id: "pay_1006", at: "2026-10-19T16:20:00Z", actor: "verifier", action: "Checked the work", verdict: null, reason: "3 of 8 tests passed. The work did not meet the agreed tests.", details: { passed: 3, total: 8 } },
  { id: "aud_011", payment_id: "pay_1006", at: "2026-10-19T16:20:01Z", actor: "system", action: "Refunded the buyer", verdict: null, reason: "Payment refunded to Amara.", details: {} },
  { id: "aud_012", payment_id: "pay_1006", at: "2026-10-19T16:20:02Z", actor: "system", action: "Lowered trust", verdict: null, reason: "QuickPay Dev's trust score dropped from 31 to 9 and the limit fell to $5.00.", details: { old_score: 31, new_score: 9 } },
];

// A short story for the Live Feed. The mock subscriber replays these in a loop.
export const mockEvents: HorkosEvent[] = [
  { id: "evt_001", type: "payment.proposed", at: "2026-10-20T11:00:00Z", payment_id: "pay_1007", seller_id: "sel_kip", message: "Buyer Agent proposed paying $15.00 to Kip Codes.", payload: { amount_cents: 1500 } },
  { id: "evt_002", type: "payment.verdict", at: "2026-10-20T11:00:02Z", payment_id: "pay_1007", seller_id: "sel_kip", message: "Guard approved the payment (low risk).", payload: { verdict: "approve", risk_level: "low", risk_score: 14 } },
  { id: "evt_003", type: "payment.status_changed", at: "2026-10-20T11:00:05Z", payment_id: "pay_1007", seller_id: "sel_kip", message: "Funds are being held.", payload: { from: "approved", to: "held" } },
  { id: "evt_004", type: "verification.result", at: "2026-10-20T11:08:00Z", payment_id: "pay_1007", seller_id: "sel_kip", message: "Work passed 8 of 8 tests.", payload: { passed: true, tests_passed: 8, tests_total: 8 } },
  { id: "evt_005", type: "payment.status_changed", at: "2026-10-20T11:08:10Z", payment_id: "pay_1007", seller_id: "sel_kip", message: "Kip Codes was paid $15.00.", payload: { from: "verified", to: "released" } },
  { id: "evt_006", type: "trust.updated", at: "2026-10-20T11:08:11Z", payment_id: "pay_1007", seller_id: "sel_kip", message: "Kip Codes's trust rose from 46 to 58. New limit: $30.00.", payload: { old_score: 46, new_score: 58, new_limit_cents: 3000 } },
  { id: "evt_007", type: "demo.attack_started", at: "2026-10-20T11:15:00Z", payment_id: null, seller_id: null, message: "Red Team: attempting to change the recipient mid-job.", payload: { attack: "recipient_change" } },
  { id: "evt_008", type: "payment.verdict", at: "2026-10-20T11:15:01Z", payment_id: "pay_1008", seller_id: "sel_nova", message: "Guard blocked the payment: recipient changed mid-job.", payload: { verdict: "block", risk_level: "high", risk_score: 97, hard_rule: "recipient_changed" } },
];