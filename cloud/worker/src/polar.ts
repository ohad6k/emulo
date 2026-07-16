import {
  validateEvent,
  WebhookVerificationError,
} from "@polar-sh/sdk/webhooks";
import { SDKValidationError } from "@polar-sh/sdk/models/errors/sdkvalidationerror";

import {
  BillingConfigurationError,
  BillingEventError,
  normalizePolarSubscriptionEvent,
} from "./billing";
import type { Env } from "./contracts";
import { recordBillingEvent } from "./repository";

const MAX_WEBHOOK_BYTES = 256 * 1024;

class WebhookRequestError extends Error {
  constructor(readonly status: number) {
    super("invalid webhook request");
    this.name = "WebhookRequestError";
  }
}

function json(status: number, body: Record<string, string>): Response {
  return Response.json(body, {
    status,
    headers: {
      "cache-control": "no-store",
    },
  });
}

function webhookHeaders(request: Request): Record<string, string> {
  return Object.fromEntries(request.headers.entries());
}

async function readBoundedBody(request: Request): Promise<{
  body: string;
  bytes: Uint8Array<ArrayBuffer>;
}> {
  const contentLength = request.headers.get("content-length");
  if (contentLength !== null) {
    const size = Number(contentLength);
    if (!Number.isSafeInteger(size) || size < 0) {
      throw new WebhookRequestError(400);
    }
    if (size > MAX_WEBHOOK_BYTES) {
      throw new WebhookRequestError(413);
    }
  }
  if (!request.headers.get("content-type")?.toLowerCase().startsWith("application/json")) {
    throw new WebhookRequestError(415);
  }
  const chunks: Uint8Array<ArrayBuffer>[] = [];
  let total = 0;
  const reader = request.body?.getReader();
  if (reader !== undefined) {
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        total += value.byteLength;
        if (total > MAX_WEBHOOK_BYTES) {
          await reader.cancel();
          throw new WebhookRequestError(413);
        }
        chunks.push(new Uint8Array(value));
      }
    } finally {
      reader.releaseLock();
    }
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    return {
      body: new TextDecoder("utf-8", { fatal: true }).decode(bytes),
      bytes,
    };
  } catch {
    throw new WebhookRequestError(400);
  }
}

async function sha256(bytes: Uint8Array<ArrayBuffer>): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (value) =>
    value.toString(16).padStart(2, "0"),
  ).join("");
}

export async function handlePolarWebhook(
  request: Request,
  env: Env,
): Promise<Response> {
  if (
    typeof env.POLAR_WEBHOOK_SECRET !== "string" ||
    env.POLAR_WEBHOOK_SECRET.length < 8
  ) {
    return json(503, { status: "unavailable" });
  }
  try {
    const { body, bytes } = await readBoundedBody(request);
    validateEvent(body, webhookHeaders(request), env.POLAR_WEBHOOK_SECRET);

    const raw: unknown = JSON.parse(body);
    const entitlement = normalizePolarSubscriptionEvent(raw, {
      monthlyProductId: env.POLAR_MONTHLY_PRODUCT_ID,
      yearlyProductId: env.POLAR_YEARLY_PRODUCT_ID,
    });
    if (entitlement === null) {
      return json(202, { status: "accepted" });
    }

    const eventId = request.headers.get("webhook-id");
    const eventType =
      typeof raw === "object" && raw !== null && "type" in raw
        ? (raw as { type?: unknown }).type
        : null;
    if (typeof eventId !== "string" || typeof eventType !== "string") {
      throw new WebhookRequestError(400);
    }

    await recordBillingEvent(
      env.DB,
      {
        provider: "polar",
        eventId,
        eventType,
        payloadSha256: await sha256(bytes),
        effectiveAt: entitlement.effectiveAt,
        receivedAt: new Date().toISOString(),
      },
      entitlement,
    );
    return json(202, { status: "accepted" });
  } catch (error) {
    if (error instanceof WebhookRequestError) {
      return json(error.status, { status: "rejected" });
    }
    if (error instanceof WebhookVerificationError) {
      return json(403, { status: "rejected" });
    }
    if (error instanceof BillingConfigurationError) {
      return json(503, { status: "unavailable" });
    }
    if (error instanceof BillingEventError) {
      return json(202, { status: "accepted" });
    }
    if (error instanceof SDKValidationError) {
      return json(400, { status: "rejected" });
    }
    if (error instanceof SyntaxError) {
      return json(400, { status: "rejected" });
    }
    return json(503, { status: "unavailable" });
  }
}
