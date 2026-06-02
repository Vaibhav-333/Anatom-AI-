/**
 * Catch-all API proxy — forwards every /api/* request to the backend.
 *
 * Uses Node.js runtime (NOT Edge) because Edge runtime has known issues
 * with forwarding POST/PUT/PATCH request bodies (ReadableStream duplex).
 * Node.js runtime reads the body fully before forwarding, which is more
 * reliable for standard REST endpoints.
 *
 * ENV VARS (set in Vercel project settings → Environment Variables):
 *   API_URL              — your Railway/Render backend URL
 *   NEXT_PUBLIC_API_URL  — alternative fallback
 */

import { NextRequest, NextResponse } from "next/server";

// Node.js runtime — reliable body forwarding for POST/PUT/PATCH
export const runtime = "nodejs";

// Extend Vercel serverless function timeout to 60 s (Hobby plan max).
// Gemini PDF analysis + Railway cold-start can easily exceed the default 10 s.
export const maxDuration = 60;

/** Read backend URL at request time — NOT baked at build time. */
function getBackendUrl(): string {
  const raw =
    process.env.API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "https://web-production-698ce.up.railway.app";

  // Guard against env vars set without a protocol (e.g. "web-production-xxx.up.railway.app")
  if (!raw.startsWith("http://") && !raw.startsWith("https://")) {
    return `https://${raw}`;
  }
  return raw.replace(/\/$/, ""); // also strip any trailing slash
}

async function proxy(
  req: NextRequest,
  context: { params: Promise<{ path: string[] }> | { path: string[] } }
) {
  // Support both Next.js 14 (sync params) and Next.js 15 (async params)
  const params = await Promise.resolve(context.params);
  const path = (params.path ?? []).join("/");
  const search = req.nextUrl.search;
  const target = `${getBackendUrl()}/${path}${search}`;

  // Build forwarded headers — strip hop-by-hop headers
  const forwardHeaders: Record<string, string> = {};
  req.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (
      lower === "host" ||
      lower === "connection" ||
      lower === "keep-alive" ||
      lower === "te" ||
      lower === "trailers" ||
      lower === "transfer-encoding" ||
      lower === "upgrade" ||
      lower === "proxy-authenticate" ||
      lower === "proxy-authorization"
    ) {
      return; // skip hop-by-hop
    }
    forwardHeaders[key] = value;
  });

  // Read the body fully as text before forwarding — avoids Edge ReadableStream issues
  let body: string | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    try {
      body = await req.text();
    } catch {
      body = undefined;
    }
  }

  // Abort the upstream fetch 4 s before Vercel's hard function cutoff so we
  // can return a friendly JSON error instead of a bare platform-level 504.
  const controller = new AbortController();
  const abortTimer = setTimeout(() => controller.abort(), 56_000); // 56 s

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers: forwardHeaders,
      body: body,
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(abortTimer);
    if (err instanceof Error && err.name === "AbortError") {
      return NextResponse.json(
        {
          detail:
            "The AI analysis is taking longer than expected (the server may be waking up from sleep). Please wait 30 seconds and try again.",
        },
        { status: 504 }
      );
    }
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json(
      {
        detail: `Backend unreachable (${message}). The server may be starting up — please try again in a moment.`,
      },
      { status: 503 }
    );
  } finally {
    clearTimeout(abortTimer);
  }

  // Forward the response
  const resBody = await upstream.text();
  const resHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (lower === "transfer-encoding" || lower === "connection") return;
    resHeaders.set(key, value);
  });
  // Ensure content-type is preserved
  if (!resHeaders.has("content-type")) {
    resHeaders.set("content-type", "application/json");
  }

  return new NextResponse(resBody, {
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
