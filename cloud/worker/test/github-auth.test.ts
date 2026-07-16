import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createOAuthFlow } from "../src/auth-store";
import {
  beginGitHubOAuth,
  completeGitHubOAuth,
  type GitHubAuthDependencies,
} from "../src/github-auth";
import type { Env } from "../src/contracts";

const testEnv = env as unknown as Env;
const NOW = new Date("2026-07-16T12:00:00.000Z");
const STATE = "state_that_is_long_and_random_enough_for_oauth";
const VERIFIER = "v".repeat(43);
const BROWSER_BINDING = "browser_binding_that_is_random_enough_12345";

async function sha256(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

function dependencies(fetcher = vi.fn()): GitHubAuthDependencies {
  let randomCall = 0;
  return {
    now: () => new Date(NOW),
    randomBytes: (length) => {
      randomCall += 1;
      return new Uint8Array(length).fill(randomCall);
    },
    fetch: fetcher as typeof fetch,
  };
}

async function seedFlow() {
  await createOAuthFlow(testEnv.DB, {
    stateHash: await sha256(STATE),
    browserBindingHash: await sha256(BROWSER_BINDING),
    codeVerifier: VERIFIER,
    createdAt: NOW.toISOString(),
    expiresAt: "2026-07-16T12:10:00.000Z",
  });
}

describe("GitHub OAuth", () => {
  beforeEach(async () => {
    await testEnv.DB.batch([
      testEnv.DB.prepare("DELETE FROM browser_sessions"),
      testEnv.DB.prepare("DELETE FROM oauth_identities"),
      testEnv.DB.prepare("DELETE FROM oauth_flows"),
      testEnv.DB.prepare("DELETE FROM entitlements"),
      testEnv.DB.prepare("DELETE FROM billing_events"),
      testEnv.DB.prepare("DELETE FROM billing_customers"),
      testEnv.DB.prepare("DELETE FROM accounts"),
    ]);
  });

  it("starts GitHub OAuth with state and S256 PKCE but no scopes", async () => {
    const response = await beginGitHubOAuth(testEnv, dependencies());
    expect(response.status).toBe(302);
    const location = new URL(response.headers.get("location") ?? "");
    expect(location.origin + location.pathname).toBe(
      "https://github.com/login/oauth/authorize",
    );
    expect(location.searchParams.get("client_id")).toBe("github-client-test");
    expect(location.searchParams.get("redirect_uri")).toBe(
      "https://api.example/v1/auth/github/callback",
    );
    expect(location.searchParams.get("code_challenge_method")).toBe("S256");
    expect(location.searchParams.get("code_challenge")).toHaveLength(43);
    expect(location.searchParams.has("scope")).toBe(false);
    expect(location.searchParams.get("state")).toHaveLength(43);
    expect(response.headers.get("cache-control")).toBe("no-store");
    expect(response.headers.get("set-cookie")).toContain(
      "__Host-emulo_oauth=",
    );
    const stored = await testEnv.DB.prepare(
      "SELECT state_hash, code_verifier FROM oauth_flows",
    ).first<{ state_hash: string; code_verifier: string }>();
    expect(stored?.state_hash).toHaveLength(64);
    expect(stored?.state_hash).not.toBe(location.searchParams.get("state"));
    expect(stored?.code_verifier).toHaveLength(43);
  });

  it("revalidates GitHub identity and creates a hashed browser session", async () => {
    await seedFlow();
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        Response.json({
          access_token: "github-test-access-token",
          token_type: "bearer",
          scope: "",
        }),
      )
      .mockResolvedValueOnce(Response.json({ id: 12345678, login: "ignored" }));
    const response = await completeGitHubOAuth(
      new Request(
        `https://api.example/v1/auth/github/callback?code=temporary-code&state=${STATE}`,
        { headers: { cookie: `__Host-emulo_oauth=${BROWSER_BINDING}` } },
      ),
      testEnv,
      dependencies(fetcher),
    );
    expect(response.status).toBe(200);
    expect(fetcher).toHaveBeenCalledTimes(2);
    const tokenRequest = fetcher.mock.calls[0];
    expect(tokenRequest[0]).toBe("https://github.com/login/oauth/access_token");
    expect(String((tokenRequest[1] as RequestInit).body)).toContain(
      `code_verifier=${VERIFIER}`,
    );
    const userRequest = fetcher.mock.calls[1];
    expect(userRequest[0]).toBe("https://api.github.com/user");
    expect((userRequest[1] as RequestInit).headers).toMatchObject({
      Authorization: "Bearer github-test-access-token",
    });
    const cookie = response.headers.get("set-cookie") ?? "";
    expect(cookie).toContain("__Host-emulo_session=");
    expect(cookie).toContain("HttpOnly");
    expect(cookie).toContain("Secure");
    expect(cookie).toContain("SameSite=Lax");
    expect(cookie).not.toContain("github-test-access-token");
    const stored = await testEnv.DB.prepare(
      "SELECT session_hash FROM browser_sessions",
    ).first<{ session_hash: string }>();
    expect(stored?.session_hash).toHaveLength(64);
    expect(cookie).not.toContain(stored?.session_hash ?? "missing");
    const columns = await testEnv.DB.prepare("PRAGMA table_info(browser_sessions)")
      .all<{ name: string }>();
    expect(columns.results.map(({ name }) => name)).not.toContain("access_token");
  });

  it("rejects replayed state before contacting GitHub", async () => {
    await seedFlow();
    const fetcher = vi.fn().mockResolvedValue(
      Response.json({ access_token: "github-test-access-token" }),
    );
    const request = () =>
      new Request(
        `https://api.example/v1/auth/github/callback?code=temporary-code&state=${STATE}`,
        { headers: { cookie: `__Host-emulo_oauth=${BROWSER_BINDING}` } },
      );
    expect(
      (await completeGitHubOAuth(request(), testEnv, dependencies(fetcher))).status,
    ).toBe(502);
    const callsAfterFirst = fetcher.mock.calls.length;
    expect(
      (await completeGitHubOAuth(request(), testEnv, dependencies(fetcher))).status,
    ).toBe(400);
    expect(fetcher).toHaveBeenCalledTimes(callsAfterFirst);
  });

  it("returns a safe upstream failure without setting a cookie", async () => {
    await seedFlow();
    const response = await completeGitHubOAuth(
      new Request(
        `https://api.example/v1/auth/github/callback?code=temporary-code&state=${STATE}`,
        { headers: { cookie: `__Host-emulo_oauth=${BROWSER_BINDING}` } },
      ),
      testEnv,
      dependencies(vi.fn().mockResolvedValue(new Response("no", { status: 503 }))),
    );
    expect(response.status).toBe(502);
    expect(response.headers.get("set-cookie")).toContain(
      "__Host-emulo_oauth=;",
    );
    expect(response.headers.get("set-cookie")).not.toContain(
      "__Host-emulo_session=",
    );
    expect(await response.text()).not.toContain("no");
  });

  it("rejects a callback from a different browser without consuming the flow", async () => {
    await seedFlow();
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(
        Response.json({
          access_token: "github-test-access-token",
          token_type: "bearer",
          scope: "",
        }),
      )
      .mockResolvedValueOnce(Response.json({ id: 12345678 }));
    const callback = (cookie?: string) =>
      new Request(
        `https://api.example/v1/auth/github/callback?code=temporary-code&state=${STATE}`,
        cookie === undefined ? undefined : { headers: { cookie } },
      );
    expect(
      (await completeGitHubOAuth(callback(), testEnv, dependencies(fetcher))).status,
    ).toBe(400);
    expect(fetcher).not.toHaveBeenCalled();
    expect(
      (
        await completeGitHubOAuth(
          callback(`__Host-emulo_oauth=${BROWSER_BINDING}`),
          testEnv,
          dependencies(fetcher),
        )
      ).status,
    ).toBe(200);
  });
});
