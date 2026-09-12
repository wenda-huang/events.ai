import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const HOP_BY_HOP = new Set([
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
]);

function backendBases(): string[] {
  const fromEnv = process.env.BACKEND_URL?.trim().replace(/\/$/, "");
  const defaults = ["http://127.0.0.1:8000", "http://localhost:8000"];
  return [...new Set(fromEnv ? [fromEnv, ...defaults] : defaults)];
}

async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const targetPath = `${path.join("/")}${req.nextUrl.search}`;
  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });
  const method = req.method.toUpperCase();
  const body =
    method === "GET" || method === "HEAD" ? undefined : Buffer.from(await req.arrayBuffer());

  let lastError = "Connection refused";
  for (const base of backendBases()) {
    try {
      const res = await fetch(`${base}/${targetPath}`, {
        method,
        headers,
        body,
        cache: "no-store",
        redirect: "manual",
      });
      const out = new Headers();
      res.headers.forEach((value, key) => {
        if (!HOP_BY_HOP.has(key.toLowerCase())) out.set(key, value);
      });
      return new NextResponse(res.body, {
        status: res.status,
        statusText: res.statusText,
        headers: out,
      });
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
    }
  }

  return NextResponse.json(
    {
      detail:
        "Cannot reach the API server on port 8000. Start the FastAPI backend and try again.",
      error: lastError,
    },
    { status: 503 },
  );
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
export const HEAD = proxy;
