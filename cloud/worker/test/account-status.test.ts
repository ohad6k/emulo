import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it } from "vitest";

import {
  createBrowserSession,
  resolveOrCreateGitHubIdentity,
} from "../src/auth-store";
import { resolveAccountStatus } from "../src/account-status";
import type { Env, EntitlementState, ProductCode } from "../src/contracts";

const testEnv = env as unknown as Env;
const ACCOUNT_ID = "acct_0123456789abcdef0123456789abcdef";
const SESSION_TOKEN = "s".repeat(43);
const NOW = new Date("2026-07-16T12:30:00.000Z");

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value),
  );
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

function request(authenticated = true): Request {
  return new Request("https://api.example/account", {
    headers: authenticated
      ? { cookie: `__Host-emulo_session=${SESSION_TOKEN}` }
      : {},
  });
}

async function insertEntitlement(
  state: EntitlementState,
  productCode: ProductCode,
  timestamps: {
    currentPeriodEnd?: string | null;
    graceEndsAt?: string | null;
    recoveryEndsAt?: string | null;
  } = {},
): Promise<void> {
  await testEnv.DB.batch([
    testEnv.DB.prepare(
      `INSERT INTO billing_customers
       (provider, provider_customer_id, account_id, external_customer_id, updated_at)
       VALUES ('polar', ?, ?, ?, ?)`,
    ).bind("polar_customer_test", ACCOUNT_ID, ACCOUNT_ID, NOW.toISOString()),
    testEnv.DB.prepare(
      `INSERT INTO entitlements
       (account_id, state, product_code, provider, provider_subscription_id,
        provider_customer_id, provider_product_id, provider_effective_at,
        provider_event_id, current_period_end, grace_ends_at, recovery_ends_at,
        updated_at)
       VALUES (?, ?, ?, 'polar', ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    ).bind(
      ACCOUNT_ID,
      state,
      productCode,
      "polar_subscription_test",
      "polar_customer_test",
      productCode === "founding-monthly"
        ? testEnv.POLAR_MONTHLY_PRODUCT_ID
        : testEnv.POLAR_YEARLY_PRODUCT_ID,
      NOW.toISOString(),
      "polar_event_test",
      timestamps.currentPeriodEnd ?? null,
      timestamps.graceEndsAt ?? null,
      timestamps.recoveryEndsAt ?? null,
      NOW.toISOString(),
    ),
  ]);
}

describe("account status", () => {
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
    await resolveOrCreateGitHubIdentity(testEnv.DB, {
      providerUserId: "12345678",
      proposedAccountId: ACCOUNT_ID,
      createdAt: "2026-07-16T12:00:00.000Z",
    });
    await createBrowserSession(testEnv.DB, {
      sessionHash: await sha256(SESSION_TOKEN),
      accountId: ACCOUNT_ID,
      createdAt: "2026-07-16T12:00:00.000Z",
      expiresAt: "2026-07-16T13:00:00.000Z",
    });
  });

  it("returns a bounded signed-out state without account data", async () => {
    await expect(resolveAccountStatus(request(false), testEnv, NOW)).resolves.toEqual({
      authenticated: false,
      environment: "sandbox",
      checkoutEnabled: false,
    });
  });

  it("maps an authenticated account without an entitlement to none", async () => {
    await expect(resolveAccountStatus(request(), testEnv, NOW)).resolves.toEqual({
      authenticated: true,
      environment: "sandbox",
      checkoutEnabled: false,
      entitlement: {
        state: "none",
        productCode: null,
        currentPeriodEnd: null,
        graceEndsAt: null,
        recoveryEndsAt: null,
      },
    });
  });

  it("returns only the safe active entitlement summary", async () => {
    await insertEntitlement("active", "founding-monthly", {
      currentPeriodEnd: "2026-08-16T12:00:00.000Z",
    });

    const status = await resolveAccountStatus(request(), testEnv, NOW);
    expect(status).toMatchObject({
      authenticated: true,
      entitlement: {
        state: "active",
        productCode: "founding-monthly",
        currentPeriodEnd: "2026-08-16T12:00:00.000Z",
        graceEndsAt: null,
        recoveryEndsAt: null,
      },
    });
    expect(JSON.stringify(status)).not.toMatch(
      /provider|subscription|customer|account_id/i,
    );
  });

  it("preserves bounded lifecycle dates for billing attention", async () => {
    await insertEntitlement("past_due", "founding-yearly", {
      graceEndsAt: "2026-07-23T12:00:00.000Z",
      recoveryEndsAt: "2026-08-15T12:00:00.000Z",
    });

    await expect(resolveAccountStatus(request(), testEnv, NOW)).resolves.toMatchObject({
      authenticated: true,
      entitlement: {
        state: "past_due",
        productCode: "founding-yearly",
        graceEndsAt: "2026-07-23T12:00:00.000Z",
        recoveryEndsAt: "2026-08-15T12:00:00.000Z",
      },
    });
  });

  it("derives checkout availability and production label only from env", async () => {
    await expect(
      resolveAccountStatus(request(), {
        ...testEnv,
        PAID_CHECKOUT_ENABLED: "true",
        POLAR_SERVER: "production",
      }, NOW),
    ).resolves.toMatchObject({
      authenticated: true,
      environment: "production",
      checkoutEnabled: true,
    });
  });

  it("propagates database failures for the Worker boundary to contain", async () => {
    const failingDb = {
      prepare() {
        throw new Error("private database diagnostic");
      },
    } as unknown as D1Database;

    await expect(
      resolveAccountStatus(request(), { ...testEnv, DB: failingDb }, NOW),
    ).rejects.toThrow("private database diagnostic");
  });
});
