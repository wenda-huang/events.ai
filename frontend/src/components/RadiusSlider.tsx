"use client";

import {
  formatRadiusMi,
  RADIUS_SLIDER_MAX,
  RADIUS_SLIDER_MIN,
  sliderProgress,
  sliderToRadiusMi,
} from "@/lib/radius";

type RadiusSliderProps = {
  slider: number;
  onSliderChange: (slider: number) => void;
  valueClassName?: string;
};

export function RadiusSlider({ slider, onSliderChange, valueClassName }: RadiusSliderProps) {
  const miles = sliderToRadiusMi(slider);
  return (
    <>
      <input
        type="range"
        min={RADIUS_SLIDER_MIN}
        max={RADIUS_SLIDER_MAX}
        step={1}
        value={slider}
        onChange={(e) => onSliderChange(Number(e.target.value))}
        style={{ ["--range-progress" as string]: sliderProgress(slider) }}
        aria-label="Search radius"
      />
      <span className={valueClassName}>{formatRadiusMi(miles)}</span>
    </>
  );
}
