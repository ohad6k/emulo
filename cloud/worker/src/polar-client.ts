import { Polar } from "@polar-sh/sdk";

import type { Env } from "./contracts";
import { authenticateBrowserSession } from "./session";

interface CheckoutInput {
  products: string[];
  externalCustomerId: string;
  customerIpAddress?: string;
  successUrl: string;
  returnUrl: string;
}

interface PortalInput {
  externalCustomerId: string;
  returnUrl: string;
}

interface PolarBillingClient {
  createCheckout(input: CheckoutInput): Promise<{ url: string }>;
  createPortal(input: PortalInput): Promise<{ customerPortalUrl: string }>;
}

export interface PolarBillingDependencies {
  now: () => Date;
  createClient: (env: Env) => PolarBillingClient;
}

const defaultDependencies: PolarBillingDependencies = {
  now: () => new Date(),
  createClient: (env) => {
    const client = new Polar({
      accessToken: env.POLAR_ACCESS_TOKEN,
      server: "sandbox",
    });
    return {
      createCheckout: (input) => client.checkouts.create(input),
      createPortal: (input) => client.customerSessions.create(input),
    };
  },
};

const PRODUCT_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

function json(status: number, body: Record<string, string>): Response {
  return Response.json(body, {
    status,
    headers: { "cache-control": "no-store" },
  });
}

function publicBase(env: Env): URL | null {
  try {
    const url = new URL(env.PUBLIC_BASE_URL);
    if (
      url.protocol !== "https:" ||
      url.pathname !== "/" ||
      url.search ||
      url.hash ||
      url.username ||
      url.password
    ) {
      return null;
    }
    return url;
  } catch {
    return null;
  }
}

function billingConfigured(env: Env): boolean {
  return (
    env.POLAR_SERVER === "sandbox" &&
    typeof env.POLAR_ACCESS_TOKEN === "string" &&
    env.POLAR_ACCESS_TOKEN.length >= 8 &&
    PRODUCT_ID_PATTERN.test(env.POLAR_MONTHLY_PRODUCT_ID) &&
    PRODUCT_ID_PATTERN.test(env.POLAR_YEARLY_PRODUCT_ID) &&
    env.POLAR_MONTHLY_PRODUCT_ID !== env.POLAR_YEARLY_PRODUCT_ID &&
    publicBase(env) !== null
  );
}

async function readPlan(request: Request): Promise<"monthly" | "yearly" | null> {
  if (!request.headers.get("content-type")?.toLowerCase().startsWith("application/json")) {
    return null;
  }
  const declared = request.headers.get("content-length");
  if (declared !== null && Number(declared) > 1024) {
    return null;
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
        if (total > 1024) {
          await reader.cancel();
          return null;
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
    const parsed: unknown = JSON.parse(
      new TextDecoder("utf-8", { fatal: true }).decode(bytes),
    );
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      return null;
    }
    const record = parsed as Record<string, unknown>;
    if (
      Object.keys(record).length !== 1 ||
      (record.plan !== "monthly" && record.plan !== "yearly")
    ) {
      return null;
    }
    return record.plan;
  } catch {
    return null;
  }
}

function hostedUrl(value: string, env: Env): string | null {
  try {
    const url = new URL(value);
    if (
      url.protocol !== "https:" ||
      url.origin !==
        (env.POLAR_SERVER === "sandbox"
          ? "https://sandbox.polar.sh"
          : "https://polar.sh") ||
      url.username ||
      url.password
    ) {
      return null;
    }
    return url.toString();
  } catch {
    return null;
  }
}

export async function handlePolarCheckout(
  request: Request,
  env: Env,
  dependencies: PolarBillingDependencies = defaultDependencies,
): Promise<Response> {
  if (env.PAID_CHECKOUT_ENABLED !== "true") {
    return json(503, { status: "checkout-disabled" });
  }
  if (!billingConfigured(env)) {
    return json(503, { status: "unavailable" });
  }
  const session = await authenticateBrowserSession(
    request,
    env.DB,
    dependencies.now(),
  );
  if (session === null) {
    return json(401, { status: "unauthorized" });
  }
  const plan = await readPlan(request);
  if (plan === null) {
    return json(400, { status: "invalid-request" });
  }
  const base = publicBase(env)!;
  try {
    const checkout = await dependencies.createClient(env).createCheckout({
      products: [
        plan === "monthly"
          ? env.POLAR_MONTHLY_PRODUCT_ID
          : env.POLAR_YEARLY_PRODUCT_ID,
      ],
      externalCustomerId: session.accountId,
      customerIpAddress: request.headers.get("cf-connecting-ip") ?? undefined,
      successUrl: new URL("/v1/billing/complete", base).toString(),
      returnUrl: new URL("/account", base).toString(),
    });
    const url = hostedUrl(checkout.url, env);
    return url === null
      ? json(502, { status: "provider-unavailable" })
      : json(200, { url });
  } catch {
    return json(502, { status: "provider-unavailable" });
  }
}

export async function handlePolarPortal(
  request: Request,
  env: Env,
  dependencies: PolarBillingDependencies = defaultDependencies,
): Promise<Response> {
  if (!billingConfigured(env)) {
    return json(503, { status: "unavailable" });
  }
  const session = await authenticateBrowserSession(
    request,
    env.DB,
    dependencies.now(),
  );
  if (session === null) {
    return json(401, { status: "unauthorized" });
  }
  try {
    const portal = await dependencies.createClient(env).createPortal({
      externalCustomerId: session.accountId,
      returnUrl: new URL("/account", publicBase(env)!).toString(),
    });
    const url = hostedUrl(portal.customerPortalUrl, env);
    return url === null
      ? json(502, { status: "provider-unavailable" })
      : json(200, { url });
  } catch {
    return json(502, { status: "provider-unavailable" });
  }
}
