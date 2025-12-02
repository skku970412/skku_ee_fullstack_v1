export const START_HOUR = 0;
export const END_HOUR = 24;
export const DAY_END_MINUTES = END_HOUR * 60;

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

export function daySlots(): string[] {
  const arr: string[] = [];
  for (let h = START_HOUR; h <= END_HOUR - 1; h++) {
    arr.push(`${pad(h)}:00`);
    arr.push(`${pad(h)}:30`);
  }
  return arr;
}

export function endTime(start: string, durationMin: number): string {
  return fromMinutes(toMinutes(start) + durationMin);
}
