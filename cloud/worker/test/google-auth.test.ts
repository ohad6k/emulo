import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createOAuthFlow } from "../src/auth-store";
import type { Env } from "../src/contracts";
import {
  beginGoogleOAuth,
  completeGoogleOAuth,
  type GoogleAuthDependencies,
} from "../src/google-auth";

const testEnv = env as unknown as Env;
const NOW = new Date("2026-07-17T12:00:00.000Z");
const STATE = "state_that_is_long_and_random_enough_for_google";
const BROWSER_BINDING = "browser_binding_that_is_random_enough_67890";
const VERIFIER = "v".repeat(43);
const NONCE_HASH = "a".repeat(64);
const ID_TOKEN = `${"a".repeat(30)}.${"b".repeat(60)}.${"c".repeat(50)}`;

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value),
  );
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

function dependencies(
  fetcher: typeof fetch = vi.fn() as unknown as typeof fetch,
  verifier = vi.fn().mockResolvedValue({ subject: "google-subject-123" }),
): GoogleAuthDependencies {
  let randomCall = 0;
  return {
    now: () => new Date(NOW),
    randomBytes: (length) => {
      randomCall += 1;
      return new Uint8Array(length).fill(randomCall);
    },
    fetch: fetcher,
    verifyIdToken: verifier,
  };
}

async function seedFlow(provider: "google" | "github" = "google") {
  await createOAuthFlow(testEnv.DB, {
    provider,
    stateHash: await sha256(STATE),
    browserBindingHash: await sha256(BROWSER_BINDING),
    codeVerifier: VERIFIER,
    nonceHash: provider === "google" ? NONCE_HASH : null,
    createdAt: NOW.toISOString(),
    expiresAt: "2026-07-17T12:10:00.000Z",
  });
}

function callback(cookie = BROWSER_BINDING) {
  return new Request(
    `https://api.example/v1/auth/google/callback?code=temporary-code&state=${STATE}`,
    { headers: { cookie: `__Host-emulo_oauth=${cookie}` } },
  );
}

describe("Google OAuth", () => {
  beforeEach(async () => {
    await testEnv.DB.batch([
      testEnv.DB.prepare("DELETE FROM oauth_diagnostics"),
      testEnv.DB.prepare("DELETE FROM browser_sessions"),
      testEnv.DB.prepare("DELETE FROM oauth_identities"),
      testEnv.DB.prepare("DELETE FROM oauth_flows"),
      testEnv.DB.prepare("DELETE FROM entitlements"),
      testEnv.DB.prepare("DELETE FROM billing_events"),
      testEnv.DB.prepare("DELETE FROM billing_customers"),
      testEnv.DB.prepare("DELETE FROM accounts"),
    ]);
  });

  it("starts Google OAuth with exact callback, minimal scopes, state, PKCE, and nonce", async () => {
    const response = await beginGoogleOAuth(testEnv, dependencies());
    expect(response.status).toBe(302);
    const location = new URL(response.headers.get("location") ?? "");
    expect(location.origin + location.pathname).toBe(
      "https://accounts.google.com/o/oauth2/v2/auth",
    );
    expect(location.searchParams.get("client_id")).toBe(
      "google-client-test.apps.googleusercontent.com",
    );
    expect(location.searchParams.get("redirect_uri")).toBe(
      "https://api.example/v1/auth/google/callback",
    );
    expect(location.searchParams.get("response_type")).toBe("code");
    expect(location.searchParams.get("scope")).toBe("openid email profile");
    expect(location.searchParams.get("code_challenge_method")).toBe("S256");
    expect(location.searchParams.get("code_challenge")).toHaveLength(43);
    expect(location.searchParams.get("state")).toHaveLength(43);
    expect(location.searchParams.get("nonce")).toHaveLength(43);
    expect(location.searchParams.has("access_type")).toBe(false);
    expect(response.headers.get("set-cookie")).toContain("__Host-emulo_oauth=");
    const stored = await testEnv.DB.prepare(
      "SELECT provider, state_hash, nonce_hash FROM oauth_flows",
    ).first<{ provider: string; state_hash: string; nonce_hash: string }>();
    expect(stored?.provider).toBe("google");
    expect(stored?.state_hash).toHaveLength(64);
    expect(stored?.nonce_hash).toHaveLength(64);
    expect(stored?.nonce_hash).not.toBe(location.searchParams.get("nonce"));
  });

  it("exchanges the code, verifies the ID token, and creates a hashed session", async () => {
    await seedFlow();
    const fetcher = vi.fn().mockResolvedValue(
      Response.json({
        access_token: "upstream-access-token-never-store",
        id_token: ID_TOKEN,
        token_type: "Bearer",
        expires_in: 3600,
      }),
    );
    const verifier = vi.fn().mockResolvedValue({ subject: "google-subject-123" });
    const response = await completeGoogleOAuth(
      callback(),
      testEnv,
      dependencies(fetcher, verifier),
    );

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe(
      "https://api.example/account?signin=complete",
    );
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][0]).toBe("https://oauth2.googleapis.com/token");
    const body = String((fetcher.mock.calls[0][1] as RequestInit).body);
    expect(body).toContain("grant_type=authorization_code");
    expect(body).toContain(`code_verifier=${VERIFIER}`);
    expect(body).not.toContain("access_type");
    expect(verifier).toHaveBeenCalledWith(ID_TOKEN, {
      clientId: "google-client-test.apps.googleusercontent.com",
      nonceHash: NONCE_HASH,
      now: NOW,
    });
    const identity = await testEnv.DB.prepare(
      "SELECT provider, provider_user_id FROM oauth_identities",
    ).first<{ provider: string; provider_user_id: string }>();
    expect(identity).toEqual({
      provider: "google",
      provider_user_id: "google-subject-123",
    });
    const session = await testEnv.DB.prepare(
      "SELECT session_hash FROM browser_sessions",
    ).first<{ session_hash: string }>();
    expect(session?.session_hash).toHaveLength(64);
    const cookie = response.headers.get("set-cookie") ?? "";
    expect(cookie).toContain("__Host-emulo_session=");
    expect(cookie).not.toContain(ID_TOKEN);
    expect(cookie).not.toContain("upstream-access-token-never-store");
  });

  it("does not consume a GitHub flow or contact Google", async () => {
    await seedFlow("github");
    const fetcher = vi.fn();
    const response = await completeGoogleOAuth(
      callback(),
      testEnv,
      dependencies(fetcher),
    );
    expect(response.status).toBe(400);
    expect(fetcher).not.toHaveBeenCalled();
    expect(
      await testEnv.DB.prepare("SELECT state_hash FROM oauth_flows").first(),
    ).not.toBeNull();
  });

  it("rejects the wrong browser binding without consuming the flow", async () => {
    await seedFlow();
    const response = await completeGoogleOAuth(
      callback("another_browser_binding_that_is_long_enough"),
      testEnv,
      dependencies(),
    );
    expect(response.status).toBe(400);
    expect(
      await testEnv.DB.prepare("SELECT state_hash FROM oauth_flows").first(),
    ).not.toBeNull();
  });

  it("fails closed when token exchange or ID-token verification fails", async () => {
    for (const [payload, verifier] of [
      [{ error: "invalid_grant" }, vi.fn()],
      [{ id_token: ID_TOKEN }, vi.fn().mockRejectedValue(new Error("bad token"))],
    ] as const) {
      await seedFlow();
      const response = await completeGoogleOAuth(
        callback(),
        testEnv,
        dependencies(vi.fn().mockResolvedValue(Response.json(payload)), verifier),
      );
      expect(response.status).toBe(502);
      expect(await testEnv.DB.prepare("SELECT account_id FROM accounts").first()).toBeNull();
      await testEnv.DB.prepare("DELETE FROM oauth_flows").run();
    }
  });

  it("returns a safe unavailable response when Google is not configured", async () => {
    const response = await beginGoogleOAuth(
      { ...testEnv, GOOGLE_CLIENT_ID: "not-configured", GOOGLE_CLIENT_SECRET: undefined },
      dependencies(),
    );
    expect(response.status).toBe(503);
    const body = await response.text();
    expect(body).toContain("Google sign-in is not available yet");
    expect(body).toContain('class="brand-lockup"');
    expect(body).toContain('href="/account.css"');
    expect(body).toContain('href="/account"');
    expect(body).not.toMatch(/secret|client id/i);
  });
});
