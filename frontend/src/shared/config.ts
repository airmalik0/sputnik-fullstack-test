/**
 * Runtime configuration sourced from build-time env vars.
 *
 * Centralised so a future host change is a one-place edit. The original
 * code hardcoded `http://localhost:8000` in three call sites; pulling
 * the value through here also lets us deploy the frontend behind a
 * different domain in production without rebuilding component code.
 *
 * NEXT_PUBLIC_* is the only env-var prefix Next exposes to the browser
 * bundle, which is the only place this constant is used.
 */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
