"use client";

type ScanEvent = {
  stage: string;
  message: string;
  level?: "log" | "info" | "warn" | "error";
  [key: string]: unknown;
};

const STAGE_COLOR: Record<string, string> = {
  start: "#b9790a",
  city: "#b9790a",
  querit: "#2f6b6b",
  pages: "#2f6b6b",
  summarize: "#b23c00",
  skip: "#8a7d6c",
  saved: "#3d7a3a",
  done: "#b9790a",
  error: "#b23c00",
};

function colorFor(stage: string): string {
  const key = Object.keys(STAGE_COLOR).find((part) => stage.startsWith(part));
  return STAGE_COLOR[key ?? ""] || "#241f1a";
}

export function logScanEvent(event: ScanEvent) {
  const stage = event.stage || "scan";
  const level = event.level === "error" ? "error" : event.level === "warn" ? "warn" : "log";
  const style = `color:${colorFor(stage)};font-weight:700`;
  const rest = { ...event };
  delete rest.stage;
  delete rest.message;
  delete rest.level;
  const extras = Object.keys(rest).length ? rest : undefined;
  if (extras) {
    console[level](`%c[scan:${stage}]%c ${event.message}`, style, "color:inherit", extras);
  } else {
    console[level](`%c[scan:${stage}]%c ${event.message}`, style, "color:inherit");
  }
}

export function logScanStart() {
  console.groupCollapsed("%c[scan] event pipeline", "color:#b9790a;font-weight:700;font-size:12px");
  console.log("Watch this group for Querit → page fetch → OpenRouter → DB.");
}

export function logScanEnd() {
  console.groupEnd();
}

export function logApp(scope: string, message: string, extra?: unknown) {
  if (extra !== undefined) {
    console.log(`%c[${scope}]%c ${message}`, "color:#8a7d6c;font-weight:700", "color:inherit", extra);
  } else {
    console.log(`%c[${scope}]%c ${message}`, "color:#8a7d6c;font-weight:700", "color:inherit");
  }
}
