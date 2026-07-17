import type { Env } from "./contracts";
import { authenticateDevice } from "./device-auth";
import { authenticateBrowserSession } from "./session";
import {
  canReadContinuity,
  canWriteContinuity,
  currentHead,
  generation,
  insertAndAdvance,
  quotaAvailable,
  touchDevice,
  type StoredGeneration,
} from "./continuity-store";

const GENERATION_PATTERN = /^gen_[a-f0-9]{20}$/;
const DEVICE_PATTERN = /^dev_[a-f0-9]{32}$/;
const SHA256_PATTERN = /^[a-f0-9]{64}$/;
const B64URL_PATTERN = /^[A-Za-z0-9_-]+$/;
const CREATED_AT_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
const MAX_REQUEST_BYTES = 270 * 1024;
const MAX_CIPHERTEXT_BYTES = 192 * 1024 + 16;

function json(status: number, body: unknown): Response {
  return Response.json(body, {
    status,
    headers: {
      "cache-control": "no-store",
      "content-security-policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
      "referrer-policy": "no-referrer",
      "x-content-type-options": "nosniff",
    },
  });
}

function base64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

function decodeBase64Url(value: unknown, expected?: number): Uint8Array | null {
  if (
    typeof value !== "string" ||
    value.length === 0 ||
    !B64URL_PATTERN.test(value)
  ) return null;
  try {
    const binary = atob(value.replaceAll("-", "+").replaceAll("_", "/") + "=".repeat((4 - value.length % 4) % 4));
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
    if (base64Url(bytes) !== value || (expected !== undefined && bytes.length !== expected)) {
      return null;
    }
    return bytes;
  } catch {
    return null;
  }
}

async function sha256(bytes: Uint8Array): Promise<string> {
  const copy = new Uint8Array(bytes.byteLength);
  copy.set(bytes);
  const digest = await crypto.subtle.digest("SHA-256", copy.buffer);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

function randomHex(bytes: number): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(bytes)), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

type Envelope = {
  schema_version: "emulo.continuity-envelope/v1";
  generation_id: string;
  parent_generation_id: string | null;
  author_device_id: string;
  created_at: string;
  nonce: string;
  ciphertext: string;
  ciphertext_sha256: string;
};

async function validateEnvelope(value: unknown): Promise<{
  envelope: Envelope;
  ciphertextBytes: number;
} | null> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const body = value as Record<string, unknown>;
  const keys = [
    "author_device_id",
    "ciphertext",
    "ciphertext_sha256",
    "created_at",
    "generation_id",
    "nonce",
    "parent_generation_id",
    "schema_version",
  ];
  if (JSON.stringify(Object.keys(body).sort()) !== JSON.stringify(keys)) return null;
  if (
    body.schema_version !== "emulo.continuity-envelope/v1" ||
    typeof body.generation_id !== "string" ||
    !GENERATION_PATTERN.test(body.generation_id) ||
    (body.parent_generation_id !== null &&
      (typeof body.parent_generation_id !== "string" ||
        !GENERATION_PATTERN.test(body.parent_generation_id))) ||
    body.parent_generation_id === body.generation_id ||
    typeof body.author_device_id !== "string" ||
    !DEVICE_PATTERN.test(body.author_device_id) ||
    typeof body.created_at !== "string" ||
    !CREATED_AT_PATTERN.test(body.created_at) ||
    !Number.isFinite(Date.parse(body.created_at)) ||
    typeof body.ciphertext_sha256 !== "string" ||
    !SHA256_PATTERN.test(body.ciphertext_sha256)
  ) return null;
  const nonce = decodeBase64Url(body.nonce, 12);
  const ciphertext = decodeBase64Url(body.ciphertext);
  if (
    nonce === null ||
    ciphertext === null ||
    ciphertext.length < 16 ||
    ciphertext.length > MAX_CIPHERTEXT_BYTES ||
    (await sha256(ciphertext)) !== body.ciphertext_sha256
  ) return null;
  return { envelope: body as Envelope, ciphertextBytes: ciphertext.length };
}

function sameGeneration(stored: StoredGeneration, envelope: Envelope): boolean {
  return (
    stored.generation_id === envelope.generation_id &&
    stored.parent_generation_id === envelope.parent_generation_id &&
    stored.author_device_id === envelope.author_device_id &&
    stored.schema_version === envelope.schema_version &&
    stored.created_at === envelope.created_at &&
    stored.nonce === envelope.nonce &&
    stored.ciphertext === envelope.ciphertext &&
    stored.ciphertext_sha256 === envelope.ciphertext_sha256
  );
}

function responseEnvelope(stored: StoredGeneration): Envelope {
  return {
    schema_version: "emulo.continuity-envelope/v1",
    generation_id: stored.generation_id,
    parent_generation_id: stored.parent_generation_id,
    author_device_id: stored.author_device_id,
    created_at: stored.created_at,
    nonce: stored.nonce,
    ciphertext: stored.ciphertext,
    ciphertext_sha256: stored.ciphertext_sha256,
  };
}

async function authenticated(request: Request, env: Env) {
  const identity = await authenticateDevice(request, env.DB);
  if (identity === null) return null;
  return identity;
}

export async function handleContinuityUpload(
  request: Request,
  env: Env,
): Promise<Response> {
  const identity = await authenticated(request, env);
  if (identity === null) return json(401, { status: "unauthorized" });
  if (!(await canWriteContinuity(env.DB, identity.accountId))) {
    return json(403, { status: "pro-required" });
  }
  if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? "")) {
    return json(415, { status: "content-type-required" });
  }
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) {
    return json(413, { status: "payload-too-large" });
  }
  let parsed: unknown;
  try {
    const raw = await request.text();
    if (new TextEncoder().encode(raw).length > MAX_REQUEST_BYTES) {
      return json(413, { status: "payload-too-large" });
    }
    parsed = JSON.parse(raw);
  } catch {
    return json(400, { status: "invalid-envelope" });
  }
  const validated = await validateEnvelope(parsed);
  if (validated === null) return json(400, { status: "invalid-envelope" });
  const { envelope, ciphertextBytes } = validated;
  if (envelope.author_device_id !== identity.deviceId) {
    return json(403, { status: "author-mismatch" });
  }

  const existing = await generation(env.DB, identity.accountId, envelope.generation_id);
  if (existing !== null) {
    if (!sameGeneration(existing, envelope)) {
      return json(409, { status: "generation-id-reused" });
    }
    await touchDevice(env.DB, identity.deviceId, new Date().toISOString());
    return json(200, {
      status: "stored",
      generationId: existing.generation_id,
      head: await currentHead(env.DB, identity.accountId),
      headAdvanced: existing.head_advanced === 1,
      idempotent: true,
    });
  }
  if (!(await quotaAvailable(env.DB, identity.accountId, ciphertextBytes))) {
    return json(413, { status: "generation-quota" });
  }

  const receivedAt = new Date().toISOString();
  const stored = await insertAndAdvance(env.DB, identity.accountId, {
    generationId: envelope.generation_id,
    parentGenerationId: envelope.parent_generation_id,
    authorDeviceId: envelope.author_device_id,
    schemaVersion: envelope.schema_version,
    createdAt: envelope.created_at,
    receivedAt,
    nonce: envelope.nonce,
    ciphertext: envelope.ciphertext,
    ciphertextSha256: envelope.ciphertext_sha256,
    ciphertextBytes,
    uploadNonce: randomHex(32),
  });
  await touchDevice(env.DB, identity.deviceId, receivedAt);
  const head = await currentHead(env.DB, identity.accountId);
  if (stored.head_advanced !== 1) {
    return json(409, {
      status: "conflict",
      currentHead: head,
      storedGeneration: stored.generation_id,
      headAdvanced: false,
    });
  }
  return json(201, {
    status: "stored",
    generationId: stored.generation_id,
    head,
    headAdvanced: true,
    idempotent: false,
  });
}

export async function handleContinuityHead(
  request: Request,
  env: Env,
): Promise<Response> {
  const identity = await authenticated(request, env);
  if (identity === null) return json(401, { status: "unauthorized" });
  if (!(await canReadContinuity(env.DB, identity.accountId))) {
    return json(403, { status: "recovery-window-ended" });
  }
  const now = new Date().toISOString();
  await touchDevice(env.DB, identity.deviceId, now);
  return json(200, { generationId: await currentHead(env.DB, identity.accountId) });
}

export async function handleContinuityGeneration(
  request: Request,
  env: Env,
  generationId: string,
): Promise<Response> {
  if (!GENERATION_PATTERN.test(generationId)) return json(404, { status: "not-found" });
  const identity = await authenticated(request, env);
  if (identity === null) return json(401, { status: "unauthorized" });
  if (!(await canReadContinuity(env.DB, identity.accountId))) {
    return json(403, { status: "recovery-window-ended" });
  }
  const stored = await generation(env.DB, identity.accountId, generationId);
  if (stored === null) return json(404, { status: "not-found" });
  await touchDevice(env.DB, identity.deviceId, new Date().toISOString());
  return json(200, responseEnvelope(stored));
}

export async function handleContinuityExport(
  request: Request,
  env: Env,
): Promise<Response> {
  const identity = await authenticated(request, env);
  if (identity === null) return json(401, { status: "unauthorized" });
  if (!(await canReadContinuity(env.DB, identity.accountId))) {
    return json(403, { status: "recovery-window-ended" });
  }
  const rows = await env.DB.prepare(
    `SELECT generation_id, parent_generation_id, ciphertext_sha256,
            ciphertext_bytes, created_at
     FROM continuity_generations
     WHERE account_id = ?
     ORDER BY received_at, generation_id
     LIMIT 500`,
  )
    .bind(identity.accountId)
    .all<{
      generation_id: string;
      parent_generation_id: string | null;
      ciphertext_sha256: string;
      ciphertext_bytes: number;
      created_at: string;
    }>();
  const now = new Date().toISOString();
  await touchDevice(env.DB, identity.deviceId, now);
  return json(200, {
    schemaVersion: "emulo.continuity-export/v1",
    head: await currentHead(env.DB, identity.accountId),
    generations: rows.results.map((row) => ({
      generationId: row.generation_id,
      parentGenerationId: row.parent_generation_id,
      ciphertextSha256: row.ciphertext_sha256,
      ciphertextBytes: row.ciphertext_bytes,
      createdAt: row.created_at,
    })),
  });
}

export async function handleDeleteContinuity(
  request: Request,
  env: Env,
): Promise<Response> {
  const session = await authenticateBrowserSession(request, env.DB, new Date());
  if (session === null) return json(401, { status: "unauthorized" });
  if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? "")) {
    return json(415, { status: "content-type-required" });
  }
  let confirmation: unknown;
  try {
    const raw = await request.text();
    if (raw.length > 128) return json(413, { status: "payload-too-large" });
    confirmation = JSON.parse(raw);
  } catch {
    return json(400, { status: "confirmation-required" });
  }
  if (
    typeof confirmation !== "object" ||
    confirmation === null ||
    Array.isArray(confirmation) ||
    JSON.stringify(Object.keys(confirmation).sort()) !==
      JSON.stringify(["confirmation"]) ||
    (confirmation as { confirmation?: unknown }).confirmation !==
      "delete-cloud-continuity"
  ) {
    return json(400, { status: "confirmation-required" });
  }
  await env.DB.batch([
    env.DB.prepare("DELETE FROM continuity_heads WHERE account_id = ?").bind(
      session.accountId,
    ),
    env.DB.prepare("DELETE FROM continuity_generations WHERE account_id = ?").bind(
      session.accountId,
    ),
    env.DB.prepare("DELETE FROM continuity_pairing_grants WHERE account_id = ?").bind(
      session.accountId,
    ),
    env.DB.prepare("DELETE FROM continuity_devices WHERE account_id = ?").bind(
      session.accountId,
    ),
  ]);
  return new Response(null, {
    status: 204,
    headers: {
      "cache-control": "no-store",
      "content-security-policy": "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
      "referrer-policy": "no-referrer",
      "x-content-type-options": "nosniff",
    },
  });
}
