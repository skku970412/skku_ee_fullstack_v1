interface ToggleProps {
  checked: boolean;
  onChange: (value: boolean) => void;
  label?: string;
}

export default function Toggle({ checked, onChange, label }: ToggleProps) {
  return (
    <label className="inline-flex items-center gap-2 select-none">
      {label && <span className="text-sm text-gray-700">{label}</span>}
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`w-12 h-7 rounded-full border flex items-center px-1 transition ${
          checked ? "bg-indigo-600 border-indigo-600" : "bg-gray-200 border-gray-200"
        }`}
      >
        <span
          className={`w-5 h-5 bg-white rounded-full shadow transform transition ${
            checked ? "translate-x-5" : "translate-x-0"
          }`}
        />
      </button>
    </label>
  );
}
