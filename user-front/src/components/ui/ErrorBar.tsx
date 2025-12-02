interface ErrorBarProps {
  msg: string;
}

export default function ErrorBar({ msg }: ErrorBarProps) {
  return (
    <div className="rounded-xl bg-red-50 text-red-700 border border-red-200 px-3 py-2 text-sm">
      {msg}
    </div>
  );
}
