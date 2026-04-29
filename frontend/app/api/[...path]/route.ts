/**
 * Catch-all API proxy — forwards every /api/* request to the backend.
 *
 * WHY this exists instead of next.config.mjs rewrites:
 *   - next.config.mjs rewrites bake the destination URL at BUILD TIME.
 *     When using ngrok (URL changes on every restart) the rewrite becomes
 *     stale and all API calls fail without a redeploy.
 *   - This Edge runtime handler reads process.env.API_URL at REQUEST TIME,
 *     so updating the env var in Vercel takes effect on the next request
 *     without rebuilding the app.
 *   - It also sets `ngrok-skip-browser-warning` which bypasses the ngrok
 *     interstitial HTML page that otherwise poisons JSON/SSE responses.
 *   - Runs in Edge runtime for full streaming support (SSE for AI copilot).
 *
 * ENV VARS (set in Vercel project settings):
 *   API_URL              — preferred: your current ngrok URL, e.g. https://abc.ngrok-free.app
 *   NEXT_PUBLIC_API_URL  — fallback (kept for backward compatibility)
 */

import { NextRequest, NextResponse } from "next/server";

export const runtime = "edge";

/** Read backend URL at request time — NOT baked at build time. */
function getBackendUrl(): string {
  return (
    process.env.API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000"
  );
}

async function proxy(
  req: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = (params.path ?? []).join("/");
  const search = req.nextUrl.search; // preserves query params (?foo=bar)
  const target = `${getBackendUrl()}/${path}${search}`;

  // Build forwarded headers — strip hop-by-hop headers that confuse proxies
  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("keep-alive");
  headers.delete("proxy-authenticate");
  headers.delete("proxy-authorization");
  headers.delete("te");
  headers.delete("trailers");
  headers.delete("transfer-encoding");
  headers.delete("upgrade");

  // ── ngrok-specific ────────────────────────────────────────────────────────
  // Without this header, ngrok (free tier) returns an HTML interstitial page
  // instead of your actual JSON/SSE response, which crashes every API call.
  headers.set("ngrok-skip-browser-warning", "true");
  // A non-browser User-Agent also suppresses the interstitial
  headers.set("User-Agent", "AnatomAI-Proxy/1.0");

  const body =
    req.method !== "GET" && req.method !== "HEAD" ? req.body : undefined;

  let upstream: Response;
  try {
    upstream = await fetch(target, { method: req.method, headers, body });
  } catch {
    return NextResponse.json(
      {
        error:
          "Backend unreachable — make sure your local server and ngrok tunnel are running.",
      },
      { status: 503 }
    );
  }

  // Forward the upstream response (including streaming body for SSE)
  const resHeaders = new Headers(upstream.headers);
  resHeaders.delete("transfer-encoding"); // Next.js handles this
  resHeaders.delete("connection");

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: resHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
