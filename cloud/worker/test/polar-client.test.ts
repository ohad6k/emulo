import { env } from "cloudflare:workers";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createBrowserSession, resolveOrCreateGitHubIdentity } from "../src/auth-store";
import type { Env } from "../src/contracts";
import {
  handlePolarCheckout,
  handlePolarPortal,
  type PolarBillingDependencies,
} from "../src/polar-client";

const testEnv = env as unknown as Env;
const ACCOUNT_ID = "acct_0123456789abcdef0123456789abcdef";
const SESSION_TOKEN = "s".repeat(43);
const SESSION_HASH = "a".repeat(64);
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

function enabledEnv(changes: Partial<Env> = {}): Env {
  return {
    ...testEnv,
    PAID_CHECKOUT_ENABLED: "true",
    POLAR_SERVER: "sandbox",
    POLAR_ACCESS_TOKEN: "polar-test-placeholder",
    ...changes,
  };
}

function billingDependencies() {
  const createCheckout = vi.fn().mockResolvedValue({
    url: "https://sandbox.polar.sh/checkout/test-checkout",
  });
  const createPortal = vi.fn().mockResolvedValue({
    customerPortalUrl: "https://sandbox.polar.sh/customer-portal/test-session",
  });
  const dependencies: PolarBillingDependencies = {
    now: () => new Date(NOW),
    createClient: () => ({
      createCheckout,
      createPortal,
    }),
  };
  return { dependencies, createCheckout, createPortal };
}

function request(
  path: string,
  body?: unknown,
  authenticated = true,
): Request {
  return new Request(`https://api.example${path}`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...(authenticated
        ? { cookie: `__Host-emulo_session=${SESSION_TOKEN}` }
        : {}),
      "cf-connecting-ip": "203.0.113.10",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

describe("authenticated Polar billing", () => {
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
    expect(await sha256(SESSION_TOKEN)).not.toBe(SESSION_HASH);
  });

  it("keeps checkout disabled without touching Polar", async () => {
    const { dependencies, createCheckout } = billingDependencies();
    const response = await handlePolarCheckout(
      request("/v1/billing/checkout", { plan: "monthly" }),
      { ...testEnv, PAID_CHECKOUT_ENABLED: "false" },
      dependencies,
    );
    expect(response.status).toBe(503);
    expect(createCheckout).not.toHaveBeenCalled();
  });

  it("requires a live authenticated browser session", async () => {
    const { dependencies, createCheckout } = billingDependencies();
    const response = await handlePolarCheckout(
      request("/v1/billing/checkout", { plan: "monthly" }, false),
      enabledEnv(),
      dependencies,
    );
    expect(response.status).toBe(401);
    expect(createCheckout).not.toHaveBeenCalled();
  });

  it("rejects an expired browser session", async () => {
    await testEnv.DB.prepare(
      "UPDATE browser_sessions SET expires_at = ?",
    )
      .bind(NOW.toISOString())
      .run();
    const { dependencies, createCheckout } = billingDependencies();
    const response = await handlePolarCheckout(
      request("/v1/billing/checkout", { plan: "monthly" }),
      enabledEnv(),
      dependencies,
    );
    expect(response.status).toBe(401);
    expect(createCheckout).not.toHaveBeenCalled();
  });

  it("creates a server-owned monthly checkout bound to the account", async () => {
    const { dependencies, createCheckout } = billingDependencies();
    const response = await handlePolarCheckout(
      request("/v1/billing/checkout", { plan: "monthly" }),
      enabledEnv(),
      dependencies,
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      url: "https://sandbox.polar.sh/checkout/test-checkout",
    });
    expect(createCheckout).toHaveBeenCalledWith({
      products: [testEnv.POLAR_MONTHLY_PRODUCT_ID],
      externalCustomerId: ACCOUNT_ID,
      customerIpAddress: "203.0.113.10",
      successUrl: "https://api.example/v1/billing/complete",
      returnUrl: "https://api.example/account",
    });
    expect(response.headers.get("cache-control")).toBe("no-store");
  });

  it("selects only the configured yearly product", async () => {
    const { dependencies, createCheckout } = billingDependencies();
    expect(
      (
        await handlePolarCheckout(
          request("/v1/billing/checkout", { plan: "yearly" }),
          enabledEnv(),
          dependencies,
        )
      ).status,
    ).toBe(200);
    expect(createCheckout.mock.calls[0][0].products).toEqual([
      testEnv.POLAR_YEARLY_PRODUCT_ID,
    ]);
  });

  it("rejects arbitrary plans and redirect fields", async () => {
    const { dependencies, createCheckout } = billingDependencies();
    for (const body of [
      { plan: "lifetime" },
      { plan: "monthly", successUrl: "https://attacker.example" },
      { productId: testEnv.POLAR_MONTHLY_PRODUCT_ID },
    ]) {
      expect(
        (
          await handlePolarCheckout(
            request("/v1/billing/checkout", body),
            enabledEnv(),
            dependencies,
          )
        ).status,
      ).toBe(400);
    }
    expect(createCheckout).not.toHaveBeenCalled();
  });

  it("creates a portal only for the authenticated external account", async () => {
    const { dependencies, createPortal } = billingDependencies();
    const response = await handlePolarPortal(
      request("/v1/billing/portal"),
      enabledEnv(),
      dependencies,
    );
    expect(response.status).toBe(200);
    expect(createPortal).toHaveBeenCalledWith({
      externalCustomerId: ACCOUNT_ID,
      returnUrl: "https://api.example/account",
    });
    expect(await response.json()).toEqual({
      url: "https://sandbox.polar.sh/customer-portal/test-session",
    });
  });

  it("returns a safe retryable provider failure", async () => {
    const { dependencies, createCheckout } = billingDependencies();
    createCheckout.mockRejectedValueOnce(new Error("provider secret detail"));
    const response = await handlePolarCheckout(
      request("/v1/billing/checkout", { plan: "monthly" }),
      enabledEnv(),
      dependencies,
    );
    expect(response.status).toBe(502);
    expect(await response.text()).not.toContain("provider secret detail");
  });
});
