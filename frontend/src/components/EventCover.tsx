"use client";

import { useId } from "react";

const COVERS = [
  "music",
  "food",
  "sports",
  "art",
  "tech",
  "outdoors",
  "nightlife",
  "volunteering",
  "workshops",
  "markets",
  "comedy",
  "film",
  "fitness",
  "gaming",
  "networking",
  "community",
] as const;

export type CoverTag = (typeof COVERS)[number];

const COVER_SET = new Set<string>(COVERS);

export type Palette = {
  sky0: string;
  sky1: string;
  land: string;
  accent: string;
  light: string;
};

export const PALETTES: Record<CoverTag, Palette> = {
  music: { sky0: "#1b1424", sky1: "#7a3b2e", land: "#241820", accent: "#f0a202", light: "#f6e2b3" },
  food: { sky0: "#f3d5a6", sky1: "#e08a4c", land: "#8a3b1c", accent: "#f2c14e", light: "#fff4dc" },
  sports: { sky0: "#87b7d9", sky1: "#2f6b4f", land: "#1f4a38", accent: "#f0a202", light: "#e8f4ea" },
  art: { sky0: "#f4d6c6", sky1: "#c45c5c", land: "#6b2e4a", accent: "#f0a202", light: "#fff1e4" },
  tech: { sky0: "#14202c", sky1: "#2f6b6b", land: "#0f171f", accent: "#8ad4c4", light: "#d7f3ec" },
  outdoors: { sky0: "#b9d7ee", sky1: "#f3e0b8", land: "#3f6b3a", accent: "#f0a202", light: "#fff8e8" },
  nightlife: { sky0: "#120e1c", sky1: "#3a2158", land: "#1a1424", accent: "#f0a202", light: "#f7d9a0" },
  volunteering: { sky0: "#f3e4c8", sky1: "#d98b6a", land: "#7a4630", accent: "#f0a202", light: "#fff6e8" },
  workshops: { sky0: "#efe0c4", sky1: "#c48a4a", land: "#5c3a24", accent: "#f0a202", light: "#fff4de" },
  markets: { sky0: "#f6e2b8", sky1: "#e09a4a", land: "#7a4424", accent: "#f0a202", light: "#fff7e8" },
  comedy: { sky0: "#1a1420", sky1: "#8a4a28", land: "#241820", accent: "#f0a202", light: "#ffe7b8" },
  film: { sky0: "#16141c", sky1: "#4a3048", land: "#1c1824", accent: "#f0a202", light: "#f3e0c4" },
  fitness: { sky0: "#f0d9b0", sky1: "#e07a48", land: "#4a6b3a", accent: "#f0a202", light: "#fff4e4" },
  gaming: { sky0: "#161428", sky1: "#3a2a78", land: "#12101c", accent: "#8ad4c4", light: "#e4ddff" },
  networking: { sky0: "#dfe8f0", sky1: "#6a8aaa", land: "#2a3a4a", accent: "#f0a202", light: "#f4f7fb" },
  community: { sky0: "#f2e4c8", sky1: "#c47a4a", land: "#5a3a28", accent: "#f0a202", light: "#fff6e8" },
};

export function coverTag(tags?: string[] | null): CoverTag {
  const matches = (tags || []).filter((tag): tag is CoverTag => COVER_SET.has(tag));
  if (matches.length === 0) return "community";
  return [...matches].sort()[0];
}

function Motif({ tag, p }: { tag: CoverTag; p: Palette }) {
  switch (tag) {
    case "music":
      return (
        <g fill={p.light} opacity="0.92">
          <ellipse cx="320" cy="300" rx="210" ry="28" fill={p.land} />
          <rect x="188" y="168" width="264" height="92" rx="10" fill="#120e16" />
          <circle cx="248" cy="214" r="22" fill={p.accent} />
          <circle cx="392" cy="214" r="22" fill={p.accent} />
          <path d="M430 92c18 8 28 28 22 48M458 84c22 10 34 34 26 58" fill="none" stroke={p.accent} strokeWidth="5" strokeLinecap="round" />
          <circle cx="452" cy="148" r="10" fill={p.accent} />
          <circle cx="488" cy="138" r="8" fill={p.light} />
        </g>
      );
    case "food":
      return (
        <g>
          <ellipse cx="320" cy="268" rx="150" ry="22" fill={p.land} opacity="0.35" />
          <ellipse cx="320" cy="232" rx="118" ry="48" fill={p.light} />
          <ellipse cx="320" cy="220" rx="92" ry="34" fill="#d2653a" />
          <circle cx="292" cy="214" r="16" fill="#f0a202" />
          <circle cx="328" cy="206" r="14" fill="#6aa35a" />
          <circle cx="354" cy="220" r="12" fill="#c45c5c" />
          <rect x="232" y="248" width="176" height="14" rx="7" fill={p.land} />
        </g>
      );
    case "sports":
      return (
        <g>
          <ellipse cx="320" cy="300" rx="220" ry="26" fill={p.land} />
          <path d="M80 210 Q320 120 560 210" fill="none" stroke={p.light} strokeWidth="8" />
          <circle cx="320" cy="188" r="42" fill={p.light} />
          <path d="M320 146c28 18 42 42 42 42M320 146c-28 18-42 42-42 42M278 188h84" fill="none" stroke={p.land} strokeWidth="3" />
        </g>
      );
    case "art":
      return (
        <g>
          <circle cx="250" cy="168" r="54" fill="#c45c5c" />
          <circle cx="318" cy="150" r="46" fill="#f0a202" opacity="0.9" />
          <circle cx="372" cy="188" r="50" fill="#2f6b6b" opacity="0.85" />
          <rect x="430" y="150" width="18" height="120" rx="6" fill="#5c3a24" />
          <circle cx="439" cy="142" r="16" fill="#c45c5c" />
          <circle cx="452" cy="156" r="12" fill="#f0a202" />
        </g>
      );
    case "tech":
      return (
        <g fill="none" stroke={p.accent} strokeWidth="3">
          <rect x="210" y="120" width="220" height="140" rx="16" fill="#0f171f" />
          <circle cx="260" cy="170" r="10" fill={p.accent} stroke="none" />
          <circle cx="320" cy="210" r="10" fill={p.light} stroke="none" />
          <circle cx="380" cy="168" r="10" fill={p.accent} stroke="none" />
          <path d="M260 170h60l60-42" />
          <path d="M320 210v-40" />
        </g>
      );
    case "outdoors":
      return (
        <g>
          <path d="M40 260 L180 120 L280 230 L380 90 L600 260 Z" fill={p.land} />
          <path d="M180 120 L220 160 L140 160 Z" fill="#2f5230" />
          <path d="M380 90 L430 150 L330 150 Z" fill="#2f5230" />
          <circle cx="500" cy="88" r="28" fill={p.accent} />
        </g>
      );
    case "nightlife":
      return (
        <g>
          <rect x="160" y="90" width="70" height="180" fill="#2a2038" />
          <rect x="250" y="60" width="90" height="210" fill="#241830" />
          <rect x="360" y="110" width="80" height="160" fill="#2e2244" />
          <rect x="460" y="80" width="64" height="190" fill="#261c36" />
          {[175, 195, 215, 268, 292, 316, 380, 404, 478, 498].map((x) => (
            <rect key={x} x={x} y={x % 40 < 20 ? 130 : 150} width="10" height="14" fill={p.accent} opacity="0.85" />
          ))}
        </g>
      );
    case "volunteering":
      return (
        <g fill={p.accent}>
          <path d="M250 210c0-28 22-50 50-50s50 22 50 50v70H250z" fill={p.light} />
          <path d="M300 150c18-28 62-28 72 8 8 28-18 48-36 62-18-14-44-34-36-70z" />
          <circle cx="250" cy="168" r="22" fill={p.light} />
          <circle cx="350" cy="168" r="22" fill={p.light} />
        </g>
      );
    case "workshops":
      return (
        <g>
          <rect x="180" y="150" width="280" height="120" rx="8" fill="#c9a06a" />
          <rect x="196" y="166" width="120" height="72" fill={p.light} />
          <path d="M400 130 l70 40 -18 32 -70-40z" fill="#8a5a32" />
          <rect x="430" y="188" width="18" height="80" rx="4" fill="#5c3a24" />
        </g>
      );
    case "markets":
      return (
        <g>
          <path d="M140 150 L320 70 L500 150" fill="#c45c5c" />
          <rect x="168" y="150" width="304" height="120" fill={p.light} />
          <rect x="196" y="178" width="70" height="58" fill="#d2653a" />
          <rect x="286" y="178" width="70" height="58" fill="#6aa35a" />
          <rect x="376" y="178" width="70" height="58" fill="#f0a202" />
        </g>
      );
    case "comedy":
      return (
        <g>
          <ellipse cx="320" cy="300" rx="180" ry="24" fill="#000" opacity="0.45" />
          <path d="M160 0 L320 260 L480 0" fill={p.accent} opacity="0.28" />
          <circle cx="320" cy="188" r="44" fill={p.light} />
          <path d="M300 198c12 16 32 16 44 0" fill="none" stroke="#241f1a" strokeWidth="4" strokeLinecap="round" />
          <circle cx="304" cy="176" r="5" fill="#241f1a" />
          <circle cx="336" cy="176" r="5" fill="#241f1a" />
        </g>
      );
    case "film":
      return (
        <g fill={p.light}>
          <rect x="150" y="70" width="44" height="220" rx="6" />
          <rect x="446" y="70" width="44" height="220" rx="6" />
          {[90, 130, 170, 210, 250].map((y) => (
            <g key={y}>
              <rect x="160" y={y} width="24" height="18" fill="#241f1a" />
              <rect x="456" y={y} width="24" height="18" fill="#241f1a" />
            </g>
          ))}
          <rect x="210" y="120" width="220" height="130" rx="8" fill="#241f1a" />
          <polygon points="290,150 360,185 290,220" fill={p.accent} />
        </g>
      );
    case "fitness":
      return (
        <g>
          <path d="M60 260 C160 200 220 240 320 170 C420 100 500 160 600 120" fill="none" stroke={p.land} strokeWidth="14" strokeLinecap="round" />
          <circle cx="236" cy="210" r="16" fill={p.accent} />
          <circle cx="430" cy="132" r="16" fill={p.light} />
        </g>
      );
    case "gaming":
      return (
        <g>
          <rect x="190" y="140" width="260" height="130" rx="48" fill="#2a2448" />
          <rect x="230" y="186" width="44" height="14" rx="4" fill={p.light} />
          <rect x="245" y="172" width="14" height="44" rx="4" fill={p.light} />
          <circle cx="390" cy="178" r="12" fill={p.accent} />
          <circle cx="418" cy="206" r="12" fill="#c45c5c" />
        </g>
      );
    case "networking":
      return (
        <g fill={p.accent} stroke={p.land} strokeWidth="4">
          <circle cx="220" cy="170" r="18" />
          <circle cx="320" cy="120" r="18" />
          <circle cx="420" cy="170" r="18" />
          <circle cx="280" cy="230" r="18" />
          <circle cx="370" cy="230" r="18" />
          <path d="M220 170L320 120L420 170L370 230L280 230Z" fill="none" />
        </g>
      );
    default:
      return (
        <g>
          <rect x="150" y="150" width="70" height="130" fill="#7a5a40" />
          <rect x="240" y="110" width="90" height="170" fill="#8a6848" />
          <rect x="360" y="140" width="80" height="140" fill="#6e4e34" />
          <rect x="460" y="170" width="60" height="110" fill="#7a5a40" />
          <circle cx="500" cy="92" r="24" fill={p.accent} />
        </g>
      );
  }
}

type Props = {
  tags?: string[] | null;
  className?: string;
  title?: string;
  showTag?: boolean;
};

export function EventCover({ tags, className = "", title, showTag = true }: Props) {
  const uid = useId().replace(/:/g, "");
  const tag = coverTag(tags);
  const p = PALETTES[tag];
  const sky = `sky-${uid}`;
  const glow = `glow-${uid}`;

  return (
    <div className={`relative overflow-hidden bg-panel ${className}`} aria-hidden={title ? undefined : true} role={title ? "img" : undefined} aria-label={title}>
      <svg viewBox="0 0 640 360" className="h-full w-full" preserveAspectRatio="xMidYMid slice">
        <defs>
          <linearGradient id={sky} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={p.sky0} />
            <stop offset="100%" stopColor={p.sky1} />
          </linearGradient>
          <radialGradient id={glow} cx="70%" cy="20%" r="50%">
            <stop offset="0%" stopColor={p.light} stopOpacity="0.45" />
            <stop offset="100%" stopColor={p.light} stopOpacity="0" />
          </radialGradient>
        </defs>
        <rect width="640" height="360" fill={`url(#${sky})`} />
        <rect width="640" height="360" fill={`url(#${glow})`} />
        <Motif tag={tag} p={p} />
        <rect width="640" height="360" fill="#241f1a" opacity="0.08" />
      </svg>
      {showTag && (
        <span className="pointer-events-none absolute bottom-2 left-2 rounded-full bg-night/55 px-2 py-0.5 text-[10px] uppercase tracking-[0.16em] text-white/90">
          {tag}
        </span>
      )}
    </div>
  );
}
