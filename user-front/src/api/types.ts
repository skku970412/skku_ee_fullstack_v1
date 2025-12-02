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

export interface LoginResponse {
  token: string;
  user: { email: string };
}

export interface VerifySlotPayload {
  plate: string;
  date: string;
  startTime: string;
  endTime: string;
  sessionId: number;
}

export interface VerifySlotResponse {
  valid: boolean;
  conflict: boolean;
  message: string;
}

export interface CreateReservationPayload {
  sessionId: number;
  plate: string;
  date: string;
  startTime: string;
  endTime: string;
  contactEmail: string;
}

export interface CreateReservationBatchPayload {
  sessionId: number;
  plate: string;
  date: string;
  startTimes: string[];
  contactEmail?: string;
}

export interface BatteryStatus {
  percent?: number | null;
  voltage?: number | null;
  timestamp?: string | null;
}
