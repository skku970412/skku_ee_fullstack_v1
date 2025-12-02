import { CheckCircle2, ChevronLeft, ChevronRight, Clock, History } from "lucide-react";
import Button from "../components/ui/Button";
import { Card, CardHeader } from "../components/ui/Card";
import ErrorBar from "../components/ui/ErrorBar";
import LabeledInput from "../components/forms/LabeledInput";
import LabeledSelect from "../components/forms/LabeledSelect";
import { fromMinutes, toMinutes, endTime } from "../utils/time";

export interface AvailabilityStrip {
  dateISO: string;
  label: string;
  color: string;
  freePct: number;
}

interface SchedulePageProps {
  sessionId: number;
  onSessionChange: (value: number) => void;
  durationMin: number;
  onDurationChange: (value: number) => void;
  durationOptions: number[];
  date: string;
  onDateChange: (value: string) => void;
  sessionOptions: number[];
  occupiedSet: Set<string>;
  slots: string[];
  startTime: string;
  onStartTimeChange: (value: string) => void;
  multiMode: boolean;
  onMultiModeChange: (value: boolean) => void;
  selectedStarts: string[];
  onToggleStart: (value: string) => void;
  estimatedPrice: number;
  plate: string;
  error: string | null;
  loading: boolean;
  onBack: () => void;
  onSubmit: () => void;
  onOpenHistory: () => void;
  availabilityLoading: boolean;
  availabilityStripe: AvailabilityStrip[];
  dayEndMinutes: number;
}

export default function SchedulePage({
  sessionId,
  onSessionChange,
  durationMin,
  onDurationChange,
  durationOptions,
  date,
  onDateChange,
  sessionOptions,
  occupiedSet,
  slots,
  startTime,
  onStartTimeChange,
  multiMode,
  onMultiModeChange,
  selectedStarts,
  onToggleStart,
  estimatedPrice,
  plate,
  error,
  loading,
  onBack,
  onSubmit,
  onOpenHistory,
  availabilityLoading,
  availabilityStripe,
  dayEndMinutes,
}: SchedulePageProps) {
  const blockMinutes = multiMode ? 60 : durationMin;
  const selectedRanges = multiMode
    ? selectedStarts.map((slot) => `${slot} ~ ${endTime(slot, 60)}`)
    : [`${startTime} ~ ${endTime(startTime, durationMin)}`];

  return (
    <Card>
      <CardHeader
        icon={<Clock className="w-5 h-5" />}
        title="사용 시간 선택"
        subtitle="세션과 시간을 선택해 예약을 진행하세요"
      />
      <div className="grid gap-4 p-6">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <LabeledSelect
            label="세션"
            value={sessionId}
            onChange={(value) => onSessionChange(Number(value))}
            options={sessionOptions.map((value) => ({ label: `세션 ${value}`, value }))}
          />
          <LabeledSelect
            label="사용 시간(분)"
            value={durationMin}
            onChange={(value) => onDurationChange(Number(value))}
            options={durationOptions.map((value) => ({ label: `${value}분`, value }))}
            disabled={multiMode}
          />
          <LabeledInput label="사용 날짜" value={date} onChange={onDateChange} type="date" />
        </div>

        <div className="flex items-center justify-between bg-gray-50 border border-gray-200 rounded-xl p-3 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={multiMode}
              onChange={(event) => onMultiModeChange(event.target.checked)}
              className="h-4 w-4"
            />
            <span>여러 개 1시간 예약 선택 모드</span>
          </label>
          <span className="text-xs text-gray-600">
            시작 시간을 여러 개 선택하면 각 1시간씩 별도 예약을 만듭니다.
          </span>
        </div>

        <div className="rounded-2xl border border-gray-200 p-3">
          <div className="text-sm text-gray-600 mb-2 flex items-center justify-between">
            <span>
              날짜별 여유도{" "}
              <span className="inline-block w-3 h-3 rounded bg-emerald-500 mr-1" />
              여유 <span className="inline-block w-3 h-3 rounded bg-amber-500 mx-1" />
              보통 <span className="inline-block w-3 h-3 rounded bg-rose-500 ml-1" />
              혼잡
            </span>
            {availabilityLoading && <span className="text-xs text-indigo-600">불러오는 중...</span>}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-2">
            {availabilityStripe.map((item) => (
              <button
                key={item.dateISO}
                onClick={() => onDateChange(item.dateISO)}
                className={`rounded-xl border px-3 py-2 text-sm flex flex-col items-center gap-1 transition ${
                  item.dateISO === date
                    ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                    : "border-gray-200 bg-white hover:bg-gray-50"
                }`}
              >
                <span>{item.label}</span>
                <span className={`text-[11px] px-2 py-0.5 rounded-full text-white ${item.color}`}>
                  여유 {item.freePct}%
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-gray-200 p-3">
          <div className="text-sm text-gray-600 mb-2">시간을 선택해주세요</div>
          <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2">
            {slots.map((slot) => {
              const start = toMinutes(slot);
              const end = start + blockMinutes;
              let overlaps = false;
              let cursor = start;
              while (cursor < end) {
                if (occupiedSet.has(fromMinutes(cursor))) {
                  overlaps = true;
                  break;
                }
                cursor += 30;
              }
              const conflictsWithSelection =
                multiMode &&
                selectedStarts.some((selected) => {
                  if (selected === slot) return false;
                  const selStart = toMinutes(selected);
                  const selEnd = selStart + 60;
                  return start < selEnd && selStart < end;
                });
              const beyond = end > dayEndMinutes;
              const disabled = overlaps || beyond || conflictsWithSelection;
              const selected = multiMode ? selectedStarts.includes(slot) : startTime === slot;
              return (
                <button
                  key={slot}
                  disabled={disabled}
                  onClick={() => (multiMode ? onToggleStart(slot) : onStartTimeChange(slot))}
                  className={`rounded-lg px-2 py-2 text-sm border transition ${
                    disabled
                      ? "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed"
                      : "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                  } ${selected ? "ring-2 ring-indigo-500" : ""}`}
                >
                  {slot}
                </button>
              );
            })}
          </div>
        </div>

        <div className="rounded-xl bg-gray-50 p-4 text-sm flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div className="space-y-1">
            <div>
              차량 번호: <span className="font-semibold">{plate}</span>
            </div>
            <div>선택한 예약: {selectedRanges.length ? selectedRanges.join(", ") : "없음"}</div>
            <div>세션: 세션 {sessionId}</div>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-500">예상 결제 금액</div>
            <div className="text-xl font-bold">{estimatedPrice.toLocaleString()}원</div>
          </div>
        </div>

        {error && <ErrorBar msg={error} />}
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={onBack}>
            <ChevronLeft className="w-4 h-4 mr-1" />
            이전
          </Button>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onOpenHistory}>
              <History className="w-4 h-4 mr-1" />
              내 예약
            </Button>
            <Button disabled={loading} onClick={onSubmit}>
              {loading ? "예약 중.." : multiMode ? `예약 확정 (${selectedStarts.length}개)` : "예약 확정"}
              <CheckCircle2 className="w-4 h-4 ml-1" />
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
