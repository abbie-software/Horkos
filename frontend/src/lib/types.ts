// Horkos shared types. These mirror docs/api-contract.md.
// Money is always an integer number of cents. Timestamps are ISO 8601 UTC strings.

export type Verdict = "approve" | "block" | "ask";
export type RiskLevel = "low" | "medium" | "high";

export type PaymentStatus =
  | "proposed"
  | "awaiting_user"
  | "approved"
  | "held"
  | "verified"
  | "released"
  | "refunded"
  | "blocked";

export type SellerTier = "new" | "building" | "trusted" | "restricted";

export type SignalCode =
  | "intent_mismatch"
  | "recipient_changed"
  | "edge_of_limit"
  | "velocity"
  | "unproven_seller"
  | "pressure_language";

export type HardRuleCode =
  | "recipient_changed"
  | "over_cap"
  | "excluded_category"
  | "blocklisted_or_low_trust";

export type AttackType =
  | "recipient_change"
  | "over_limit"
  | "edge_of_limit"
  | "rapid_retries"
  | "pressure_language"
  | "bad_work";

export type Actor = "user" | "buyer_agent" | "guard" | "verifier" | "system";

export type EventType =
  | "payment.proposed"
  | "payment.verdict"
  | "payment.status_changed"
  | "verification.result"
  | "trust.updated"
  | "demo.attack_started"
  | "demo.reset";

export type JobStatus =
  | "open"
  | "awaiting_work"
  | "verifying"
  | "completed"
  | "failed"
  | "cancelled";

export interface User {
  id: string;
  name: string;
  email: string;
}

export interface Policy {
  per_job_cap_cents: number;
  daily_cap_cents: number;
  ask_threshold_cents: number;
  allowed_categories: string[];
  blocked_categories: string[];
  ask_for_new_sellers: boolean;
}

export interface Oath {
  id: string;
  raw_text: string; // what the user typed, in plain English
  policy: Policy; // what Horkos understood and will enforce
  updated_at: string;
}

export interface Seller {
  id: string;
  name: string;
  paypal_email: string; // sandbox account
  trust_score: number; // 0 to 100
  tier: SellerTier;
  limit_cents: number; // current trust-based spending limit
  jobs_completed: number;
  jobs_failed: number;
  last_activity_at: string | null;
}

export interface Signal {
  code: SignalCode;
  triggered: boolean;
  detail: string;
}

export interface Decision {
  verdict: Verdict;
  risk_score: number; // 0 to 100
  risk_level: RiskLevel;
  reason: string; // plain English, shown to the user
  hard_rule: HardRuleCode | null; // set when a hard rule decided the outcome
  signals: Signal[]; // always all six, triggered or not
}

export interface Transition {
  status: PaymentStatus;
  at: string;
  note: string;
}

export interface PaypalRefs {
  funding_ref: string | null;
  payout_ref: string | null;
  refund_ref: string | null;
}

export interface Payment {
  id: string;
  job_id: string;
  seller_id: string;
  seller_name: string;
  amount_cents: number;
  currency: "USD";
  status: PaymentStatus;
  decision: Decision;
  history: Transition[];
  paypal: PaypalRefs;
  approve_url?: string | null; // set only while a payment waits for funding (sandbox mode)
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: string;
  request_text: string;
  category: string;
  status: JobStatus;
  seller_id: string;
  payment_id: string;
  acceptance_tests: string[]; // plain-English description of what must pass
  created_at: string;
}

export interface TestResult {
  passed: number;
  failed: number;
  total: number;
  duration_ms: number;
  output_excerpt: string;
}

export interface AuditEntry {
  id: string;
  payment_id: string;
  at: string;
  actor: Actor;
  action: string;
  verdict: Verdict | null;
  reason: string;
  details: Record<string, unknown>;
}

export interface HorkosEvent {
  id: string;
  type: EventType;
  at: string;
  payment_id: string | null;
  seller_id: string | null;
  message: string; // ready to show in the Live Feed
  payload: Record<string, unknown>;
}

export interface ListResponse<T> {
  items: T[];
  total: number;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}

export interface CreateJobResponse {
  job: Job;
  payment: Payment;
}

export interface SubmissionResponse {
  submission_id: string;
  status: "verifying";
  payment_id: string;
}

export interface AttackResponse {
  attack_id: string;
  type: AttackType;
  status: "started";
}

export interface ApiError {
  error: { code: string; message: string };
}