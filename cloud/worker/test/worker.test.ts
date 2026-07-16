import { env } from "cloudflare:workers";
import { SELF } from "cloudflare:test";
import { Buffer } from "node:buffer";
import { beforeEach, describe, expect, it } from "vitest";
import { Webhook } from "standardwebhooks";

import type { Env } from "../src/contracts";
import { handlePolarWebhook } from "../src/polar";

const testEnv = env as unknown as Env;
const ACCOUNT_ID = "acct_0123456789abcdef0123456789abcdef";
const MONTHLY_PRODUCT_ID = "11111111-1111-4111-8111-111111111111";
const SECRET = testEnv.POLAR_WEBHOOK_SECRET!;

function subscriptionPayload(changes: Record<string, unknown> = {}) {
  const timestamp = "2026-07-16T12:00:00Z";
  const { data: dataChanges, ...eventChanges } = changes;
  const product = {
    id: MONTHLY_PRODUCT_ID,
    created_at: timestamp,
    modified_at: null,
    trial_interval: null,
    trial_interval_count: null,
    name: "Emulo Autopilot Founding Monthly",
    description: null,
    visibility: "public",
    recurring_interval: "month",
    recurring_interval_count: 1,
    is_recurring: true,
    is_archived: false,
    organization_id: "org_test",
    metadata: {},
    prices: [],
    benefits: [],
    medias: [],
    attached_custom_fields: [],
  };
  return {
    type: "subscription.active",
    timestamp,
    ...eventChanges,
    data: {
      created_at: timestamp,
      modified_at: timestamp,
      id: "sub_123",
      amount: 900,
      currency: "usd",
      recurring_interval: "month",
      recurring_interval_count: 1,
      status: "active",
      current_period_start: timestamp,
      current_period_end: "2026-08-16T12:00:00Z",
      trial_start: null,
      trial_end: null,
      cancel_at_period_end: false,
      canceled_at: null,
      started_at: timestamp,
      ends_at: null,
      ended_at: null,
      customer_id: "customer_123",
      product_id: MONTHLY_PRODUCT_ID,
      discount_id: null,
      checkout_id: "checkout_123",
      customer_cancellation_reason: null,
      customer_cancellation_comment: null,
      metadata: {},
      customer: {
        id: "customer_123",
        created_at: timestamp,
        modified_at: timestamp,
        metadata: {},
        external_id: ACCOUNT_ID,
        email_verified: true,
        type: "individual",
        name: null,
        billing_address: null,
        tax_id: null,
        organization_id: "org_test",
        deleted_at: null,
        avatar_url: "https://example.invalid/avatar.png",
      },
      product,
      discount: null,
      prices: [],
      meters: [],
      pending_update: null,
      ...(dataChanges as Record<string, unknown> | undefined),
    },
  };
}

function signedRequest(
  payload: unknown,
  eventId = "evt_001",
  secret = SECRET,
  at = new Date(),
) {
  const body = JSON.stringify(payload);
  const base64Secret = Buffer.from(secret, "utf-8").toString("base64");
  const signature = new Webhook(base64Secret).sign(eventId, at, body);
  return new Request("https://api.example/v1/billing/webhooks/polar", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "webhook-id": eventId,
      "webhook-timestamp": Math.floor(at.getTime() / 1000).toString(),
      "webhook-signature": signature,
    },
    body,
  });
}

async function fetch(request: Request) {
  return SELF.fetch(request);
}

describe("Emulo Autopilot Worker", () => {
  beforeEach(async () => {
    await testEnv.DB.batch([
      testEnv.DB.prepare("DELETE FROM entitlements"),
      testEnv.DB.prepare("DELETE FROM billing_events"),
      testEnv.DB.prepare("DELETE FROM billing_customers"),
      testEnv.DB.prepare("DELETE FROM accounts"),
      testEnv.DB.prepare(
        "INSERT INTO accounts (account_id, created_at) VALUES (?, ?)",
      ).bind(ACCOUNT_ID, "2026-07-16T11:00:00.000Z"),
    ]);
  });

  it("serves a bounded health response", async () => {
    const response = await fetch(new Request("https://api.example/healthz"));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      service: "emulo-autopilot-api",
      status: "ok",
    });
  });

  it("accepts a valid signed subscription event", async () => {
    const response = await fetch(signedRequest(subscriptionPayload()));
    expect(response.status).toBe(202);
    expect(await response.json()).toEqual({ status: "accepted" });
    const entitlement = await testEnv.DB.prepare(
      "SELECT state, provider_event_id FROM entitlements WHERE account_id = ?",
    )
      .bind(ACCOUNT_ID)
      .first<{ state: string; provider_event_id: string }>();
    expect(entitlement).toEqual({ state: "active", provider_event_id: "evt_001" });
  });

  it.each([
    ["subscription.canceled", "active", true, "active"],
    ["subscription.uncanceled", "active", false, "active"],
    ["subscription.past_due", "past_due", false, "past_due"],
    ["subscription.revoked", "canceled", false, "ended"],
  ])(
    "processes signed %s lifecycle events",
    async (type, status, cancelAtPeriodEnd, expected) => {
      const response = await fetch(
        signedRequest(
          subscriptionPayload({
            type,
            data: { status, cancel_at_period_end: cancelAtPeriodEnd },
          }),
          `evt_${type.replace("subscription.", "")}`,
        ),
      );
      expect(response.status).toBe(202);
      const entitlement = await testEnv.DB.prepare(
        "SELECT state FROM entitlements WHERE account_id = ?",
      )
        .bind(ACCOUNT_ID)
        .first<{ state: string }>();
      expect(entitlement?.state).toBe(expected);
    },
  );

  it("rejects an invalid signature without any database write", async () => {
    const request = signedRequest(subscriptionPayload(), "evt_bad", "wrong-secret");
    const response = await fetch(request);
    expect(response.status).toBe(403);
    const count = await testEnv.DB.prepare(
      "SELECT COUNT(*) AS count FROM billing_events",
    ).first<{ count: number }>();
    expect(count?.count).toBe(0);
  });

  it("keeps webhooks unavailable until the signing secret is installed", async () => {
    const response = await handlePolarWebhook(
      signedRequest(subscriptionPayload(), "evt_missing_secret"),
      { ...testEnv, POLAR_WEBHOOK_SECRET: undefined },
    );
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ status: "unavailable" });
    const count = await testEnv.DB.prepare(
      "SELECT COUNT(*) AS count FROM billing_events",
    ).first<{ count: number }>();
    expect(count?.count).toBe(0);
  });

  it("rejects a signed request outside the replay window", async () => {
    const old = new Date(Date.now() - 10 * 60 * 1000);
    const response = await fetch(
      signedRequest(subscriptionPayload(), "evt_old", SECRET, old),
    );
    expect(response.status).toBe(403);
  });

  it("rejects a signed malformed payload without a database write", async () => {
    const response = await fetch(
      signedRequest({ type: "subscription.active" }, "evt_malformed"),
    );
    expect(response.status).toBe(400);
    const count = await testEnv.DB.prepare(
      "SELECT COUNT(*) AS count FROM billing_events",
    ).first<{ count: number }>();
    expect(count?.count).toBe(0);
  });

  it("fails closed for an unknown product", async () => {
    const response = await fetch(
      signedRequest(
        subscriptionPayload({
          data: { product_id: "33333333-3333-4333-b333-333333333333" },
        }),
        "evt_unknown_product",
      ),
    );
    expect(response.status).toBe(202);
    expect(await testEnv.DB.prepare("SELECT * FROM entitlements").first()).toBeNull();
  });

  it("retries verified events when product configuration is invalid", async () => {
    const response = await handlePolarWebhook(
      signedRequest(subscriptionPayload(), "evt_bad_config"),
      {
        ...testEnv,
        POLAR_MONTHLY_PRODUCT_ID: "not-configured",
        POLAR_YEARLY_PRODUCT_ID: "not-configured",
      },
    );
    expect(response.status).toBe(503);
    expect(await testEnv.DB.prepare("SELECT * FROM billing_events").first()).toBeNull();
  });

  it("records safe metadata but no entitlement for an unknown account", async () => {
    const response = await fetch(
      signedRequest(
        subscriptionPayload({
          data: {
            customer: {
              ...subscriptionPayload().data.customer,
              external_id: "acct_ffffffffffffffffffffffffffffffff",
            },
          },
        }),
        "evt_unknown_account",
      ),
    );
    expect(response.status).toBe(202);
    const event = await testEnv.DB.prepare(
      "SELECT processing_result FROM billing_events WHERE event_id = ?",
    )
      .bind("evt_unknown_account")
      .first<{ processing_result: string }>();
    expect(event?.processing_result).toBe("unknown-account");
    expect(await testEnv.DB.prepare("SELECT * FROM entitlements").first()).toBeNull();
  });

  it("handles duplicate deliveries idempotently", async () => {
    expect((await fetch(signedRequest(subscriptionPayload()))).status).toBe(202);
    expect((await fetch(signedRequest(subscriptionPayload()))).status).toBe(202);
    const count = await testEnv.DB.prepare(
      "SELECT COUNT(*) AS count FROM billing_events",
    ).first<{ count: number }>();
    expect(count?.count).toBe(1);
  });

  it("rejects oversized bodies before verification", async () => {
    const response = await fetch(
      new Request("https://api.example/v1/billing/webhooks/polar", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "x".repeat(256 * 1024 + 1),
      }),
    );
    expect(response.status).toBe(413);
  });

  it("cancels a streaming body as soon as it exceeds the limit", async () => {
    let pullCount = 0;
    let canceled = false;
    const body = new ReadableStream<Uint8Array>({
      pull(controller) {
        pullCount += 1;
        if (pullCount <= 3) {
          controller.enqueue(new Uint8Array(128 * 1024));
        } else {
          controller.close();
        }
      },
      cancel() {
        canceled = true;
      },
    });
    const response = await handlePolarWebhook(
      new Request("https://api.example/v1/billing/webhooks/polar", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body,
      }),
      testEnv,
    );
    expect(response.status).toBe(413);
    expect(canceled).toBe(true);
    expect(pullCount).toBe(3);
  });

  it("returns retryable failure for an internal TypeError", async () => {
    const failingDatabase = {
      prepare() {
        throw new TypeError("injected database failure");
      },
    } as unknown as D1Database;
    const response = await handlePolarWebhook(
      signedRequest(subscriptionPayload(), "evt_db_failure"),
      { ...testEnv, DB: failingDatabase },
    );
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ status: "unavailable" });
  });

  it("returns exact route and method failures", async () => {
    expect(
      (await fetch(new Request("https://api.example/not-found"))).status,
    ).toBe(404);
    expect(
      (
        await fetch(
          new Request("https://api.example/v1/billing/webhooks/polar"),
        )
      ).status,
    ).toBe(405);
  });
});
