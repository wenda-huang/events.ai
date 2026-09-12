/** Planet-covering radius; backend treats this as “no distance filter”. */
export const UNLIMITED_RADIUS_MI = 12_500;

export const RADIUS_SLIDER_MIN = 0;
export const RADIUS_SLIDER_MAX = 100;

const MIN_MI = 1;
const MAX_FINITE_MI = 2_500;

export function isUnlimitedRadius(radiusMi: number): boolean {
  return radiusMi >= UNLIMITED_RADIUS_MI;
}

export function sliderToRadiusMi(slider: number): number {
  if (slider >= RADIUS_SLIDER_MAX) return UNLIMITED_RADIUS_MI;
  const t = Math.max(0, Math.min(1, slider / (RADIUS_SLIDER_MAX - 1)));
  return roundRadiusMi(MIN_MI * (MAX_FINITE_MI / MIN_MI) ** t);
}

export function radiusMiToSlider(radiusMi: number): number {
  if (!Number.isFinite(radiusMi) || isUnlimitedRadius(radiusMi)) return RADIUS_SLIDER_MAX;
  const clamped = Math.max(MIN_MI, Math.min(MAX_FINITE_MI, radiusMi));
  const t = Math.log(clamped / MIN_MI) / Math.log(MAX_FINITE_MI / MIN_MI);
  return Math.round(t * (RADIUS_SLIDER_MAX - 1));
}

export function formatRadiusMi(radiusMi: number): string {
  if (isUnlimitedRadius(radiusMi)) return "All";
  if (radiusMi < 10) return `${radiusMi} mi`;
  return `${Math.round(radiusMi)} mi`;
}

export function sliderProgress(slider: number): string {
  return `${(slider / RADIUS_SLIDER_MAX) * 100}%`;
}

function roundRadiusMi(value: number): number {
  if (value < 10) return Math.round(value * 2) / 2;
  if (value < 30) return Math.round(value);
  if (value < 100) return Math.round(value / 5) * 5;
  if (value < 500) return Math.round(value / 25) * 25;
  if (value < 2000) return Math.round(value / 50) * 50;
  return Math.round(value / 100) * 100;
}
