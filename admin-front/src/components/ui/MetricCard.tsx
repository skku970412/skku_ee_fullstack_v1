import React from "react";

interface MetricCardProps {
  icon: React.ReactNode;
  title: string;
  value: string;
}

export default function MetricCard({ icon, title, value }: MetricCardProps) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 text-gray-700">
        <div className="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center">{icon}</div>
        <div className="text-sm">{title}</div>
      </div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
    </div>
  );
}
