import type {
  EntitlementState,
  NormalizedEntitlement,
  ProductCode,
  ProductConfiguration,
} from "./contracts";

const SUBSCRIPTION_EVENTS = new Set([
  "subscription.created",
  "subscription.active",
  "subscription.updated",
  "subscription.canceled",
  "subscription.uncanceled",
  "subscription.past_due",
  "subscription.revoked",
]);

const ACCOUNT_PATTERN = /^acct_[a-f0-9]{32}$/;
const PROVIDER_ID_PATTERN = /^[A-Za-z0-9_-]{1,128}$/;
const POLAR_PRODUCT_ID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const UTC_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;
const DAY_MS = 24 * 60 * 60 * 1000;

export class BillingEventError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "BillingEventError";
  }
}

export class BillingConfigurationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "BillingConfigurationError";
  }
}

function object(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new BillingEventError(`${label} must be an object`);
  }
  return value as Record<string, unknown>;
}

function identifier(value: unknown, label: string): string {
  if (typeof value !== "string" || !PROVIDER_ID_PATTERN.test(value)) {
    throw new BillingEventError(`${label} is invalid`);
  }
  return value;
}

function timestamp(value: unknown, label: string): string {
  if (typeof value !== "string" || !UTC_PATTERN.test(value)) {
    throw new BillingEventError(`${label} is invalid`);
  }
  const milliseconds = Date.parse(value);
  if (!Number.isFinite(milliseconds)) {
    throw new BillingEventError(`${label} is invalid`);
  }
  return new Date(milliseconds).toISOString();
}

function optionalTimestamp(value: unknown, label: string): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  return timestamp(value, label);
}

function addDays(value: string, days: number): string {
  return new Date(Date.parse(value) + days * DAY_MS).toISOString();
}

function productCode(
  value: unknown,
  configuration: ProductConfiguration,
): ProductCode {
  if (
    !POLAR_PRODUCT_ID_PATTERN.test(configuration.monthlyProductId) ||
    !POLAR_PRODUCT_ID_PATTERN.test(configuration.yearlyProductId) ||
    configuration.monthlyProductId === configuration.yearlyProductId
  ) {
    throw new BillingConfigurationError("Polar product configuration is invalid");
  }
  const productId = identifier(value, "Polar product ID");
  if (productId === configuration.monthlyProductId) {
    return "founding-monthly";
  }
  if (productId === configuration.yearlyProductId) {
    return "founding-yearly";
  }
  throw new BillingEventError("Polar product is not allowed");
}

function entitlementState(
  eventType: string,
  status: unknown,
  cancelAtPeriodEnd: unknown,
): EntitlementState {
  if (typeof status !== "string") {
    throw new BillingEventError("Polar subscription status is invalid");
  }
  if (cancelAtPeriodEnd !== true && cancelAtPeriodEnd !== false) {
    throw new BillingEventError("Polar cancellation flag is invalid");
  }
  if (eventType === "subscription.revoked") {
    return "ended";
  }
  if (eventType === "subscription.past_due") {
    return "past_due";
  }
  if (
    eventType === "subscription.canceled" &&
    cancelAtPeriodEnd &&
    (status === "active" || status === "trialing")
  ) {
    return status;
  }
  if (eventType === "subscription.canceled") {
    return "ended";
  }
  if (status === "trialing") {
    return "trialing";
  }
  if (status === "active") {
    return "active";
  }
  if (status === "past_due") {
    return "past_due";
  }
  if (status === "canceled" || status === "unpaid") {
    return "ended";
  }
  throw new BillingEventError("Polar subscription status is unsupported");
}

export function normalizePolarSubscriptionEvent(
  input: unknown,
  configuration: ProductConfiguration,
): NormalizedEntitlement | null {
  const event = object(input, "Polar event");
  if (typeof event.type !== "string") {
    throw new BillingEventError("Polar event type is invalid");
  }
  if (!SUBSCRIPTION_EVENTS.has(event.type)) {
    return null;
  }
  const eventTimestamp = timestamp(event.timestamp, "Polar event timestamp");
  const data = object(event.data, "Polar subscription");
  const customer = object(data.customer, "Polar customer");
  if (
    typeof customer.external_id !== "string" ||
    !ACCOUNT_PATTERN.test(customer.external_id)
  ) {
    throw new BillingEventError("Polar external account ID is invalid");
  }
  const providerProductId = identifier(data.product_id, "Polar product ID");
  const code = productCode(providerProductId, configuration);
  const effectiveAt =
    data.modified_at === null || data.modified_at === undefined
      ? eventTimestamp
      : timestamp(data.modified_at, "Polar modified timestamp");
  const state = entitlementState(
    event.type,
    data.status,
    data.cancel_at_period_end,
  );
  return {
    accountId: customer.external_id,
    state,
    productCode: code,
    provider: "polar",
    providerSubscriptionId: identifier(data.id, "Polar subscription ID"),
    providerCustomerId: identifier(data.customer_id, "Polar customer ID"),
    providerProductId,
    effectiveAt,
    currentPeriodEnd: optionalTimestamp(
      data.current_period_end,
      "Polar current period end",
    ),
    graceEndsAt: state === "past_due" ? addDays(effectiveAt, 7) : null,
    recoveryEndsAt: state === "ended" ? addDays(effectiveAt, 30) : null,
  };
}
