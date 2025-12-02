import { Camera, Car, ChevronLeft, ChevronRight } from "lucide-react";
import React from "react";
import Button from "../components/ui/Button";
import { Card, CardHeader } from "../components/ui/Card";
import ErrorBar from "../components/ui/ErrorBar";
import type { Reservation } from "../api/types";

interface PlateVerificationPageProps {
  plate: string;
  plateValid: boolean | null;
  plateRegistered: boolean | null;
  plateHistory: Reservation[];
  error: string | null;
  loading: boolean;
  onPlateChange: (value: string) => void;
  onBack: () => void;
  onVerify: () => void;
  onOpenScanner: () => void;
  onCloseScanner: () => void;
  onSnap: () => void;
  scanOpen: boolean;
  videoRef: React.RefObject<HTMLVideoElement>;
}

export default function PlateVerificationPage({
  plate,
  plateValid,
  plateRegistered,
  plateHistory,
  error,
  loading,
  onPlateChange,
  onBack,
  onVerify,
  onOpenScanner,
  onCloseScanner,
  onSnap,
  scanOpen,
  videoRef,
}: PlateVerificationPageProps) {
  const canProceed = plateValid === true;

  return (
    <Card>
      <CardHeader
        icon={<Car className="w-5 h-5" />}
        title="차량 번호 확인"
        subtitle="차량 번호를 직접 입력하거나 카메라로 인식해 주세요."
      />
      <div className="grid gap-3 p-6">
        <div className="flex gap-2">
          <input
            className={`flex-1 rounded-xl border px-4 py-3 text-lg outline-none focus:ring-2 focus:ring-indigo-500 ${
              plateValid === false ? "border-red-400" : "border-gray-200"
            }`}
            placeholder="예) 12가3456 / 123나4567"
            value={plate}
            onChange={(event) => onPlateChange(event.target.value)}
          />
          <button
            onClick={onOpenScanner}
            className="rounded-xl border border-gray-200 px-3 py-2 hover:bg-gray-50 active:scale-[.99]"
          >
            <Camera className="w-5 h-5" />
          </button>
        </div>
        {plateValid === false && (
          <p className="text-sm text-red-500">올바른 형식의 차량 번호를 입력해 주세요.</p>
        )}
        {plateRegistered !== null && (
          <p className={`text-sm ${plateRegistered ? "text-emerald-600" : "text-amber-600"}`}>
            {plateRegistered ? "기존 예약 이력이 확인되었습니다." : "새로운 차량 번호입니다."}
          </p>
        )}
        {plateHistory.length > 0 && (
          <div className="rounded-xl border border-gray-200 p-3 text-sm">
            <div className="font-semibold text-gray-700 mb-2">최근 예약 이력</div>
            <ul className="space-y-1 text-gray-600">
              {plateHistory.map((reservation) => (
                <li key={reservation.id}>
                  {reservation.date} {reservation.startTime}~{reservation.endTime} · 세션{" "}
                  {reservation.sessionId} · {reservation.status}
                </li>
              ))}
            </ul>
          </div>
        )}
        {error && <ErrorBar msg={error} />}
        <div className="flex items-center justify-between">
          <Button variant="ghost" onClick={onBack}>
            <ChevronLeft className="w-4 h-4 mr-1" />
            이전
          </Button>
          <Button disabled={!canProceed || loading} onClick={onVerify}>
            {loading ? "확인 중..." : "다음"}
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      </div>

      {scanOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="p-4 border-b flex items-center justify-between">
              <div className="font-semibold flex items-center gap-2">
                <Camera className="w-4 h-4" /> 번호판 인식
              </div>
              <button onClick={onCloseScanner} className="text-gray-500 hover:text-gray-800">
                닫기
              </button>
            </div>
            <div className="p-4">
              <video ref={videoRef} className="w-full rounded-xl bg-black" playsInline muted />
              <div className="flex gap-2 mt-3">
                <Button className="flex-1" onClick={onSnap}>
                  촬영하고 인식
                </Button>
                <Button variant="ghost" onClick={onCloseScanner}>
                  취소
                </Button>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                참고: 실제 환경에서는 OCR 모델을 통한 인식 과정을 사용합니다.
              </p>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
