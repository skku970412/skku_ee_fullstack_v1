import React from "react";

export interface StepDefinition {
  id: number;
  title: string;
  icon: React.ReactNode;
}

interface StepperProps {
  current: number;
  steps: StepDefinition[];
}

export default function Stepper({ current, steps }: StepperProps) {
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {steps.map((step) => {
        const active = step.id === current;
        const passed = step.id < current;
        return (
          <div
            key={step.id}
            className={`flex items-center gap-2 rounded-2xl border p-3 transition flex-1 min-w-[140px] sm:min-w-[160px] ${
              active
                ? "border-indigo-500 bg-indigo-50"
                : passed
                ? "border-emerald-400 bg-emerald-50"
                : "border-gray-200 bg-white"
            }`}
          >
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${
                active
                  ? "bg-indigo-600 text-white"
                  : passed
                  ? "bg-emerald-500 text-white"
                  : "bg-gray-200 text-gray-700"
              }`}
            >
              {step.id}
            </div>
            <div className="flex items-center gap-1 text-sm">
              <span>{step.icon}</span>
              <span className={active ? "text-indigo-700" : "text-gray-700"}>{step.title}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
