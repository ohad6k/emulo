import { env } from "cloudflare:workers";
import { SELF } from "cloudflare:test";
import { beforeEach, describe, expect, it } from "vitest";

import {
  createBrowserSession,
  resolveOrCreateGitHubIdentity,
} from "../src/auth-store";
import type { Env } from "../src/contracts";

const testEnv = env as unknown as Env;
const ACCOUNT_ID = "acct_0123456789abcdef0123456789abcdef";
const SESSION_TOKEN = "i".repeat(43);

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value),
  );
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

function authenticatedHeaders(): HeadersInit {
  return { cookie: `__Host-emulo_session=${SESSION_TOKEN}` };
}

async function insertActiveEntitlement(): Promise<void> {
  await testEnv.DB.batch([
    testEnv.DB.prepare(
      `INSERT INTO billing_customers
       (provider, provider_customer_id, account_id, external_customer_id, updated_at)
       VALUES ('polar', ?, ?, ?, ?)`,
    ).bind(
      "polar_customer_integration",
      ACCOUNT_ID,
      ACCOUNT_ID,
      "2026-07-16T20:02:07.698Z",
    ),
    testEnv.DB.prepare(
      `INSERT INTO entitlements
       (account_id, state, product_code, provider, provider_subscription_id,
        provider_customer_id, provider_product_id, provider_effective_at,
        provider_event_id, current_period_end, grace_ends_at, recovery_ends_at,
        updated_at)
       VALUES (?, 'active', 'founding-monthly', 'polar', ?, ?, ?, ?, ?, ?, NULL, NULL, ?)`,
    ).bind(
      ACCOUNT_ID,
      "polar_subscription_integration",
      "polar_customer_integration",
      testEnv.POLAR_MONTHLY_PRODUCT_ID,
      "2026-07-16T20:02:03.754Z",
      "polar_event_integration",
      "2026-08-16T20:02:03.754Z",
      "2026-07-16T20:02:07.698Z",
    ),
  ]);
}

describe("authenticated Worker integration", () => {
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
      expiresAt: "2099-07-16T13:00:00.000Z",
    });
  });

  it("serves a truthful signed-out account and pending-payment page", async () => {
    const account = await SELF.fetch("https://api.example/account");
    expect(account.status).toBe(200);
    expect(account.headers.get("cache-control")).toBe("no-store");
    const accountBody = await account.text();
    expect(accountBody).toContain("Sign in to Emulo");
    expect(accountBody).toContain("Continue with Google");
    expect(accountBody).toContain("Continue with GitHub");
    expect(accountBody).not.toContain("account is connected");
    expect(accountBody).toContain('class="brand-mark"');
    expect(accountBody).toContain('href="/emulo.png"');
    expect(accountBody).toContain('href="/account.css"');
    expect(accountBody).toContain('data-account-state="signed-out"');
    expect(accountBody).toContain('href="/privacy.html"');
    for (const rejected of [
      "Private account",
      "Signed out",
      "Production",
      "View open source",
      "opaque, hashed browser session",
    ]) {
      expect(accountBody).not.toContain(rejected);
    }
    expect(account.headers.get("content-security-policy")).toContain(
      "style-src 'self'",
    );
    for (const directive of [
      "default-src 'none'",
      "script-src 'self'",
      "img-src 'self'",
      "frame-ancestors 'none'",
      "base-uri 'none'",
      "form-action 'self'",
    ]) {
      expect(account.headers.get("content-security-policy")).toContain(directive);
    }

    const script = await SELF.fetch("https://api.example/account.js");
    expect(script.status).toBe(200);
    expect(script.headers.get("content-type")).toBe(
      "text/javascript; charset=utf-8",
    );
    expect(await script.text()).toContain('fetch("/v1/billing/checkout"');

    const styles = await SELF.fetch("https://api.example/account.css");
    expect(styles.status).toBe(200);
    expect(styles.headers.get("content-type")).toBe("text/css; charset=utf-8");
    expect(await styles.text()).toContain("prefers-reduced-motion");

    expect((await SELF.fetch("https://api.example/emulo.svg")).status).toBe(404);

    const complete = await SELF.fetch(
      "https://api.example/v1/billing/complete",
    );
    expect(complete.status).toBe(200);
    const body = await complete.text();
    expect(body).toContain("Sign in to continue");
    expect(body).not.toContain("Polar");
    expect(body).not.toContain("access is active");
    expect(body).toContain('data-payment-state="verifying"');
    expect(body).toContain('aria-live="polite"');
    expect(body).not.toContain("Payment successful");
  });

  it("returns no-store authenticated status without identifiers", async () => {
    const signedOut = await SELF.fetch("https://api.example/v1/account/status");
    expect(signedOut.status).toBe(401);
    expect(signedOut.headers.get("cache-control")).toBe("no-store");
    expect(await signedOut.json()).toEqual({ status: "unauthenticated" });

    const signedIn = await SELF.fetch("https://api.example/v1/account/status", {
      headers: authenticatedHeaders(),
    });
    expect(signedIn.status).toBe(200);
    expect(signedIn.headers.get("cache-control")).toBe("no-store");
    const body = await signedIn.text();
    expect(JSON.parse(body)).toMatchObject({
      authenticated: true,
      environment: "sandbox",
      checkoutEnabled: false,
      entitlement: { state: "none", productCode: null },
    });
    expect(body).not.toMatch(/accountId|account_id|provider|subscription|customer/i);
  });

  it("serves the optimized real Emulo icon with immutable headers", async () => {
    const mark = await SELF.fetch("https://api.example/emulo.png");
    expect(mark.status).toBe(200);
    expect(mark.headers.get("content-type")).toBe("image/png");
    expect(mark.headers.get("cache-control")).toBe(
      "public, max-age=86400, immutable",
    );
    expect((await mark.arrayBuffer()).byteLength).toBeGreaterThan(100_000);
    expect(
      (
        await SELF.fetch("https://api.example/emulo.png", { method: "POST" })
      ).status,
    ).toBe(405);
  });

  it("serves every customer policy before authentication", async () => {
    for (const path of ["/privacy.html", "/terms.html", "/refunds.html"]) {
      const response = await SELF.fetch(`https://api.example${path}`);
      expect(response.status).toBe(200);
      expect(response.headers.get("content-type")).toBe(
        "text/html; charset=utf-8",
      );
      expect(response.headers.get("content-security-policy")).toContain(
        "default-src 'self'",
      );
      expect(await response.text()).toContain("ohadkrispin@gmail.com");
      expect(
        (
          await SELF.fetch(`https://api.example${path}`, { method: "POST" })
        ).status,
      ).toBe(405);
    }
    const styles = await SELF.fetch("https://api.example/legal.css");
    expect(styles.status).toBe(200);
    expect(styles.headers.get("content-type")).toBe("text/css; charset=utf-8");
  });

  it("renders webhook-confirmed active account and receipt states", async () => {
    await insertActiveEntitlement();

    const account = await SELF.fetch("https://api.example/account", {
      headers: authenticatedHeaders(),
    });
    const accountBody = await account.text();
    expect(accountBody).toContain('data-account-state="active"');
    expect(accountBody).toContain("Emulo Pro is active");
    expect(accountBody).toContain("data-portal-form");
    expect(accountBody).not.toContain("data-checkout-form");

    const complete = await SELF.fetch(
      "https://api.example/v1/billing/complete",
      { headers: authenticatedHeaders() },
    );
    const completeBody = await complete.text();
    expect(completeBody).toContain('data-payment-state="active"');
    expect(completeBody).toContain("Emulo Pro activated");
    expect(completeBody).not.toContain("Confirming your subscription");
    expect(completeBody).not.toContain("webhook");
  });

  it("ships bounded checkout, portal, and status-polling interactions", async () => {
    const script = await (
      await SELF.fetch("https://api.example/account.js")
    ).text();
    expect(script).toContain('fetch("/v1/billing/checkout"');
    expect(script).toContain('fetch("/v1/billing/portal"');
    expect(script).toContain('fetch("/v1/account/status"');
    expect(script).toContain("MAX_STATUS_ATTEMPTS");
    expect(script).toContain('credentials: "same-origin"');
    expect(script).not.toContain("innerHTML");
    expect(script).not.toContain("signed confirmation");
    expect(script).not.toContain("verified Polar");
  });

  it("keeps checkout disabled through the public Worker route", async () => {
    const response = await SELF.fetch(
      "https://api.example/v1/billing/checkout",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ plan: "yearly" }),
      },
    );
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ status: "checkout-disabled" });
  });

  it("keeps exact methods on account and billing routes", async () => {
    const googleStart = await SELF.fetch(
      "https://api.example/v1/auth/google/start",
      { redirect: "manual" },
    );
    expect(googleStart.status).toBe(302);
    expect(googleStart.headers.get("location")).toContain(
      "https://accounts.google.com/o/oauth2/v2/auth",
    );
    expect(
      (
        await SELF.fetch("https://api.example/account", { method: "POST" })
      ).status,
    ).toBe(405);
    expect(
      (
        await SELF.fetch("https://api.example/account.js", { method: "POST" })
      ).status,
    ).toBe(405);
    expect(
      (
        await SELF.fetch("https://api.example/account.css", { method: "POST" })
      ).status,
    ).toBe(405);
    expect(
      (
        await SELF.fetch("https://api.example/v1/billing/complete", {
          method: "POST",
        })
      ).status,
    ).toBe(405);
    expect(
      (
        await SELF.fetch("https://api.example/v1/account/status", {
          method: "POST",
        })
      ).status,
    ).toBe(405);
    expect(
      (
        await SELF.fetch("https://api.example/v1/billing/portal", {
          method: "GET",
        })
      ).status,
    ).toBe(405);
    for (const path of [
      "/v1/auth/google/start",
      "/v1/auth/google/callback",
    ]) {
      expect(
        (await SELF.fetch(`https://api.example${path}`, { method: "POST" }))
          .status,
      ).toBe(405);
    }
  });
});
