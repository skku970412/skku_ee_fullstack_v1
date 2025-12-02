import { ChevronLeft, History, Power, QrCode } from "lucide-react";
import Button from "../components/ui/Button";
import { Card, CardHeader } from "../components/ui/Card";
import InfoRow from "../components/ui/InfoRow";
import type { Reservation } from "../api/types";

interface ReservationResultProps {
  reservations: Reservation[];
  plate: string;
  sessionId: number;
  date: string;
  startTime: string;
  durationMin: number;
  estimatedPrice: number;
  onChangeSchedule: () => void;
  onGoMyReservations: () => void;
  onReset: () => void;
}

export default function ReservationResult({
  reservations,
  plate,
  sessionId,
  date,
  startTime,
  durationMin,
  estimatedPrice,
  onChangeSchedule,
  onGoMyReservations,
  onReset,
}: ReservationResultProps) {
  const multiple = reservations.length > 1;

  return (
    <Card>
      <CardHeader
        icon={<Power className="w-5 h-5 text-emerald-600" />}
        title="예약이 완료되었습니다"
        subtitle="예약 정보를 확인해주세요"
      />
      <div className="p-6 grid gap-4">
        <div className="rounded-2xl border border-gray-200 p-4 grid gap-3 text-sm">
          <div className="grid sm:grid-cols-2 gap-3">
            <InfoRow label="예약 개수" value={`${reservations.length}건`} />
            <InfoRow label="차량 번호" value={plate} />
            <InfoRow label="세션" value={`세션 ${sessionId}`} />
            <InfoRow
              label="예상 요금"
              value={`${estimatedPrice.toLocaleString()}원`}
            />
            {!multiple && (
              <>
                <InfoRow label="예약 일정" value={`${date} ${startTime} · ${durationMin}분`} />
                <InfoRow
                  label="상태"
                  value={
                    <span className="inline-flex items-center gap-1 text-emerald-600">
                      <Power className="w-4 h-4" />
                      CONFIRMED
                    </span>
                  }
                />
              </>
            )}
          </div>
          {multiple && (
            <div className="rounded-xl bg-gray-50 border border-gray-200 p-3">
              <div className="font-medium mb-2">선택한 시간</div>
              <ul className="space-y-1 text-gray-700">
                {reservations.map((res) => (
                  <li key={res.id} className="flex items-center justify-between">
                    <span>
                      {res.date} {res.startTime} ~ {res.endTime}
                    </span>
                    <span className="text-xs text-gray-500">ID: {res.id}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <div className="rounded-2xl bg-gray-50 p-4 flex items-center gap-3 text-sm text-gray-600">
          <QrCode className="w-8 h-8" />
          예약 QR 코드가 준비되면 차량 인식용으로 활용될 예정입니다.
        </div>
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={onChangeSchedule}>
            <ChevronLeft className="w-4 h-4 mr-1" />
            시간 다시 선택
          </Button>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onGoMyReservations}>
              <History className="w-4 h-4 mr-1" />
              내 예약 보기
            </Button>
            <Button onClick={onReset}>새로 예약</Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
