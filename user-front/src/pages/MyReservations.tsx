import { ChevronLeft, Trash2 } from "lucide-react";
import Button from "../components/ui/Button";
import { Card, CardHeader } from "../components/ui/Card";
import ErrorBar from "../components/ui/ErrorBar";
import type { Reservation } from "../api/types";

interface MyReservationsPageProps {
  reservations: Reservation[];
  deletingId: string | null;
  loading: boolean;
  onBack: () => void;
  onDelete: (id: string) => void;
  onDeleteAll: () => void;
  error: string | null;
  onSelect: (reservation: Reservation) => void;
}

export default function MyReservationsPage({
  reservations,
  deletingId,
  loading,
  onBack,
  onDelete,
  onDeleteAll,
  error,
  onSelect,
}: MyReservationsPageProps) {
  return (
    <Card>
      <CardHeader
        title="내 예약"
        subtitle="등록된 예약 내역을 확인하고 관리할 수 있습니다."
      />
      <div className="p-6 space-y-4">
        {error && <ErrorBar msg={error} />}
        {reservations.length === 0 ? (
          <div className="text-gray-500">등록된 예약이 없습니다.</div>
        ) : (
          <div className="overflow-auto rounded-xl border border-gray-200">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="text-left p-3">예약 ID</th>
                  <th className="text-left p-3">일정</th>
                  <th className="text-left p-3">세션</th>
                  <th className="text-left p-3">차량 번호</th>
                  <th className="text-left p-3">상태</th>
                  <th className="text-left p-3 w-20">관리</th>
                </tr>
              </thead>
              <tbody>
                {reservations.map((reservation) => (
                  <tr key={reservation.id} className="border-t">
                    <td className="p-3">
                      <button
                        type="button"
                        onClick={() => onSelect(reservation)}
                        className="text-indigo-600 hover:text-indigo-800 font-semibold underline-offset-4 hover:underline"
                      >
                        {reservation.id}
                      </button>
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      {reservation.date} {reservation.startTime}~{reservation.endTime}
                    </td>
                    <td className="p-3">세션 {reservation.sessionId}</td>
                    <td className="p-3">{reservation.plate}</td>
                    <td className="p-3">
                      <span className="text-xs px-2 py-1 rounded-full bg-indigo-100 text-indigo-700">
                        {reservation.status}
                      </span>
                    </td>
                    <td className="p-3">
                      <button
                        onClick={() => onDelete(reservation.id)}
                        disabled={deletingId === reservation.id}
                        className="rounded px-2 py-1 text-xs border border-red-200 text-red-700 hover:bg-red-50 disabled:opacity-50 inline-flex items-center gap-1"
                      >
                        <Trash2 className="w-3 h-3" />
                        {deletingId === reservation.id ? "삭제중..." : "삭제"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="flex items-center justify-between mt-4">
          <Button variant="ghost" onClick={onBack}>
            <ChevronLeft className="w-4 h-4 mr-1" />
            이전 단계로
          </Button>
          <Button onClick={onDeleteAll} disabled={loading || reservations.length === 0}>
            예약 전체 삭제
          </Button>
        </div>
      </div>
    </Card>
  );
}
