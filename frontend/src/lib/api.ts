// One place for every call to the backend.
// With NEXT_PUBLIC_USE_MOCKS=true (the default) it returns fake data, so you can
// build every screen without waiting for the server. Set it to "false" to go live.

import {
  mockAudit,
  mockEvents,
  mockJob,
  mockOath,
  mockPayments,
  mockSellers,
  mockUser,
} from "./mock-data";
import type {
  ApiError,
  AttackResponse,
  AttackType,
  AuditEntry,
  CreateJobResponse,
  HorkosEvent,
  Job,
  ListResponse,
  LoginResponse,
  Oath,
  Payment,
  Seller,
  SubmissionResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS !== "false";

let token: string | null = null;
export function setToken(value: string | null) {
  token = value;
}
let unauthorizedHandler: (() => void) | null = null;
export function setUnauthorizedHandler(fn: (() => void) | null) {
  unauthorizedHandler = fn;
}

const wait = (ms = 300) => new Promise((resolve) => setTimeout(resolve, ms));

export function formatUSD(cents: number): string {
  return (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });
}

export class ApiRequestError extends Error {
  status: number;
  code: string | null;
  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
    if (!res.ok) {
          if (res.status === 401 && path !== "/auth/login") unauthorizedHandler?.();
    let message = `Request failed (${res.status})`;
    let code: string | null = null;
    try {
      const body = (await res.json()) as ApiError;
      if (body?.error?.message) message = body.error.message;
      if (body?.error?.code) code = body.error.code;
    } catch {
      // keep the default message
    }
    throw new ApiRequestError(message, res.status, code);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---------- Auth ----------
export async function login(email: string, password: string): Promise<LoginResponse> {
  if (USE_MOCKS) {
    await wait();
    return { access_token: "mock-token", token_type: "bearer", user: mockUser };
  }
  const result = await request<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(result.access_token);
  return result;
}

// ---------- Oath ----------
export async function getOath(): Promise<Oath> {
  if (USE_MOCKS) {
    await wait();
    return mockOath;
  }
  return request<Oath>("/oath");
}

export async function saveOath(rawText: string): Promise<Oath> {
  if (USE_MOCKS) {
    await wait(600);
    return { ...mockOath, raw_text: rawText, updated_at: new Date().toISOString() };
  }
  return request<Oath>("/oath", { method: "PUT", body: JSON.stringify({ raw_text: rawText }) });
}

// ---------- Jobs and payments ----------
export async function createJob(requestText: string, sellerId?: string): Promise<CreateJobResponse> {
  if (USE_MOCKS) {
    await wait(800);
    return {
      job: { ...mockJob, request_text: requestText, seller_id: sellerId ?? mockJob.seller_id },
      payment: mockPayments[2],
    };
  }
  return request<CreateJobResponse>("/jobs", {
    method: "POST",
    body: JSON.stringify({ request_text: requestText, seller_id: sellerId }),
  });
}

export async function getPayments(): Promise<ListResponse<Payment>> {
  if (USE_MOCKS) {
    await wait();
    return { items: mockPayments, total: mockPayments.length };
  }
  return request<ListResponse<Payment>>("/payments");
}

export async function getPayment(id: string): Promise<Payment> {
  if (USE_MOCKS) {
    await wait();
    const found = mockPayments.find((p) => p.id === id);
    if (!found) throw new Error("Payment not found");
    return found;
  }
  return request<Payment>(`/payments/${id}`);
}

export async function decidePayment(id: string, decision: "approve" | "reject"): Promise<Payment> {
  if (USE_MOCKS) {
    await wait(500);
    const found = mockPayments.find((p) => p.id === id);
    if (!found) throw new Error("Payment not found");
    if (decision === "reject") return { ...found, status: "blocked" };
    return {
      ...found,
      status: "approved",
      paypal: { ...found.paypal, approve_url: `/funding/return?payment=${id}` },
    };  }
  return request<Payment>(`/payments/${id}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision }),
  });
}

export async function submitWork(jobId: string, sellerId: string, content: string): Promise<SubmissionResponse> {
  if (USE_MOCKS) {
    await wait(500);
    return { submission_id: "sub_demo", status: "verifying", payment_id: "pay_1002" };
  }
  return request<SubmissionResponse>(`/jobs/${jobId}/submission`, {
    method: "POST",
    body: JSON.stringify({ seller_id: sellerId, content }),
  });
}

// ---------- Trust Board and Audit Trail ----------
export async function getSellers(): Promise<ListResponse<Seller>> {
  if (USE_MOCKS) {
    await wait();
    return { items: mockSellers, total: mockSellers.length };
  }
  return request<ListResponse<Seller>>("/sellers");
}

export async function getAudit(paymentId?: string): Promise<ListResponse<AuditEntry>> {
  if (USE_MOCKS) {
    await wait();
    const items = paymentId ? mockAudit.filter((a) => a.payment_id === paymentId) : mockAudit;
    return { items, total: items.length };
  }
  const query = paymentId ? `?payment_id=${encodeURIComponent(paymentId)}` : "";
  return request<ListResponse<AuditEntry>>(`/audit${query}`);
}

// ---------- Demo controls ----------
export async function triggerAttack(type: AttackType): Promise<AttackResponse> {
  if (USE_MOCKS) {
    await wait(400);
    return { attack_id: "atk_demo", type, status: "started" };
  }
  return request<AttackResponse>(`/demo/attack/${type}`, { method: "POST" });
}

// Remembers where the fake story is, so every event id stays unique
let mockEventCursor = 0;
let mockEventSerial = 0;

export function restartMockEvents(): void {
  mockEventCursor = 0;
}

export async function resetDemo(): Promise<void> {
  if (USE_MOCKS) {
    await wait(400);
    mockEventCursor = 0;
    return;
  }
  await request<void>("/demo/reset", { method: "POST" });
}

// ---------- Live Feed ----------
// Call this inside useEffect and return the result as the cleanup function.
// Real mode: Server-Sent Events (runs until you leave the page).
// Mock mode: plays the 8-event story once, then stops and calls onEnd.
export function subscribeToEvents(
  onEvent: (event: HorkosEvent) => void,
  onEnd?: () => void
): () => void {
  if (USE_MOCKS) {
    const timer = setInterval(() => {
      if (mockEventCursor >= mockEvents.length) {
        clearInterval(timer);
        onEnd?.();
        return;
      }
      const base = mockEvents[mockEventCursor];
      mockEventCursor += 1;
      mockEventSerial += 1;
      onEvent({
        ...base,
        id: `${base.id}_${mockEventSerial}`,
        at: new Date().toISOString(),
      });
    }, 2500);
    return () => clearInterval(timer);
  }
  // EventSource cannot send headers, so the token goes in the query string.
  const source = new EventSource(
    `${API_URL}/events?token=${encodeURIComponent(token ?? "")}`
  );
  source.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data) as HorkosEvent);
    } catch {
      // ignore malformed events
    }
  };
  return () => source.close();
}


export async function getJobs(sellerId: string): Promise<ListResponse<Job>> {
  if (USE_MOCKS) {
    await wait(300);
    const base: Job = {
      id: "job_2002",
      request_text: "Write a Python function that converts a CSV file into JSON.",
      category: "coding",
      status: "awaiting_work",
      seller_id: "sel_kip",
      payment_id: "pay_1002",
      acceptance_tests: [
        "Function csv_to_json(path) converts a simple CSV with a header row",
        "Handles empty fields",
        "Raises a clear error on an empty file",
      ],
      created_at: "2026-10-20T09:00:00Z",
    };
    const other: Job = {
      ...base,
      id: "job_2004",
      seller_id: "sel_nova",
      payment_id: "pay_1004",
      request_text: "Write a Python function that removes duplicate rows from a list of dictionaries.",
      acceptance_tests: [
        "Function dedupe_rows(rows) keeps the first copy of each duplicate",
        "Keeps the original order",
        "Returns an empty list for an empty input",
      ],
    };
    const items = [base, other].filter((j) => j.seller_id === sellerId);
    return { items, total: items.length };
  }
    return request<ListResponse<Job>>(`/jobs?status=awaiting_work`);
}

// POST /payments/{id}/funding/confirm. Call it when the buyer returns from PayPal.
export async function confirmFunding(id: string): Promise<Payment> {
  if (USE_MOCKS) {
    await wait(700);
    const found = mockPayments.find((p) => p.id === id);
    if (!found) throw new Error("Payment not found");
    return {
      ...found,
      status: "held",
      paypal: { ...found.paypal, funding_ref: `MOCK-FUND-${id}`, approve_url: null },
    };
  }
  return request<Payment>(`/payments/${id}/funding/confirm`, { method: "POST" });
}

export interface SignupBody {
  name: string;
  email: string;
  password: string;
  role?: "buyer" | "seller";
  paypal_email?: string;
}

export async function signup(body: SignupBody): Promise<LoginResponse> {
  if (USE_MOCKS) {
    await wait(500);
    const role = body.role ?? "buyer";
    setToken("mock-token");
    return {
      access_token: "mock-token",
      token_type: "bearer",
      user: { ...mockUser, name: body.name, email: body.email, role, seller_id: role === "seller" ? "sel_new" : null },
    };
  }
  const result = await request<LoginResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(body),
  });
  setToken(result.access_token);
  return result;
}