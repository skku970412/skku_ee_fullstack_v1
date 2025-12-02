import {
  CreateReservationPayload,
  LoginResponse,
  Reservation,
  SessionsResponse,
  VerifySlotPayload,
  VerifySlotResponse,
  CreateReservationBatchPayload,
  BatteryStatus,
} from "./types";

const DEFAULT_API_BASE =
  import.meta.env.VITE_API_BASE ??
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://localhost:8000");

export const API_BASE = DEFAULT_API_BASE.replace(/\/$/, "");

async function extractError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail) && data.detail.length > 0) {
      const first = data.detail[0];
      if (typeof first?.msg === "string") return first.msg;
    }
    if (typeof data?.message === "string") return data.message;
  } catch {
    // ignore JSON parse errors
  }
  const text = await res.text();
  return text || `Request failed (status ${res.status}).`;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/api/user/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(await extractError(res));
  return (await res.json()) as LoginResponse;
}

export async function listReservationsBySession(dateISO: string): Promise<SessionsResponse> {
  const res = await fetch(
    `${API_BASE}/api/reservations/by-session?date=${encodeURIComponent(dateISO)}`
  );
  if (!res.ok) throw new Error(await extractError(res));
  return (await res.json()) as SessionsResponse;
}

export async function verifySlot(payload: VerifySlotPayload): Promise<VerifySlotResponse> {
  const res = await fetch(`${API_BASE}/api/plates/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await extractError(res));
  return (await res.json()) as VerifySlotResponse;
}

export async function lookupPlate(plate: string): Promise<Reservation[]> {
  const res = await fetch(`${API_BASE}/api/reservations/my?plate=${encodeURIComponent(plate)}`);
  if (!res.ok) throw new Error(await extractError(res));
  return (await res.json()) as Reservation[];
}

export async function createReservation(payload: CreateReservationPayload): Promise<Reservation> {
  const res = await fetch(`${API_BASE}/api/reservations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await extractError(res));
  return (await res.json()) as Reservation;
}

export async function createReservationsBatch(payload: CreateReservationBatchPayload): Promise<Reservation[]> {
  const res = await fetch(`${API_BASE}/api/reservations/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await extractError(res));
  return (await res.json()) as Reservation[];
}

export async function myReservations(email: string): Promise<Reservation[]> {
  const res = await fetch(
    `${API_BASE}/api/reservations/my?email=${encodeURIComponent(email.toLowerCase())}`
  );
  if (!res.ok) throw new Error(await extractError(res));
  return (await res.json()) as Reservation[];
}

export async function deleteReservation(id: string, email: string): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/reservations/${id}?email=${encodeURIComponent(email.toLowerCase())}`,
    { method: "DELETE" }
  );
  if (!res.ok) throw new Error(await extractError(res));
}

export async function recognizePlate(image: Blob): Promise<{ plate: string; [k: string]: any }> {
  const makeForm = () => {
    const form = new FormData();
    form.append("image", image, "capture.jpg");
    return form;
  };

  const endpoints = [
    {
      url: `${API_BASE}/api/license-plates`,
      fallbackStatuses: new Set([404, 405]),
    },
    {
      url: `${API_BASE}/api/plates/recognize`,
      fallbackStatuses: new Set<number>(),
    },
  ] as const;

  let lastError: Error | null = null;

  for (const { url, fallbackStatuses } of endpoints) {
    let response: Response;
    try {
      response = await fetch(url, {
        method: "POST",
        body: makeForm(),
      });
    } catch (error) {
      if (error instanceof Error) {
        lastError = error;
        continue;
      }
      throw error;
    }

    if (response.ok) {
      return (await response.json()) as { plate: string; [k: string]: any };
    }

    const message = await extractError(response);
    if (fallbackStatuses.has(response.status)) {
      lastError = new Error(message);
      continue;
    }

    throw new Error(message);
  }

  throw lastError ?? new Error("Plate recognition request failed.");
}

export async function getBatteryStatus(): Promise<BatteryStatus> {
  const res = await fetch(`${API_BASE}/api/battery/now`);
  if (!res.ok) throw new Error(await extractError(res));
  return (await res.json()) as BatteryStatus;
}
