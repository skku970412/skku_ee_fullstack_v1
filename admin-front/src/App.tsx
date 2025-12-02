import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";

import Header from "./components/ui/Header";
import LoginPage from "./pages/Login";
import DashboardPage from "./pages/Dashboard";
import {
  deleteReservation,
  listReservationsBySession,
  loginAdmin,
} from "./api/client";
import type { SessionReservations } from "./api/types";
import { slotsOfDay } from "./utils/time";

type Step = 1 | 2;

export default function App() {
  const [step, setStep] = useState<Step>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(null);

  const todayISO = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const [date, setDate] = useState<string>(todayISO);

  const [sessions, setSessions] = useState<SessionReservations[]>([]);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [layoutMode, setLayoutMode] = useState<"grid" | "list">("grid");

  const [autoRefresh, setAutoRefresh] = useState(true);
  const intervalRef = useRef<number | null>(null);

  const goToStep = useCallback((next: Step) => {
    setError(null);
    setStep(next);
  }, []);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const { sessions: result } = await listReservationsBySession(date, token);
      setSessions(result);
      setLastUpdatedAt(new Date());
    } catch (err: any) {
      setError(err?.message ?? "예약 현황을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [date, token]);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const { token: issuedToken } = await loginAdmin(email.trim(), password);
      setToken(issuedToken);
      goToStep(2);
    } catch (err: any) {
      setError(err?.message ?? "로그인에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!token) return;
    if (!window.confirm("이 예약을 삭제하시겠습니까?")) return;
    setDeletingId(id);
    setError(null);
    try {
      await deleteReservation(id, token);
      setSessions((prev) =>
        prev.map((session) => ({
          ...session,
          reservations: session.reservations.filter((reservation) => reservation.id !== id),
        }))
      );
    } catch (err: any) {
      setError(err?.message ?? "예약 삭제에 실패했습니다.");
    } finally {
      setDeletingId(null);
    }
  };

  useEffect(() => {
    if (step === 2 && token) {
      load();
    }
  }, [date, step, token, load]);

  useEffect(() => {
    if (step !== 2 || !token) return;

    if (autoRefresh) {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
      }
      intervalRef.current = window.setInterval(load, 15000);
      return () => {
        if (intervalRef.current) {
          window.clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };
    }

    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [autoRefresh, step, token, load]);

  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
      }
    };
  }, []);

  const kpi = useMemo(() => {
    const totalReservations = sessions.reduce((acc, session) => acc + session.reservations.length, 0);
    const inProgress = sessions.reduce(
      (acc, session) =>
        acc + session.reservations.filter((reservation) => reservation.status === "IN_PROGRESS").length,
      0
    );
    const totalSlots = slotsOfDay().length * 4;
    const occupied = sessions.reduce(
      (acc, session) => acc + session.reservations.length * 1.7,
      0
    );
    const utilization = totalSlots > 0 ? Math.min(100, Math.round((occupied / totalSlots) * 100)) : 0;
    return { totalRes: totalReservations, inProgress, utilization };
  }, [sessions]);

  return (
    <div className="min-h-screen w-full bg-gradient-to-b from-gray-50 to-white flex items-center justify-center p-4">
      <div className="w-full max-w-6xl space-y-4">
        <Header />

        <motion.div layout>
          {step === 1 && (
            <LoginPage
              email={email}
              password={password}
              onEmailChange={setEmail}
              onPasswordChange={setPassword}
              onSubmit={handleLogin}
              loading={loading}
              error={error}
            />
          )}

          {step === 2 && (
            <DashboardPage
              date={date}
              onDateChange={setDate}
              autoRefresh={autoRefresh}
              onToggleAutoRefresh={setAutoRefresh}
              onRefresh={load}
              loading={loading}
              sessions={sessions}
              deletingId={deletingId}
              onDeleteReservation={handleDelete}
              lastUpdatedAt={lastUpdatedAt}
              kpi={kpi}
              error={error}
              layoutMode={layoutMode}
              onLayoutModeChange={setLayoutMode}
            />
          )}
        </motion.div>

        <footer className="text-xs text-gray-500 text-center">
          © {new Date().getFullYear()} EV Wireless Charging · Admin Dashboard
        </footer>
      </div>
    </div>
  );
}
