import type {
  EntitlementState,
  Env,
  ProductCode,
} from "./contracts";
import { authenticateBrowserSession } from "./session";

export interface EntitlementSummary {
  state: EntitlementState;
  productCode: ProductCode | null;
  currentPeriodEnd: string | null;
  graceEndsAt: string | null;
  recoveryEndsAt: string | null;
}

export type AccountStatus =
  | {
      authenticated: false;
      environment: "sandbox" | "production";
      checkoutEnabled: false;
    }
  | {
      authenticated: true;
      environment: "sandbox" | "production";
      checkoutEnabled: boolean;
      entitlement: EntitlementSummary;
    };

interface EntitlementRow {
  state: EntitlementState;
  product_code: ProductCode;
  current_period_end: string | null;
  grace_ends_at: string | null;
  recovery_ends_at: string | null;
}

function environment(env: Env): "sandbox" | "production" {
  return env.POLAR_SERVER === "production" ? "production" : "sandbox";
}

export async function resolveAccountStatus(
  request: Request,
  env: Env,
  now = new Date(),
): Promise<AccountStatus> {
  const billingEnvironment = environment(env);
  const session = await authenticateBrowserSession(request, env.DB, now);
  if (session === null) {
    return {
      authenticated: false,
      environment: billingEnvironment,
      checkoutEnabled: false,
    };
  }

  const entitlement = await env.DB.prepare(
    `SELECT state, product_code, current_period_end, grace_ends_at, recovery_ends_at
     FROM entitlements
     WHERE account_id = ?`,
  )
    .bind(session.accountId)
    .first<EntitlementRow>();

  return {
    authenticated: true,
    environment: billingEnvironment,
    checkoutEnabled:
      env.PAID_CHECKOUT_ENABLED === "true" &&
      (env.POLAR_SERVER === "sandbox" || env.POLAR_SERVER === "production"),
    entitlement:
      entitlement === null
        ? {
            state: "none",
            productCode: null,
            currentPeriodEnd: null,
            graceEndsAt: null,
            recoveryEndsAt: null,
          }
        : {
            state: entitlement.state,
            productCode: entitlement.product_code,
            currentPeriodEnd: entitlement.current_period_end,
            graceEndsAt: entitlement.grace_ends_at,
            recoveryEndsAt: entitlement.recovery_ends_at,
          },
  };
}
