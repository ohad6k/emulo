import {
  consumeOAuthFlow,
  createBrowserSession,
  createOAuthFlow,
  resolveOrCreateOAuthIdentity,
} from "./auth-store";
import type { Env } from "./contracts";
import {
  verifyGoogleIdToken,
  type GoogleTokenVerificationOptions,
} from "./google-token";

const CALLBACK_PATH = "/v1/auth/google/callback";
const SESSION_COOKIE = "__Host-emulo_session";
const FLOW_COOKIE = "__Host-emulo_oauth";
const FLOW_LIFETIME_MS = 10 * 60 * 1000;
const SESSION_LIFETIME_SECONDS = 24 * 60 * 60;

export interface GoogleAuthDependencies {
  now: () => Date;
  randomBytes: (length: number) => Uint8Array;
  fetch: typeof fetch;
  verifyIdToken: (
    token: string,
    options: GoogleTokenVerificationOptions,
  ) => Promise<{ subject: string }>;
}

const defaultDependencies: GoogleAuthDependencies = {
  now: () => new Date(),
  randomBytes: (length) => crypto.getRandomValues(new Uint8Array(length)),
  fetch,
  verifyIdToken: verifyGoogleIdToken,
};

function base64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary)
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replace(/=+$/, "");
}

async function digest(value: string): Promise<Uint8Array<ArrayBuffer>> {
  return new Uint8Array(
    await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)),
  );
}

async function hexDigest(value: string): Promise<string> {
  return Array.from(await digest(value), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

function publicBase(env: Env): URL | null {
  try {
    const url = new URL(env.PUBLIC_BASE_URL);
    return url.protocol === "https:" &&
      !url.username &&
      !url.password &&
      url.pathname === "/" &&
      !url.search &&
      !url.hash
      ? url
      : null;
  } catch {
    return null;
  }
}

function configurationValid(env: Env): env is Env & {
  GOOGLE_CLIENT_ID: string;
  GOOGLE_CLIENT_SECRET: string;
} {
  return (
    publicBase(env) !== null &&
    typeof env.GOOGLE_CLIENT_ID === "string" &&
    /^[A-Za-z0-9._-]{8,256}$/.test(env.GOOGLE_CLIENT_ID) &&
    env.GOOGLE_CLIENT_ID !== "not-configured" &&
    typeof env.GOOGLE_CLIENT_SECRET === "string" &&
    env.GOOGLE_CLIENT_SECRET.length >= 8
  );
}

function callbackUrl(env: Env): string {
  return new URL(CALLBACK_PATH, publicBase(env)!).toString();
}

function safeResponse(status: number, message: string): Response {
  return new Response(
    `<!doctype html><meta charset="utf-8"><title>Emulo</title><p>${message}</p>`,
    {
      status,
      headers: {
        "cache-control": "no-store",
        "content-security-policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        "content-type": "text/html; charset=utf-8",
        "referrer-policy": "no-referrer",
        "x-content-type-options": "nosniff",
      },
    },
  );
}

function cookieValue(request: Request): string | null {
  const header = request.headers.get("cookie");
  if (header === null) return null;
  for (const part of header.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === FLOW_COOKIE) {
      const value = rest.join("=");
      return /^[A-Za-z0-9_-]{32,128}$/.test(value) ? value : null;
    }
  }
  return null;
}

function clearFlowCookie(response: Response): Response {
  response.headers.append(
    "set-cookie",
    `${FLOW_COOKIE}=; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Lax`,
  );
  return response;
}

async function upstreamJson(response: Response): Promise<Record<string, unknown> | null> {
  try {
    const parsed: unknown = await response.json();
    return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

type GoogleStage =
  | "token_exchange"
  | "id_token_verification"
  | "identity_write"
  | "session_write";

async function recordDiagnostic(
  env: Env,
  stage: GoogleStage,
  statusCode: number | null,
  errorCode: string | null,
  createdAt: string,
): Promise<void> {
  await env.DB.batch([
    env.DB.prepare(
      `INSERT INTO oauth_diagnostics
       (provider, stage, status_code, error_code, created_at)
       VALUES ('google', ?, ?, ?, ?)`,
    ).bind(stage, statusCode, errorCode, createdAt),
    env.DB.prepare(
      `DELETE FROM oauth_diagnostics
       WHERE diagnostic_id NOT IN (
         SELECT diagnostic_id FROM oauth_diagnostics
         ORDER BY diagnostic_id DESC LIMIT 100
       )`,
    ),
  ]);
}

function accountId(bytes: Uint8Array): string {
  return `acct_${Array.from(bytes, (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("")}`;
}

export async function beginGoogleOAuth(
  env: Env,
  dependencies: GoogleAuthDependencies = defaultDependencies,
): Promise<Response> {
  if (!configurationValid(env)) return safeResponse(503, "Google sign-in is not available yet.");
  const now = dependencies.now();
  const state = base64Url(dependencies.randomBytes(32));
  const codeVerifier = base64Url(dependencies.randomBytes(32));
  const browserBinding = base64Url(dependencies.randomBytes(32));
  const nonce = base64Url(dependencies.randomBytes(32));
  await createOAuthFlow(env.DB, {
    provider: "google",
    stateHash: await hexDigest(state),
    browserBindingHash: await hexDigest(browserBinding),
    codeVerifier,
    nonceHash: await hexDigest(nonce),
    createdAt: now.toISOString(),
    expiresAt: new Date(now.getTime() + FLOW_LIFETIME_MS).toISOString(),
  });
  const authorize = new URL("https://accounts.google.com/o/oauth2/v2/auth");
  authorize.searchParams.set("client_id", env.GOOGLE_CLIENT_ID);
  authorize.searchParams.set("redirect_uri", callbackUrl(env));
  authorize.searchParams.set("response_type", "code");
  authorize.searchParams.set("scope", "openid email profile");
  authorize.searchParams.set("state", state);
  authorize.searchParams.set("nonce", nonce);
  authorize.searchParams.set(
    "code_challenge",
    base64Url(await digest(codeVerifier)),
  );
  authorize.searchParams.set("code_challenge_method", "S256");
  return new Response(null, {
    status: 302,
    headers: {
      "cache-control": "no-store",
      location: authorize.toString(),
      "referrer-policy": "no-referrer",
      "set-cookie": `${FLOW_COOKIE}=${browserBinding}; Path=/; Max-Age=600; Secure; HttpOnly; SameSite=Lax`,
    },
  });
}

export async function completeGoogleOAuth(
  request: Request,
  env: Env,
  dependencies: GoogleAuthDependencies = defaultDependencies,
): Promise<Response> {
  if (!configurationValid(env)) {
    return clearFlowCookie(safeResponse(503, "Google sign-in is not available yet."));
  }
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const browserBinding = cookieValue(request);
  if (
    url.searchParams.has("error") ||
    code === null ||
    !/^[A-Za-z0-9._~-]{1,256}$/.test(code) ||
    state === null ||
    !/^[A-Za-z0-9_-]{32,128}$/.test(state) ||
    browserBinding === null
  ) {
    return clearFlowCookie(safeResponse(400, "Sign-in could not be completed."));
  }
  const now = dependencies.now();
  const flow = await consumeOAuthFlow(
    env.DB,
    "google",
    await hexDigest(state),
    await hexDigest(browserBinding),
    now.toISOString(),
  );
  if (flow?.nonceHash === undefined) {
    return clearFlowCookie(safeResponse(400, "Sign-in could not be completed."));
  }

  let stage: GoogleStage = "token_exchange";
  try {
    const tokenResponse = await dependencies.fetch("https://oauth2.googleapis.com/token", {
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        client_id: env.GOOGLE_CLIENT_ID,
        client_secret: env.GOOGLE_CLIENT_SECRET,
        code,
        code_verifier: flow.codeVerifier,
        grant_type: "authorization_code",
        redirect_uri: callbackUrl(env),
      }).toString(),
    });
    const tokenPayload = await upstreamJson(tokenResponse);
    const idToken = tokenPayload?.id_token;
    if (
      !tokenResponse.ok ||
      typeof idToken !== "string" ||
      idToken.length < 64 ||
      idToken.length > 8_192
    ) {
      const upstreamCode = tokenPayload?.error;
      await recordDiagnostic(
        env,
        "token_exchange",
        tokenResponse.status,
        typeof upstreamCode === "string" && /^[a-z_]{1,64}$/.test(upstreamCode)
          ? upstreamCode
          : null,
        now.toISOString(),
      );
      return clearFlowCookie(
        safeResponse(502, "Google sign-in is temporarily unavailable."),
      );
    }

    stage = "id_token_verification";
    const identity = await dependencies.verifyIdToken(idToken, {
      clientId: env.GOOGLE_CLIENT_ID,
      nonceHash: flow.nonceHash,
      now,
    });
    stage = "identity_write";
    const resolvedAccountId = await resolveOrCreateOAuthIdentity(env.DB, {
      provider: "google",
      providerUserId: identity.subject,
      proposedAccountId: accountId(dependencies.randomBytes(16)),
      createdAt: now.toISOString(),
    });
    stage = "session_write";
    const sessionToken = base64Url(dependencies.randomBytes(32));
    await createBrowserSession(env.DB, {
      sessionHash: await hexDigest(sessionToken),
      accountId: resolvedAccountId,
      createdAt: now.toISOString(),
      expiresAt: new Date(now.getTime() + SESSION_LIFETIME_SECONDS * 1000).toISOString(),
    });
    const response = new Response(null, {
      status: 303,
      headers: {
        "cache-control": "no-store",
        location: new URL("/account?signin=complete", publicBase(env)!).toString(),
        "referrer-policy": "no-referrer",
        "set-cookie": `${SESSION_COOKIE}=${sessionToken}; Path=/; Max-Age=${SESSION_LIFETIME_SECONDS}; Secure; HttpOnly; SameSite=Lax`,
      },
    });
    return clearFlowCookie(response);
  } catch (error) {
    const errorCode =
      error instanceof Error && /^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(error.name)
        ? error.name
        : "unknown";
    try {
      await recordDiagnostic(env, stage, null, errorCode, now.toISOString());
    } catch {
      // Authentication must remain fail-closed even if diagnostics storage fails.
    }
    console.warn("google_oauth_failure", { stage, error: errorCode });
    return clearFlowCookie(
      safeResponse(502, "Google sign-in is temporarily unavailable."),
    );
  }
}
