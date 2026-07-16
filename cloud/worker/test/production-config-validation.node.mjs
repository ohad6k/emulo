import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { validateProductionConfig } from "../scripts/validate-production-config.mjs";

function validConfig() {
  return {
    name: "emulo-production",
    preview_urls: false,
    vars: {
      APP_ENV: "production",
      GITHUB_CLIENT_ID: "not-configured",
      PUBLIC_BASE_URL: "https://emulo-production.ohad1306.workers.dev/",
      PAID_CHECKOUT_ENABLED: "false",
      POLAR_SERVER: "production",
      POLAR_MONTHLY_PRODUCT_ID: "not-configured",
      POLAR_YEARLY_PRODUCT_ID: "not-configured",
    },
    secrets: {
      required: ["GITHUB_CLIENT_SECRET"],
    },
    d1_databases: [
      {
        binding: "DB",
        database_name: "emulo-autopilot-production",
        database_id: "62061306-a925-4497-9813-2d64ec572f18",
      },
    ],
  };
}

describe("production Wrangler configuration guard", () => {
  it("accepts an isolated disabled pre-activation config", () => {
    assert.deepEqual(validateProductionConfig(validConfig()), {
      service: "emulo-production",
      database: "emulo-autopilot-production",
      activationState: "provider-actions-required",
    });
  });

  it("accepts complete nonsecret provider identifiers while checkout is disabled", () => {
    const config = validConfig();
    config.vars.GITHUB_CLIENT_ID = "Ov23productionclient";
    config.vars.POLAR_MONTHLY_PRODUCT_ID = "11111111-1111-4111-8111-111111111111";
    config.vars.POLAR_YEARLY_PRODUCT_ID = "22222222-2222-4222-8222-222222222222";
    assert.equal(
      validateProductionConfig(config).activationState,
      "nonsecret-config-ready",
    );
  });

  it("rejects checkout enablement in the committed production config", () => {
    const config = validConfig();
    config.vars.PAID_CHECKOUT_ENABLED = "true";
    assert.throws(
      () => validateProductionConfig(config),
      /checkout must remain disabled/i,
    );
  });

  it("rejects Sandbox service, server, database, or public URL drift", () => {
    for (const mutate of [
      (config) => { config.name = "emulo"; },
      (config) => { config.vars.POLAR_SERVER = "sandbox"; },
      (config) => { config.d1_databases[0].database_name = "emulo-autopilot-beta"; },
      (config) => { config.vars.PUBLIC_BASE_URL = "https://emulo.ohad1306.workers.dev/"; },
    ]) {
      const config = validConfig();
      mutate(config);
      assert.throws(() => validateProductionConfig(config));
    }
  });

  it("rejects production preview hostnames", () => {
    const config = validConfig();
    config.preview_urls = true;
    assert.throws(
      () => validateProductionConfig(config),
      /preview URLs must remain disabled/i,
    );
  });

  it("rejects partial product configuration and secret values in vars", () => {
    const partial = validConfig();
    partial.vars.POLAR_MONTHLY_PRODUCT_ID = "11111111-1111-4111-8111-111111111111";
    assert.throws(
      () => validateProductionConfig(partial),
      /product IDs must be configured together/i,
    );

    const secretInVars = validConfig();
    secretInVars.vars.POLAR_ACCESS_TOKEN = "must-never-be-here";
    assert.throws(
      () => validateProductionConfig(secretInVars),
      /secret values must not be stored/i,
    );
  });

  it("requires only the deploy-stage GitHub secret", () => {
    const config = validConfig();
    config.secrets.required = [
      "GITHUB_CLIENT_SECRET",
      "POLAR_ACCESS_TOKEN",
    ];
    assert.throws(
      () => validateProductionConfig(config),
      /deploy-stage secret declarations/i,
    );
  });
});
