import {
  cloudflareTest,
  readD1Migrations,
} from "@cloudflare/vitest-pool-workers";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

process.env.POLAR_WEBHOOK_SECRET ??= "test-only-placeholder";
process.env.GITHUB_CLIENT_SECRET ??= "github-secret-test";
process.env.POLAR_ACCESS_TOKEN ??= "polar-test-placeholder";

export default defineConfig({
  plugins: [
    cloudflareTest(async () => ({
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: {
        bindings: {
          APP_ENV: "test",
          GITHUB_CLIENT_ID: "github-client-test",
          GITHUB_CLIENT_SECRET: "github-secret-test",
          PUBLIC_BASE_URL: "https://api.example/",
          PAID_CHECKOUT_ENABLED: "false",
          POLAR_ACCESS_TOKEN: "polar-test-placeholder",
          POLAR_SERVER: "sandbox",
          POLAR_MONTHLY_PRODUCT_ID: "11111111-1111-4111-8111-111111111111",
          POLAR_YEARLY_PRODUCT_ID: "22222222-2222-4222-a222-222222222222",
          POLAR_WEBHOOK_SECRET: "test-only-placeholder",
          TEST_MIGRATIONS: await readD1Migrations(
            fileURLToPath(new URL("./migrations", import.meta.url)),
          ),
        },
      },
    })),
  ],
  test: {
    setupFiles: ["./test/apply-migrations.ts"],
  },
});
