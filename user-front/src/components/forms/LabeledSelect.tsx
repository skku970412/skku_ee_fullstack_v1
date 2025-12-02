interface Option<T> {
  label: string;
  value: T;
}

interface LabeledSelectProps<T extends string | number> {
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: Option<T>[];
  disabled?: boolean;
}

export default function LabeledSelect<T extends string | number>({
  label,
  value,
  onChange,
  options,
  disabled = false,
}: LabeledSelectProps<T>) {
  return (
    <label className="grid gap-1">
      <span className="text-sm text-gray-700">{label}</span>
      <select
        className="rounded-xl border border-gray-200 px-4 py-3 outline-none focus:ring-2 focus:ring-indigo-500"
        value={value as any}
        onChange={(event) => {
          const raw = event.target.value;
          const numeric = Number(raw);
          const next = Number.isNaN(numeric) ? ((raw as unknown) as T) : ((numeric as unknown) as T);
          onChange(next);
        }}
        disabled={disabled}
      >
        {options.map((option) => (
          <option key={String(option.value)} value={option.value as any}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
