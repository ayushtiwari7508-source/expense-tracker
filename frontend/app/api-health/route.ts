import { NextResponse } from "next/server";

/**
 * Minimal liveness endpoint for container healthchecks.
 * Intentionally does not touch the API — process liveness only.
 */
export function GET() {
  return NextResponse.json({ status: "ok" });
}
