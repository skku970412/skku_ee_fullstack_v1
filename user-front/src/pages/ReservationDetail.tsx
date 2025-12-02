import {
  ArrowLeft,
  BatteryCharging,
  Car,
  Clock3,
  Power,
  TimerReset,
  User,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import type { BatteryStatus, Reservation } from "../api/types";
import { getBatteryStatus } from "../api/client";
import Button from "../components/ui/Button";
import { Card } from "../components/ui/Card";

interface ReservationDetailPageProps {
  reservation: Reservation;
  userEmail: string;
  onBack: () => void;
  onDelete: (id: string) => void;
  isDeleting?: boolean;
}

function seededNumber(seed: string, min: number, max: number): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  }
  const span = Math.max(1, max - min);
  return min + Math.abs(hash) % span;
}

function formatMinutes(total: number): string {
  if (total < 60) return `${total}분`;
  const hours = Math.floor(total / 60);
  const minutes = total % 60;
  if (minutes === 0) return `${hours}시간`;
  return `${hours}시간 ${minutes}분`;
}

export default function ReservationDetailPage({
  reservation,
  userEmail,
  onBack,
  onDelete,
  isDeleting = false,
}: ReservationDetailPageProps) {
  const fallbackBattery = useMemo(() => seededNumber(reservation.id, 48, 96), [reservation.id]);
  const detail = useMemo(() => {
    const remaining = seededNumber(`${reservation.id}-rem`, 20, 120);
    const parkingDetected =
      reservation.status === "IN_PROGRESS" || reservation.status === "CONFIRMED";
    return { remaining, parkingDetected };
  }, [reservation.id, reservation.status]);
  const [batteryStatus, setBatteryStatus] = useState<BatteryStatus | null>(null);
  const [batteryLoading, setBatteryLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setBatteryLoading(true);
      try {
        const status = await getBatteryStatus();
        if (cancelled) return;
        setBatteryStatus(status);
      } catch {
        if (cancelled) return;
        setBatteryStatus(null);
      } finally {
        if (!cancelled) {
          setBatteryLoading(false);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [reservation.id]);

  const displayBattery =
    typeof batteryStatus?.percent === "number" && !Number.isNaN(batteryStatus.percent)
      ? Math.round(batteryStatus.percent)
      : fallbackBattery;

  const batteryMuted =
    batteryStatus?.percent != null
      ? (batteryStatus.timestamp
        ? `Firebase RTDB @ ${new Date(batteryStatus.timestamp).toLocaleString()}`
        : "Firebase RTDB")
      : "RTDB value missing; showing fallback";

  const statusTone: Record<
    Reservation["status"],
    { text: string; classes: string }
  > = {
    CONFIRMED: { text: "확정", classes: "bg-amber-100 text-amber-700" },
    IN_PROGRESS: { text: "진행 중", classes: "bg-emerald-100 text-emerald-700" },
    COMPLETED: { text: "완료", classes: "bg-indigo-100 text-indigo-700" },
    CANCELLED: { text: "취소", classes: "bg-gray-200 text-gray-600" },
  };

  return (
    <div className="space-y-4">
      <div className="rounded-3xl bg-gradient-to-r from-indigo-600 via-blue-600 to-cyan-500 text-white p-6 shadow-lg">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-xs uppercase tracking-wide opacity-80">Reservation Detail</div>
            <div className="text-2xl font-semibold mt-1 break-words">{reservation.id}</div>
            <div className="text-sm opacity-90 mt-1">
              세션 {reservation.sessionId} · {reservation.date} {reservation.startTime}~{reservation.endTime}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-3 py-1 rounded-full bg-white/20 border border-white/30 backdrop-blur-sm`}>
              {reservation.plate}
            </span>
            <span className={`text-xs px-3 py-1 rounded-full ${statusTone[reservation.status].classes}`}>
              {statusTone[reservation.status].text}
            </span>
          </div>
        </div>
      </div>

      <Card>
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <InfoTile
              icon={<User className="w-4 h-4" />}
              label="User ID"
              value={reservation.contactEmail || userEmail || "미등록"}
            />
            <InfoTile
              icon={<Clock3 className="w-4 h-4" />}
              label="예약 시간"
              value={`${reservation.date} ${reservation.startTime} ~ ${reservation.endTime}`}
              muted="로컬 시간대 기준"
            />
            <InfoTile
              icon={<Car className="w-4 h-4" />}
              label="자동차 on parkinglot 유무"
              value={detail.parkingDetected ? "입차 확인됨" : "입차 대기"}
              tone={detail.parkingDetected ? "positive" : "warning"}
              muted={detail.parkingDetected ? "센서 신호 정상" : "카메라/센서 대기 중"}
            />
            <InfoTile
              icon={<BatteryCharging className="w-4 h-4" />}
              label="현재 배터리 용량"
              value={`${displayBattery}%${batteryLoading ? " (loading...)" : ""}`}
              muted={batteryMuted}
              meterValue={displayBattery}
            />
            <InfoTile
              icon={<TimerReset className="w-4 h-4" />}
              label="남은 시간"
              value={formatMinutes(detail.remaining)}
              muted="예상 잔여 충전 시간"
            />
            <InfoTile
              icon={<Power className="w-4 h-4" />}
              label="세션"
              value={`세션 ${reservation.sessionId}`}
              muted="예약 구역"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t">
            <Button variant="ghost" onClick={onBack} className="gap-2 text-gray-700">
              <ArrowLeft className="w-4 h-4" />
              예약 목록으로
            </Button>
            <Button
              onClick={() => onDelete(reservation.id)}
              disabled={isDeleting}
              className="bg-rose-600 hover:bg-rose-700"
            >
              {isDeleting ? "삭제 중..." : "예약 삭제"}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}

interface InfoTileProps {
  icon: ReactNode;
  label: string;
  value: string;
  muted?: string;
  tone?: "positive" | "warning";
  meterValue?: number;
}

function InfoTile({ icon, label, value, muted, tone, meterValue }: InfoTileProps) {
  const toneClass =
    tone === "positive"
      ? "bg-emerald-50 border-emerald-100"
      : tone === "warning"
      ? "bg-amber-50 border-amber-100"
      : "bg-gray-50 border-gray-100";

  return (
    <div className={`rounded-2xl border ${toneClass} p-4 flex flex-col gap-2 shadow-[0_1px_8px_rgba(0,0,0,0.03)]`}>
      <div className="flex items-center gap-2 text-gray-600 text-sm">
        <div className="w-8 h-8 rounded-xl bg-white border border-gray-100 flex items-center justify-center text-gray-700">
          {icon}
        </div>
        <span className="font-semibold text-gray-800">{label}</span>
      </div>
      <div className="text-lg font-bold text-gray-900 break-words">{value}</div>
      {muted && <div className="text-xs text-gray-500">{muted}</div>}
      {typeof meterValue === "number" && (
        <div className="w-full h-2 rounded-full bg-white/80 border border-gray-100 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400"
            style={{ width: `${Math.min(100, Math.max(0, meterValue))}%` }}
          />
        </div>
      )}
    </div>
  );
}
