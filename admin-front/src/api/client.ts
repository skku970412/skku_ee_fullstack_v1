import type {
  AdminLoginResponse,
  DeleteReservationResponse,
  SessionsResponse,
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
    // ignore parse errors
  }
  const text = await res.text();
  return text || `요청이 실패했습니다. (status ${res.status})`;
}

export async function loginAdmin(email: string, password: string): Promise<AdminLoginResponse> {
  const res = await fetch(`${API_BASE}/api/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    throw new Error(await extractError(res));
  }
  return (await res.json()) as AdminLoginResponse;
}

export async function listReservationsBySession(
  dateISO: string,
  token: string
): Promise<SessionsResponse> {
  const res = await fetch(
    `${API_BASE}/api/admin/reservations/by-session?date=${encodeURIComponent(dateISO)}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
  if (!res.ok) {
    throw new Error(await extractError(res));
  }
  return (await res.json()) as SessionsResponse;
}

export async function deleteReservation(
  id: string,
  token: string
): Promise<DeleteReservationResponse> {
  const res = await fetch(`${API_BASE}/api/admin/reservations/${id}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) {
    throw new Error(await extractError(res));
  }
  return (await res.json()) as DeleteReservationResponse;
}
