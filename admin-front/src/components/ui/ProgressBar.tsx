interface ProgressBarProps {
  percent: number;
}

export default function ProgressBar({ percent }: ProgressBarProps) {
  const safe = Math.max(0, Math.min(100, percent));
  return (
    <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
      <div className="h-2 bg-indigo-600" style={{ width: `${safe}%` }} />
    </div>
  );
}
