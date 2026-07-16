import { describe, expect, it } from "vitest";

import {
  BillingConfigurationError,
  BillingEventError,
  normalizePolarSubscriptionEvent,
} from "../src/billing";

const MONTHLY_PRODUCT_ID = "11111111-1111-4111-8111-111111111111";
const YEARLY_PRODUCT_ID = "22222222-2222-4222-a222-222222222222";
const products = {
  monthlyProductId: MONTHLY_PRODUCT_ID,
  yearlyProductId: YEARLY_PRODUCT_ID,
};

function event(overrides: Record<string, unknown> = {}) {
  const data = {
    id: "sub_123",
    customer_id: "customer_123",
    product_id: MONTHLY_PRODUCT_ID,
    status: "active",
    modified_at: "2026-07-16T12:00:00Z",
    current_period_end: "2026-08-16T12:00:00Z",
    cancel_at_period_end: false,
    customer: { external_id: "acct_0123456789abcdef0123456789abcdef" },
    ...((overrides.data as Record<string, unknown>) ?? {}),
  };
  return {
    type: "subscription.updated",
    timestamp: "2026-07-16T11:59:00Z",
    ...overrides,
    data,
  };
}

describe("normalizePolarSubscriptionEvent", () => {
  it.each([
    ["subscription.active", "active", "active"],
    ["subscription.updated", "trialing", "trialing"],
    ["subscription.past_due", "past_due", "past_due"],
    ["subscription.uncanceled", "active", "active"],
    ["subscription.revoked", "canceled", "ended"],
  ])("maps %s / %s to %s", (type, status, expected) => {
    const normalized = normalizePolarSubscriptionEvent(
      event({ type, data: { status } }),
      products,
    );
    expect(normalized?.state).toBe(expected);
  });

  it("keeps a scheduled cancellation active until revocation", () => {
    const normalized = normalizePolarSubscriptionEvent(
      event({
        type: "subscription.canceled",
        data: { status: "active", cancel_at_period_end: true },
      }),
      products,
    );
    expect(normalized?.state).toBe("active");
    expect(normalized?.currentPeriodEnd).toBe("2026-08-16T12:00:00.000Z");
  });

  it("adds bounded grace and recovery timestamps", () => {
    const pastDue = normalizePolarSubscriptionEvent(
      event({ type: "subscription.past_due", data: { status: "past_due" } }),
      products,
    );
    expect(pastDue?.graceEndsAt).toBe("2026-07-23T12:00:00.000Z");
    expect(pastDue?.recoveryEndsAt).toBeNull();

    const ended = normalizePolarSubscriptionEvent(
      event({ type: "subscription.revoked", data: { status: "canceled" } }),
      products,
    );
    expect(ended?.graceEndsAt).toBeNull();
    expect(ended?.recoveryEndsAt).toBe("2026-08-15T12:00:00.000Z");
  });

  it("uses modified_at as the ordering timestamp", () => {
    const normalized = normalizePolarSubscriptionEvent(event(), products);
    expect(normalized?.effectiveAt).toBe("2026-07-16T12:00:00.000Z");
  });

  it("distinguishes the founding monthly and yearly products", () => {
    expect(normalizePolarSubscriptionEvent(event(), products)?.productCode).toBe(
      "founding-monthly",
    );
    expect(
      normalizePolarSubscriptionEvent(
        event({ data: { product_id: YEARLY_PRODUCT_ID } }),
        products,
      )?.productCode,
    ).toBe("founding-yearly");
  });

  it.each([
    ["unknown product", event({ data: { product_id: "prod_unknown" } })],
    ["unknown state", event({ data: { status: "paused" } })],
    ["missing external account", event({ data: { customer: {} } })],
    ["invalid effective timestamp", event({ data: { modified_at: "tomorrow" } })],
  ])("fails closed for %s", (_label, value) => {
    expect(() => normalizePolarSubscriptionEvent(value, products)).toThrow(
      BillingEventError,
    );
  });

  it.each([
    ["placeholder", { monthlyProductId: "not-configured", yearlyProductId: YEARLY_PRODUCT_ID }],
    ["duplicate", { monthlyProductId: MONTHLY_PRODUCT_ID, yearlyProductId: MONTHLY_PRODUCT_ID }],
    ["malformed", { monthlyProductId: "bad id", yearlyProductId: YEARLY_PRODUCT_ID }],
    ["uppercase", { monthlyProductId: "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA", yearlyProductId: YEARLY_PRODUCT_ID }],
    [
      "case-equivalent duplicate",
      {
        monthlyProductId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        yearlyProductId: "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
      },
    ],
  ])("rejects %s product configuration", (_label, configuration) => {
    expect(() => normalizePolarSubscriptionEvent(event(), configuration)).toThrow(
      BillingConfigurationError,
    );
  });

  it("ignores verified event types that cannot change entitlement", () => {
    expect(
      normalizePolarSubscriptionEvent(
        event({ type: "checkout.updated" }),
        products,
      ),
    ).toBeNull();
  });
});
