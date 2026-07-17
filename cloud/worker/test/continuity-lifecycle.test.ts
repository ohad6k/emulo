import { env } from "cloudflare:workers";
import { SELF } from "cloudflare:test";
import { beforeEach, describe, expect, it } from "vitest";

import {
  createBrowserSession,
  resolveOrCreateGitHubIdentity,
} from "../src/auth-store";
import type { Env } from "../src/contracts";

const testEnv = env as unknown as Env;
const ACCOUNT_ID = "acct_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const OTHER_ACCOUNT_ID = "acct_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
const DEVICE_ID = "dev_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const TOKEN = "c".repeat(43);
const SESSION = "d".repeat(43);
const OTHER_SESSION = "e".repeat(43);

async function sha256(value: string | Uint8Array): Promise<string> {
  const source = typeof value === "string" ? new TextEncoder().encode(value) : value;
  const copy = new Uint8Array(source.byteLength);
  copy.set(source);
  const digest = await crypto.subtle.digest("SHA-256", copy.buffer);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

function b64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

async function createAccount(
  accountId: string,
  providerId: string,
  sessionToken: string,
) {
  await resolveOrCreateGitHubIdentity(testEnv.DB, {
    providerUserId: providerId,
    proposedAccountId: accountId,
    createdAt: "2026-07-17T12:00:00.000Z",
  });
  await createBrowserSession(testEnv.DB, {
    sessionHash: await sha256(sessionToken),
    accountId,
    createdAt: "2026-07-17T12:00:00.000Z",
    expiresAt: "2099-07-17T12:00:00.000Z",
  });
}

async function activate(accountId: string) {
  const customer = `customer_${accountId}`;
  await testEnv.DB.batch([
    testEnv.DB.prepare(
      `INSERT INTO billing_customers
       (provider, provider_customer_id, account_id, external_customer_id, updated_at)
       VALUES ('polar', ?, ?, ?, ?)`,
    ).bind(customer, accountId, accountId, "2026-07-17T12:01:00.000Z"),
    testEnv.DB.prepare(
      `INSERT INTO entitlements
       (account_id, state, product_code, provider, provider_subscription_id,
        provider_customer_id, provider_product_id, provider_effective_at,
        provider_event_id, current_period_end, grace_ends_at, recovery_ends_at,
        updated_at)
       VALUES (?, 'active', 'founding-monthly', 'polar', ?, ?, ?, ?, ?, ?, NULL, NULL, ?)`,
    ).bind(
      accountId,
      `subscription_${accountId}`,
      customer,
      testEnv.POLAR_MONTHLY_PRODUCT_ID,
      "2026-07-17T12:01:00.000Z",
      `event_${accountId}`,
      "2026-08-17T12:01:00.000Z",
      "2026-07-17T12:01:00.000Z",
    ),
  ]);
}

async function createDevice() {
  await testEnv.DB.prepare(
    `INSERT INTO continuity_devices
     (device_id, account_id, label, key_agreement_public_key,
      wrapped_master_key, token_hash, client_version, created_at,
      last_seen_at, revoked_at)
     VALUES (?, ?, 'Lifecycle device', ?, ?, ?, '0.3.8', ?, ?, NULL)`,
  )
    .bind(
      DEVICE_ID,
      ACCOUNT_ID,
      "A".repeat(43),
      JSON.stringify({ encrypted: "B".repeat(128) }),
      await sha256(TOKEN),
      "2026-07-17T12:02:00.000Z",
      "2026-07-17T12:02:00.000Z",
    )
    .run();
}

async function upload() {
  const ciphertext = new TextEncoder().encode("encrypted-only-lifecycle-marker");
  return SELF.fetch("https://api.example/v1/continuity/generations", {
    method: "POST",
    headers: {
      authorization: `Bearer ${TOKEN}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      schema_version: "emulo.continuity-envelope/v1",
      generation_id: "gen_aaaaaaaaaaaaaaaaaaaa",
      parent_generation_id: null,
      author_device_id: DEVICE_ID,
      created_at: "2026-07-17T12:03:00Z",
      nonce: b64(new Uint8Array(12)),
      ciphertext: b64(ciphertext),
      ciphertext_sha256: await sha256(ciphertext),
    }),
  });
}

describe("continuity export and deletion lifecycle", () => {
  beforeEach(async () => {
    await testEnv.DB.batch([
      testEnv.DB.prepare("DELETE FROM continuity_heads"),
      testEnv.DB.prepare("DELETE FROM continuity_generations"),
      testEnv.DB.prepare("DELETE FROM continuity_pairing_grants"),
      testEnv.DB.prepare("DELETE FROM continuity_devices"),
      testEnv.DB.prepare("DELETE FROM browser_sessions"),
      testEnv.DB.prepare("DELETE FROM oauth_identities"),
      testEnv.DB.prepare("DELETE FROM oauth_flows"),
      testEnv.DB.prepare("DELETE FROM entitlements"),
      testEnv.DB.prepare("DELETE FROM billing_events"),
      testEnv.DB.prepare("DELETE FROM billing_customers"),
      testEnv.DB.prepare("DELETE FROM accounts"),
    ]);
    await createAccount(ACCOUNT_ID, "11111111", SESSION);
    await activate(ACCOUNT_ID);
    await createDevice();
    expect((await upload()).status).toBe(201);
  });

  it("returns a bounded ciphertext export manifest without secrets or payloads", async () => {
    const response = await SELF.fetch("https://api.example/v1/continuity/export", {
      headers: { authorization: `Bearer ${TOKEN}` },
    });
    expect(response.status).toBe(200);
    const text = await response.text();
    expect(JSON.parse(text)).toEqual({
      schemaVersion: "emulo.continuity-export/v1",
      head: "gen_aaaaaaaaaaaaaaaaaaaa",
      generations: [
        {
          generationId: "gen_aaaaaaaaaaaaaaaaaaaa",
          parentGenerationId: null,
          ciphertextSha256: expect.stringMatching(/^[a-f0-9]{64}$/),
          ciphertextBytes: 31,
          createdAt: "2026-07-17T12:03:00Z",
        },
      ],
    });
    expect(text).not.toMatch(/ciphertext"|nonce|token|wrapped|upload/i);
  });

  it("deletes only the signed-in account's cloud continuity data", async () => {
    await createAccount(OTHER_ACCOUNT_ID, "22222222", OTHER_SESSION);
    expect(
      (
        await SELF.fetch("https://api.example/v1/continuity", {
          method: "DELETE",
          headers: {
            cookie: `__Host-emulo_session=${OTHER_SESSION}`,
            "content-type": "application/json",
          },
          body: JSON.stringify({ confirmation: "delete-cloud-continuity" }),
        })
      ).status,
    ).toBe(204);
    expect(
      await testEnv.DB.prepare(
        "SELECT generation_id FROM continuity_heads WHERE account_id = ?",
      )
        .bind(ACCOUNT_ID)
        .first(),
    ).not.toBeNull();

    expect(
      (
        await SELF.fetch("https://api.example/v1/continuity", {
          method: "DELETE",
          headers: {
            cookie: `__Host-emulo_session=${SESSION}`,
            "content-type": "application/json",
          },
          body: JSON.stringify({ confirmation: "delete-cloud-continuity" }),
        })
      ).status,
    ).toBe(204);
    expect(
      await testEnv.DB.prepare(
        "SELECT generation_id FROM continuity_generations WHERE account_id = ?",
      )
        .bind(ACCOUNT_ID)
        .first(),
    ).toBeNull();
    expect(
      await testEnv.DB.prepare(
        "SELECT device_id FROM continuity_devices WHERE account_id = ?",
      )
        .bind(ACCOUNT_ID)
        .first(),
    ).toBeNull();
    expect(
      await testEnv.DB.prepare("SELECT account_id FROM accounts WHERE account_id = ?")
        .bind(ACCOUNT_ID)
        .first(),
    ).not.toBeNull();
    expect(
      (
        await SELF.fetch("https://api.example/v1/continuity/head", {
          headers: { authorization: `Bearer ${TOKEN}` },
        })
      ).status,
    ).toBe(401);
    expect(
      (
        await SELF.fetch("https://api.example/v1/continuity", {
          method: "DELETE",
          headers: { cookie: `__Host-emulo_session=${SESSION}` },
        })
      ).status,
    ).toBe(415);
    expect(
      (
        await SELF.fetch("https://api.example/v1/continuity", {
          method: "DELETE",
          headers: {
            cookie: `__Host-emulo_session=${SESSION}`,
            "content-type": "application/json",
          },
          body: JSON.stringify({ confirmation: "no" }),
        })
      ).status,
    ).toBe(400);
  });

  it("requires browser authentication for deletion and exact methods", async () => {
    expect(
      (
        await SELF.fetch("https://api.example/v1/continuity", {
          method: "DELETE",
        })
      ).status,
    ).toBe(401);
    expect(
      (
        await SELF.fetch("https://api.example/v1/continuity/export", {
          method: "POST",
          headers: { authorization: `Bearer ${TOKEN}` },
        })
      ).status,
    ).toBe(405);
    expect(
      (
        await SELF.fetch("https://api.example/v1/continuity", {
          headers: { cookie: `__Host-emulo_session=${SESSION}` },
        })
      ).status,
    ).toBe(405);
  });
});
