export type ReservationStatus =
  | "CONFIRMED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED";

export interface Reservation {
  id: string;
  sessionId: number;
  plate: string;
  date: string;
  startTime: string;
  endTime: string;
  status: ReservationStatus;
  contactEmail?: string | null;
}

export interface SessionReservations {
  sessionId: number;
  name: string;
  reservations: Reservation[];
}

export interface SessionsResponse {
  sessions: SessionReservations[];
}

export interface AdminLoginResponse {
  token: string;
  admin: { email: string };
}

export interface DeleteReservationResponse {
  ok: boolean;
}
