import {
  consumeOAuthFlow,
  createBrowserSession,
  createOAuthFlow,
  resolveOrCreateGitHubIdentity,
} from "./auth-store";
import type { Env } from "./contracts";

const CALLBACK_PATH = "/v1/auth/github/callback";
const SESSION_COOKIE = "__Host-emulo_session";
const FLOW_COOKIE = "__Host-emulo_oauth";
const FLOW_LIFETIME_MS = 10 * 60 * 1000;
const SESSION_LIFETIME_SECONDS = 24 * 60 * 60;

export interface GitHubAuthDependencies {
  now: () => Date;
  randomBytes: (length: number) => Uint8Array;
  fetch: typeof fetch;
}

const defaultDependencies: GitHubAuthDependencies = {
  now: () => new Date(),
  randomBytes: (length) => crypto.getRandomValues(new Uint8Array(length)),
  fetch,
};

function base64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary)
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replace(/=+$/, "");
}

async function digest(value: string): Promise<Uint8Array<ArrayBuffer>> {
  const bytes = new TextEncoder().encode(value);
  return new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
}

async function hexDigest(value: string): Promise<string> {
  return Array.from(await digest(value), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

function publicBase(env: Env): URL | null {
  try {
    const url = new URL(env.PUBLIC_BASE_URL);
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      url.pathname !== "/" ||
      url.search ||
      url.hash
    ) {
      return null;
    }
    return url;
  } catch {
    return null;
  }
}

function configurationValid(env: Env): boolean {
  return (
    publicBase(env) !== null &&
    /^[A-Za-z0-9_-]{1,128}$/.test(env.GITHUB_CLIENT_ID) &&
    env.GITHUB_CLIENT_ID !== "not-configured" &&
    typeof env.GITHUB_CLIENT_SECRET === "string" &&
    env.GITHUB_CLIENT_SECRET.length >= 8
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

function upstreamErrorCode(payload: Record<string, unknown> | null): string | null {
  const value = payload?.error;
  return typeof value === "string" && /^[a-z_]{1,64}$/.test(value) ? value : null;
}

function cookieValue(request: Request, name: string): string | null {
  const header = request.headers.get("cookie");
  if (header === null) {
    return null;
  }
  for (const part of header.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) {
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

export async function beginGitHubOAuth(
  env: Env,
  dependencies: GitHubAuthDependencies = defaultDependencies,
): Promise<Response> {
  if (!configurationValid(env)) {
    return safeResponse(503, "Sign-in is not configured.");
  }
  const now = dependencies.now();
  const state = base64Url(dependencies.randomBytes(32));
  const codeVerifier = base64Url(dependencies.randomBytes(32));
  const browserBinding = base64Url(dependencies.randomBytes(32));
  const codeChallenge = base64Url(await digest(codeVerifier));
  await createOAuthFlow(env.DB, {
    stateHash: await hexDigest(state),
    browserBindingHash: await hexDigest(browserBinding),
    codeVerifier,
    createdAt: now.toISOString(),
    expiresAt: new Date(now.getTime() + FLOW_LIFETIME_MS).toISOString(),
  });

  const authorize = new URL("https://github.com/login/oauth/authorize");
  authorize.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
  authorize.searchParams.set("redirect_uri", callbackUrl(env));
  authorize.searchParams.set("state", state);
  authorize.searchParams.set("code_challenge", codeChallenge);
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

async function upstreamJson(
  response: Response,
): Promise<Record<string, unknown> | null> {
  try {
    const parsed: unknown = await response.json();
    return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

async function recordOAuthDiagnostic(
  env: Env,
  input: {
    stage: "token_exchange" | "user_lookup";
    statusCode: number;
    errorCode: string | null;
    createdAt: string;
  },
): Promise<void> {
  await env.DB.batch([
    env.DB
      .prepare(
        `INSERT INTO oauth_diagnostics
         (provider, stage, status_code, error_code, created_at)
         VALUES ('github', ?, ?, ?, ?)`,
      )
      .bind(input.stage, input.statusCode, input.errorCode, input.createdAt),
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

export async function completeGitHubOAuth(
  request: Request,
  env: Env,
  dependencies: GitHubAuthDependencies = defaultDependencies,
): Promise<Response> {
  if (!configurationValid(env)) {
    return clearFlowCookie(safeResponse(503, "Sign-in is not configured."));
  }
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const browserBinding = cookieValue(request, FLOW_COOKIE);
  if (
    url.searchParams.has("error") ||
    code === null ||
    !/^[A-Za-z0-9_-]{1,256}$/.test(code) ||
    state === null ||
    !/^[A-Za-z0-9_-]{32,128}$/.test(state) ||
    browserBinding === null
  ) {
    return clearFlowCookie(safeResponse(400, "Sign-in could not be completed."));
  }
  const now = dependencies.now();
  const flow = await consumeOAuthFlow(
    env.DB,
    await hexDigest(state),
    await hexDigest(browserBinding),
    now.toISOString(),
  );
  if (flow === null) {
    return clearFlowCookie(safeResponse(400, "Sign-in could not be completed."));
  }

  try {
    const tokenResponse = await dependencies.fetch(
      "https://github.com/login/oauth/access_token",
      {
        method: "POST",
        headers: {
          accept: "application/json",
          "content-type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          client_id: env.GITHUB_CLIENT_ID,
          client_secret: env.GITHUB_CLIENT_SECRET,
          code,
          redirect_uri: callbackUrl(env),
          code_verifier: flow.codeVerifier,
        }).toString(),
      },
    );
    const tokenPayload = await upstreamJson(tokenResponse);
    const accessToken = tokenPayload?.access_token;
    if (typeof accessToken !== "string" || accessToken.length < 8 || accessToken.length > 512) {
      await recordOAuthDiagnostic(env, {
        stage: "token_exchange",
        statusCode: tokenResponse.status,
        errorCode: upstreamErrorCode(tokenPayload),
        createdAt: now.toISOString(),
      });
      console.warn("github_oauth_failure", {
        stage: "token_exchange",
        status: tokenResponse.status,
        error: upstreamErrorCode(tokenPayload),
      });
      return clearFlowCookie(safeResponse(502, "GitHub sign-in is temporarily unavailable."));
    }

    const userResponse = await dependencies.fetch("https://api.github.com/user", {
      headers: {
        accept: "application/vnd.github+json",
        Authorization: `Bearer ${accessToken}`,
        "user-agent": "emulo-autopilot",
        "x-github-api-version": "2022-11-28",
      },
    });
    const user = await upstreamJson(userResponse);
    if (
      typeof user?.id !== "number" ||
      !Number.isSafeInteger(user.id) ||
      user.id <= 0
    ) {
      await recordOAuthDiagnostic(env, {
        stage: "user_lookup",
        statusCode: userResponse.status,
        errorCode: null,
        createdAt: now.toISOString(),
      });
      console.warn("github_oauth_failure", {
        stage: "user_lookup",
        status: userResponse.status,
      });
      return clearFlowCookie(safeResponse(502, "GitHub sign-in is temporarily unavailable."));
    }

    const resolvedAccountId = await resolveOrCreateGitHubIdentity(env.DB, {
      providerUserId: String(user.id),
      proposedAccountId: accountId(dependencies.randomBytes(16)),
      createdAt: now.toISOString(),
    });
    const sessionToken = base64Url(dependencies.randomBytes(32));
    await createBrowserSession(env.DB, {
      sessionHash: await hexDigest(sessionToken),
      accountId: resolvedAccountId,
      createdAt: now.toISOString(),
      expiresAt: new Date(
        now.getTime() + SESSION_LIFETIME_SECONDS * 1000,
      ).toISOString(),
    });
    const response = new Response(null, {
      status: 303,
      headers: {
        "cache-control": "no-store",
        location: new URL("/account?signin=complete", publicBase(env)!).toString(),
        "referrer-policy": "no-referrer",
      },
    });
    response.headers.set(
      "set-cookie",
      `${SESSION_COOKIE}=${sessionToken}; Path=/; Max-Age=${SESSION_LIFETIME_SECONDS}; Secure; HttpOnly; SameSite=Lax`,
    );
    return clearFlowCookie(response);
  } catch (error) {
    console.warn("github_oauth_failure", {
      stage: "internal",
      error: error instanceof Error ? error.name : "unknown",
    });
    return clearFlowCookie(safeResponse(502, "GitHub sign-in is temporarily unavailable."));
  }
}
