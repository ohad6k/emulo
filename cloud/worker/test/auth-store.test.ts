import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";

import {
  consumeOAuthFlow,
  createBrowserSession,
  createOAuthFlow,
  resolveBrowserSession,
  resolveOrCreateGitHubIdentity,
  revokeBrowserSession,
} from "../src/auth-store";
import type { Env } from "../src/contracts";

const testEnv = env as unknown as Env;
const ACCOUNT_ID = "acct_0123456789abcdef0123456789abcdef";
const OTHER_ACCOUNT_ID = "acct_ffffffffffffffffffffffffffffffff";
const NOW = "2026-07-16T12:00:00.000Z";
const LATER = "2026-07-16T12:10:00.000Z";

describe("auth store", () => {
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

  it("consumes a valid OAuth state exactly once", async () => {
    await createOAuthFlow(testEnv.DB, {
      stateHash: "a".repeat(64),
      browserBindingHash: "1".repeat(64),
      codeVerifier: "v".repeat(43),
      createdAt: NOW,
      expiresAt: LATER,
    });
    expect(
      await consumeOAuthFlow(
        testEnv.DB,
        "a".repeat(64),
        "1".repeat(64),
        "2026-07-16T12:05:00.000Z",
      ),
    ).toEqual({ codeVerifier: "v".repeat(43) });
    expect(
      await consumeOAuthFlow(
        testEnv.DB,
        "a".repeat(64),
        "1".repeat(64),
        "2026-07-16T12:05:01.000Z",
      ),
    ).toBeNull();
  });

  it("refuses and removes an expired OAuth state", async () => {
    await createOAuthFlow(testEnv.DB, {
      stateHash: "b".repeat(64),
      browserBindingHash: "2".repeat(64),
      codeVerifier: "w".repeat(43),
      createdAt: NOW,
      expiresAt: LATER,
    });
    expect(
      await consumeOAuthFlow(
        testEnv.DB,
        "b".repeat(64),
        "2".repeat(64),
        "2026-07-16T12:10:00.000Z",
      ),
    ).toBeNull();
    expect(
      await testEnv.DB.prepare(
        "SELECT state_hash FROM oauth_flows WHERE state_hash = ?",
      )
        .bind("b".repeat(64))
        .first(),
    ).toBeNull();
  });

  it("rejects an OAuth state lifetime longer than ten minutes", async () => {
    await expect(
      createOAuthFlow(testEnv.DB, {
        stateHash: "e".repeat(64),
        browserBindingHash: "3".repeat(64),
        codeVerifier: "x".repeat(43),
        createdAt: NOW,
        expiresAt: "2026-07-16T12:10:00.001Z",
      }),
    ).rejects.toThrow("OAuth flow lifetime is too long");
    expect(
      await testEnv.DB.prepare(
        "SELECT state_hash FROM oauth_flows WHERE state_hash = ?",
      )
        .bind("e".repeat(64))
        .first(),
    ).toBeNull();
  });

  it("requires the browser binding without consuming another browser's flow", async () => {
    await createOAuthFlow(testEnv.DB, {
      stateHash: "f".repeat(64),
      browserBindingHash: "4".repeat(64),
      codeVerifier: "y".repeat(43),
      createdAt: NOW,
      expiresAt: LATER,
    });
    expect(
      await consumeOAuthFlow(
        testEnv.DB,
        "f".repeat(64),
        "5".repeat(64),
        "2026-07-16T12:05:00.000Z",
      ),
    ).toBeNull();
    expect(
      await consumeOAuthFlow(
        testEnv.DB,
        "f".repeat(64),
        "4".repeat(64),
        "2026-07-16T12:05:00.000Z",
      ),
    ).toEqual({ codeVerifier: "y".repeat(43) });
  });

  it("reclaims abandoned expired flows when a new flow starts", async () => {
    await createOAuthFlow(testEnv.DB, {
      stateHash: "6".repeat(64),
      browserBindingHash: "7".repeat(64),
      codeVerifier: "z".repeat(43),
      createdAt: NOW,
      expiresAt: LATER,
    });
    await createOAuthFlow(testEnv.DB, {
      stateHash: "8".repeat(64),
      browserBindingHash: "9".repeat(64),
      codeVerifier: "q".repeat(43),
      createdAt: "2026-07-16T12:10:00.001Z",
      expiresAt: "2026-07-16T12:20:00.001Z",
    });
    expect(
      await testEnv.DB.prepare(
        "SELECT state_hash FROM oauth_flows WHERE state_hash = ?",
      )
        .bind("6".repeat(64))
        .first(),
    ).toBeNull();
  });

  it("reuses a GitHub identity without creating a second account", async () => {
    expect(
      await resolveOrCreateGitHubIdentity(testEnv.DB, {
        providerUserId: "12345678",
        proposedAccountId: ACCOUNT_ID,
        createdAt: NOW,
      }),
    ).toBe(ACCOUNT_ID);
    expect(
      await resolveOrCreateGitHubIdentity(testEnv.DB, {
        providerUserId: "12345678",
        proposedAccountId: OTHER_ACCOUNT_ID,
        createdAt: LATER,
      }),
    ).toBe(ACCOUNT_ID);
    const count = await testEnv.DB.prepare(
      "SELECT COUNT(*) AS count FROM accounts",
    ).first<{ count: number }>();
    expect(count?.count).toBe(1);
  });

  it("resolves only live hashed browser sessions", async () => {
    await resolveOrCreateGitHubIdentity(testEnv.DB, {
      providerUserId: "12345678",
      proposedAccountId: ACCOUNT_ID,
      createdAt: NOW,
    });
    await createBrowserSession(testEnv.DB, {
      sessionHash: "c".repeat(64),
      accountId: ACCOUNT_ID,
      createdAt: NOW,
      expiresAt: LATER,
    });
    expect(
      await resolveBrowserSession(
        testEnv.DB,
        "c".repeat(64),
        "2026-07-16T12:09:59.000Z",
      ),
    ).toEqual({ accountId: ACCOUNT_ID });
    expect(
      await resolveBrowserSession(testEnv.DB, "c".repeat(64), LATER),
    ).toBeNull();
  });

  it("revokes a browser session idempotently", async () => {
    await resolveOrCreateGitHubIdentity(testEnv.DB, {
      providerUserId: "12345678",
      proposedAccountId: ACCOUNT_ID,
      createdAt: NOW,
    });
    await createBrowserSession(testEnv.DB, {
      sessionHash: "d".repeat(64),
      accountId: ACCOUNT_ID,
      createdAt: NOW,
      expiresAt: LATER,
    });
    await revokeBrowserSession(testEnv.DB, "d".repeat(64), NOW);
    await revokeBrowserSession(testEnv.DB, "d".repeat(64), LATER);
    expect(
      await resolveBrowserSession(
        testEnv.DB,
        "d".repeat(64),
        "2026-07-16T12:05:00.000Z",
      ),
    ).toBeNull();
  });

  it("stores hashes but has no raw state or session-token columns", async () => {
    const flowColumns = await testEnv.DB.prepare("PRAGMA table_info(oauth_flows)")
      .all<{ name: string }>();
    const sessionColumns = await testEnv.DB.prepare(
      "PRAGMA table_info(browser_sessions)",
    ).all<{ name: string }>();
    expect(flowColumns.results.map(({ name }) => name)).not.toContain("state");
    expect(sessionColumns.results.map(({ name }) => name)).not.toContain(
      "session_token",
    );
    expect(sessionColumns.results.map(({ name }) => name)).toContain(
      "session_hash",
    );
  });
});
