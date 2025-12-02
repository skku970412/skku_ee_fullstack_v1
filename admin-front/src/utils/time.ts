export const START_HOUR = 9;
export const END_HOUR = 22;

export function pad(n: number): string {
  return n.toString().padStart(2, "0");
}

export function toMinutes(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
}

export function fromMinutes(mins: number): string {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${pad(h)}:${pad(m)}`;
}

export function slotsOfDay(): string[] {
  const slots: string[] = [];
  for (let h = START_HOUR; h <= END_HOUR - 1; h++) {
    slots.push(`${pad(h)}:00`);
    slots.push(`${pad(h)}:30`);
  }
  return slots;
}
