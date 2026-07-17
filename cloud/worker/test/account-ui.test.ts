import { describe, expect, it } from "vitest";

import type { AccountStatus } from "../src/account-status";
import {
  accountScript,
  renderAccountPage,
  renderPaymentPage,
} from "../src/account-ui";

function status(
  state: "none" | "trialing" | "active" | "past_due" | "grace" | "ended" | "refunded",
  changes: Partial<Extract<AccountStatus, { authenticated: true }>> = {},
): Extract<AccountStatus, { authenticated: true }> {
  return {
    authenticated: true,
    environment: "sandbox",
    checkoutEnabled: false,
    entitlement: {
      state,
      productCode: state === "none" ? null : "founding-monthly",
      currentPeriodEnd: null,
      graceEndsAt: null,
      recoveryEndsAt: null,
    },
    ...changes,
  };
}

async function body(response: Response): Promise<string> {
  expect(response.status).toBe(200);
  expect(response.headers.get("cache-control")).toBe("no-store");
  return response.text();
}

describe("Emulo account UI", () => {
  it("renders the professional two-provider sign-in surface", async () => {
    const html = await body(renderAccountPage({
      authenticated: false,
      environment: "sandbox",
      checkoutEnabled: false,
    }));
    expect(html).toContain('data-account-state="signed-out"');
    expect(html).toContain("Sign in to Emulo");
    expect(html).toContain("Continue with Google");
    expect(html).toContain("Continue with GitHub");
    expect(html).toContain('href="/privacy.html"');
    expect(html).toContain('href="/terms.html"');
    expect(html).toContain('href="/refunds.html"');
    expect(html).not.toContain("account is connected");
    for (const rejected of [
      "Private account",
      "Signed out",
      "Production",
      "View open source",
      "opaque, hashed browser session",
      "Connect your Emulo account",
    ]) {
      expect(html).not.toContain(rejected);
    }
  });

  it("hides Google and the provider divider until Google OAuth is configured", async () => {
    const signedOut = {
      authenticated: false,
      environment: "production",
      checkoutEnabled: false,
    } as const;
    const accountHtml = await body(renderAccountPage(signedOut, { googleEnabled: false }));
    const paymentHtml = await body(renderPaymentPage(signedOut, { googleEnabled: false }));

    for (const html of [accountHtml, paymentHtml]) {
      expect(html).toContain("Continue with GitHub");
      expect(html).not.toContain("Continue with Google");
      expect(html).not.toContain('class="provider-divider"');
    }
  });

  it("keeps founding checkout absent while the gate is disabled", async () => {
    const html = await body(renderAccountPage(status("none")));
    expect(html).toContain('data-account-state="none"');
    expect(html).toContain("Your Emulo account is ready.");
    expect(html).toContain("Emulo Pro is not available for purchase yet.");
    expect(html).toContain("encrypted continuity");
    expect(html).toContain("up to 5 devices");
    expect(html).toContain("30-day export window");
    expect(html).not.toContain("data-checkout-form");
  });

  it("offers only fixed monthly and yearly plans when checkout is enabled", async () => {
    const html = await body(renderAccountPage(status("none", {
      checkoutEnabled: true,
    })));
    expect(html).toContain('data-plan="monthly"');
    expect(html).toContain('data-plan="yearly"');
    expect(html).not.toContain("lifetime");
  });

  it("makes the portal primary for active customers without duplicate checkout", async () => {
    const html = await body(renderAccountPage(status("active")));
    expect(html).toContain("Emulo Pro is active");
    expect(html).toContain("Monthly");
    expect(html).toContain("Manage subscription");
    expect(html).toContain("End-to-end encrypted");
    expect(html).toContain("5 paired devices");
    expect(html).toContain("data-portal-form");
    expect(html).not.toContain("data-checkout-form");
    expect(html).not.toContain("Polar");
    expect(html).not.toContain("webhook");
  });

  it("offers continuity controls only to active Pro accounts", async () => {
    const active = await body(renderAccountPage(status("active")));
    const inactive = await body(renderAccountPage(status("none")));

    expect(active).toContain('data-continuity-root');
    expect(active).toContain('data-create-pairing-code');
    expect(active).toContain('data-pairing-result');
    expect(active).toContain('data-device-list');
    expect(active).toContain('href="/v1/continuity/export"');
    expect(active).toContain("Download encrypted export manifest");
    expect(active).toContain('data-continuity-delete-form');
    expect(active).toContain("delete-cloud-continuity");
    expect(active).not.toContain('value="delete-cloud-continuity"');
    expect(active).toContain("Local files stay on your devices");
    expect(inactive).not.toContain('data-continuity-root');
    expect(inactive).not.toContain('data-create-pairing-code');
    expect(inactive).not.toContain('data-continuity-delete-form');
  });

  it("uses same-origin safe device controls without embedding private material", async () => {
    const script = await accountScript().text();

    expect(script).toContain('fetch("/v1/devices/pair/start"');
    expect(script).toContain('fetch("/v1/devices"');
    expect(script).toContain('fetch("/v1/continuity"');
    expect(script).toContain("textContent");
    expect(script).not.toContain("innerHTML");
    expect(script).not.toContain("deviceToken");
    expect(script).not.toContain("wrappedMasterKey");
    expect(script).not.toContain("Authorization");
  });

  it.each(["past_due", "grace"] as const)(
    "shows billing attention without weakening local Emulo for %s",
    async (state) => {
      const html = await body(renderAccountPage(status(state)));
      expect(html).toContain("Billing needs attention");
      expect(html).toContain("local Emulo stays yours");
      expect(html).toContain("data-portal-form");
      expect(html).not.toContain("Polar");
    },
  );

  it.each(["ended", "refunded"] as const)(
    "explains cloud continuity ending for %s",
    async (state) => {
      const html = await body(renderAccountPage(status(state)));
      expect(html).toContain("Cloud continuity is paused");
      expect(html).toContain("local profiles and workflows remain yours");
      expect(html).not.toContain("Polar");
    },
  );

  it("keeps the receipt pending until an entitlement exists", async () => {
    const html = await body(renderPaymentPage(status("none")));
    expect(html).toContain('data-payment-state="verifying"');
    expect(html).toContain("Confirming your subscription");
    expect(html).not.toContain("Polar");
    expect(html).not.toContain("Payment successful");
  });

  it("renders webhook-confirmed activation immediately", async () => {
    const html = await body(renderPaymentPage(status("active")));
    expect(html).toContain('data-payment-state="active"');
    expect(html).toContain("Emulo Pro activated");
    expect(html).not.toContain("Confirming your subscription");
    expect(html).not.toContain("webhook");
  });
});
