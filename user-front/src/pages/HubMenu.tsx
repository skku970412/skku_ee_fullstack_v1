import type { ReactNode } from "react";
import { BadgeCheck, CarFront, ClipboardList, DollarSign } from "lucide-react";
import Button from "../components/ui/Button";
import { Card, CardHeader } from "../components/ui/Card";

interface PricingItem {
  label: string;
  price: string;
  note?: string;
}

interface HubMenuProps {
  onBook: () => void;
  onMyReservations: () => void;
  onTogglePricing: () => void;
  showPricing: boolean;
  pricing: PricingItem[];
}

export default function HubMenu({
  onBook,
  onMyReservations,
  onTogglePricing,
  showPricing,
  pricing,
}: HubMenuProps) {
  return (
    <Card>
      <CardHeader
        icon={<BadgeCheck className="w-4 h-4 text-indigo-600" />}
        title="무선충전 예약 메뉴"
        subtitle="무엇을 하실지 선택해 주세요."
      />
      <div className="p-6 space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          <HubButton
            icon={<CarFront className="w-4 h-4" />}
            label="차량 예약"
            description="번호 입력/스캔 후 시간 선택"
            onClick={onBook}
          />
          <HubButton
            icon={<ClipboardList className="w-4 h-4" />}
            label="내 예약 보기"
            description="예약 내역 확인 및 삭제"
            onClick={onMyReservations}
          />
          <HubButton
            icon={<DollarSign className="w-4 h-4" />}
            label="가격 보기"
            description="이용 요금 안내"
            onClick={onTogglePricing}
            active={showPricing}
          />
        </div>

        {showPricing && (
          <div className="rounded-2xl border border-indigo-100 bg-indigo-50/60 p-4 space-y-2">
            <div className="text-sm font-semibold text-indigo-800 flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              이용 요금 안내
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {pricing.map((item) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between rounded-xl bg-white px-3 py-2 border border-indigo-100 shadow-[0_1px_6px_rgba(0,0,0,0.04)]"
                >
                  <div className="text-sm font-medium text-gray-800">{item.label}</div>
                  <div className="text-sm font-semibold text-indigo-700">{item.price}</div>
                  {item.note && <div className="text-xs text-gray-500">{item.note}</div>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

interface HubButtonProps {
  icon: ReactNode;
  label: string;
  description: string;
  onClick: () => void;
  active?: boolean;
}

function HubButton({ icon, label, description, onClick, active }: HubButtonProps) {
  return (
    <Button
      onClick={onClick}
      variant="ghost"
      className={`w-full justify-start gap-3 px-4 py-4 text-left shadow-sm border border-gray-200 bg-white hover:-translate-y-0.5 hover:shadow-md ${
        active ? "ring-2 ring-indigo-200" : ""
      }`}
    >
      <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center">
        {icon}
      </div>
      <div className="flex flex-col">
        <span className="font-semibold text-gray-900">{label}</span>
        <span className="text-xs text-gray-500">{description}</span>
      </div>
    </Button>
  );
}
