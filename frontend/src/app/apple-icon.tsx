import { ImageResponse } from "next/og";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#f6f1e6",
        }}
      >
        <svg width="118" height="118" viewBox="0 0 32 32">
          <path
            fill="#f0a202"
            d="M16 4.2c-4.15 0-7.5 3.28-7.5 7.32 0 5.5 6.7 15.28 7.15 15.94a.45.45 0 0 0 .7 0C16.8 26.8 23.5 17.02 23.5 11.52 23.5 7.48 20.15 4.2 16 4.2z"
          />
          <circle cx="16" cy="11.4" r="3.15" fill="#fff8e8" />
          <circle cx="16" cy="11.4" r="1.55" fill="#c44900" opacity="0.55" />
        </svg>
      </div>
    ),
    { ...size },
  );
}
