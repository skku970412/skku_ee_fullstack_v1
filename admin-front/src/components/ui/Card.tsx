import React from "react";

interface CardProps {
  children: React.ReactNode;
}

export function Card({ children }: CardProps) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      {children}
    </div>
  );
}

interface CardHeaderProps {
  icon?: React.ReactNode;
  title: string;
  subtitle?: string;
}

export function CardHeader({ icon, title, subtitle }: CardHeaderProps) {
  return (
    <div className="px-6 py-4 border-b bg-white/50">
      <div className="flex items-center gap-2">
        {icon && (
          <div className="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center">
            {icon}
          </div>
        )}
        <div>
          <div className="font-semibold">{title}</div>
          {subtitle && <div className="text-sm text-gray-500">{subtitle}</div>}
        </div>
      </div>
    </div>
  );
}
