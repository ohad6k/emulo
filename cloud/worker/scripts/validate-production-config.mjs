import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

const PRODUCT_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const SERVER_SIDE_SECRETS = [
  "POLAR_ACCESS_TOKEN",
  "POLAR_WEBHOOK_SECRET",
  "GITHUB_CLIENT_SECRET",
];
const DEPLOY_STAGE_REQUIRED_SECRETS = ["GITHUB_CLIENT_SECRET"];
const FORBIDDEN_VAR_KEYS = new Set(SERVER_SIDE_SECRETS);
const SANDBOX_DATABASE_ID = "63f95387-b248-4332-8bd7-3ef44bd3628a";

function invariant(condition, message) {
  if (!condition) throw new Error(message);
}

function sorted(values) {
  return [...values].sort();
}

export function validateProductionConfig(config) {
  invariant(config !== null && typeof config === "object", "config must be an object");
  invariant(config.name === "emulo-production", "production service name is invalid");
  invariant(
    config.preview_urls === false,
    "production preview URLs must remain disabled",
  );

  const vars = config.vars;
  invariant(vars !== null && typeof vars === "object", "production vars are missing");
  invariant(vars.APP_ENV === "production", "APP_ENV must be production");
  invariant(vars.POLAR_SERVER === "production", "Polar server must be production");
  invariant(
    vars.PAID_CHECKOUT_ENABLED === "false",
    "checkout must remain disabled in committed production config",
  );
  invariant(
    vars.PUBLIC_BASE_URL === "https://emulo-production.ohad1306.workers.dev/",
    "production public base URL is invalid",
  );
  for (const key of Object.keys(vars)) {
    invariant(!FORBIDDEN_VAR_KEYS.has(key), "secret values must not be stored in vars");
  }

  const databases = config.d1_databases;
  invariant(Array.isArray(databases) && databases.length === 1, "exactly one production D1 binding is required");
  const database = databases[0];
  invariant(database.binding === "DB", "production D1 binding must be DB");
  invariant(
    database.database_name === "emulo-autopilot-production",
    "production D1 database name is invalid",
  );
  invariant(
    typeof database.database_id === "string" &&
      database.database_id.length > 0 &&
      database.database_id !== SANDBOX_DATABASE_ID,
    "production D1 must not reuse the Sandbox database",
  );

  const requiredSecrets = config.secrets?.required;
  invariant(
    Array.isArray(requiredSecrets) &&
      JSON.stringify(sorted(requiredSecrets)) ===
        JSON.stringify(sorted(DEPLOY_STAGE_REQUIRED_SECRETS)),
    "deploy-stage secret declarations are incomplete or too broad",
  );

  const monthly = vars.POLAR_MONTHLY_PRODUCT_ID;
  const yearly = vars.POLAR_YEARLY_PRODUCT_ID;
  const productsUnconfigured = monthly === "not-configured" && yearly === "not-configured";
  const productsConfigured = PRODUCT_ID.test(monthly) && PRODUCT_ID.test(yearly);
  invariant(
    productsUnconfigured || productsConfigured,
    "Polar product IDs must be configured together",
  );
  invariant(
    typeof vars.GITHUB_CLIENT_ID === "string" && vars.GITHUB_CLIENT_ID.length > 0,
    "GitHub client ID declaration is missing",
  );

  return {
    service: config.name,
    database: database.database_name,
    activationState:
      productsConfigured && vars.GITHUB_CLIENT_ID !== "not-configured"
        ? "nonsecret-config-ready"
        : "provider-actions-required",
  };
}

async function main() {
  const path = process.argv[2] ?? "wrangler.production.jsonc";
  const config = JSON.parse(await readFile(path, "utf8"));
  const result = validateProductionConfig(config);
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  await main();
}
