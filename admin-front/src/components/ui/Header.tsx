import { Power } from "lucide-react";

export default function Header() {
  return (
    <div className="flex items-center gap-3">
      <div className="w-10 h-10 rounded-2xl bg-indigo-600 flex items-center justify-center shadow text-white">
        <Power className="w-5 h-5" />
      </div>
      <div>
        <div className="font-semibold text-lg">관리자 대시보드</div>
        <div className="text-sm text-gray-500">세션별 예약 현황을 실시간으로 확인합니다.</div>
      </div>
    </div>
  );
}
