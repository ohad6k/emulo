import { resolveBrowserSession } from "./auth-store";

const SESSION_COOKIE = "__Host-emulo_session";

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value),
  );
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

function sessionToken(request: Request): string | null {
  const header = request.headers.get("cookie");
  if (header === null) {
    return null;
  }
  for (const part of header.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === SESSION_COOKIE) {
      const value = rest.join("=");
      return /^[A-Za-z0-9_-]{43}$/.test(value) ? value : null;
    }
  }
  return null;
}

export async function authenticateBrowserSession(
  request: Request,
  db: D1Database,
  now: Date,
): Promise<{ accountId: string } | null> {
  const token = sessionToken(request);
  if (token === null) {
    return null;
  }
  return resolveBrowserSession(db, await sha256(token), now.toISOString());
}
