import { History, Power } from "lucide-react";
import Button from "./Button";

interface HeaderProps {
  loggedIn: boolean;
  onMyReservations: () => void;
  userEmail?: string;
  weather?: {
    temp: number;
    description: string;
  } | null;
}

export default function Header({ loggedIn, onMyReservations, userEmail, weather }: HeaderProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-2xl bg-indigo-600 flex items-center justify-center shadow text-white">
          <Power className="w-5 h-5" />
        </div>
        <div>
          <div className="font-semibold text-lg">무선충전 예약</div>
          <div className="text-sm text-gray-500">차량번호 기반 스마트 예약 시스템</div>
        </div>
      </div>
      <div className="flex flex-col items-start sm:items-end gap-1">
        {loggedIn && userEmail && (
          <div className="text-sm font-semibold text-gray-800">
            안녕하세요 <span className="text-indigo-700">{userEmail}</span> 님
          </div>
        )}
        {weather && (
          <div className="text-xs text-gray-600 flex items-center gap-2 bg-white border border-gray-200 rounded-full px-3 py-1 shadow-sm">
            <span className="font-semibold text-gray-800">{weather.temp.toFixed(1)}°C</span>
            <span className="text-gray-500">{weather.description}</span>
          </div>
        )}
        {loggedIn && (
          <div className="sm:self-end">
            <Button variant="ghost" onClick={onMyReservations} className="gap-1 text-gray-700">
              <History className="w-4 h-4" />
              내 예약
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
