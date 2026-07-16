export type EntitlementState =
  | "none"
  | "trialing"
  | "active"
  | "past_due"
  | "grace"
  | "ended"
  | "refunded";

export type ProductCode = "founding-monthly" | "founding-yearly";

export interface ProductConfiguration {
  monthlyProductId: string;
  yearlyProductId: string;
}

export interface NormalizedEntitlement {
  accountId: string;
  state: EntitlementState;
  productCode: ProductCode;
  provider: "polar";
  providerSubscriptionId: string;
  providerCustomerId: string;
  providerProductId: string;
  effectiveAt: string;
  currentPeriodEnd: string | null;
  graceEndsAt: string | null;
  recoveryEndsAt: string | null;
}

export interface Env {
  DB: D1Database;
  APP_ENV: string;
  POLAR_MONTHLY_PRODUCT_ID: string;
  POLAR_YEARLY_PRODUCT_ID: string;
  POLAR_WEBHOOK_SECRET?: string;
  GITHUB_CLIENT_ID: string;
  GITHUB_CLIENT_SECRET: string;
  PUBLIC_BASE_URL: string;
  PAID_CHECKOUT_ENABLED: string;
  POLAR_ACCESS_TOKEN?: string;
  POLAR_SERVER: string;
}
