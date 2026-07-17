import {
  cloudflareTest,
  readD1Migrations,
} from "@cloudflare/vitest-pool-workers";
import { randomUUID } from "node:crypto";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const polarWebhookSecret = process.env.POLAR_WEBHOOK_SECRET ?? randomUUID();
const githubClientSecret = process.env.GITHUB_CLIENT_SECRET ?? randomUUID();
const googleClientSecret = process.env.GOOGLE_CLIENT_SECRET ?? randomUUID();
const polarAccessToken = process.env.POLAR_ACCESS_TOKEN ?? randomUUID();

process.env.POLAR_WEBHOOK_SECRET = polarWebhookSecret;
process.env.GITHUB_CLIENT_SECRET = githubClientSecret;
process.env.GOOGLE_CLIENT_SECRET = googleClientSecret;
process.env.POLAR_ACCESS_TOKEN = polarAccessToken;

export default defineConfig({
  plugins: [
    cloudflareTest(async () => ({
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: {
        bindings: {
          APP_ENV: "test",
          GITHUB_CLIENT_ID: "github-client-test",
          GITHUB_CLIENT_SECRET: githubClientSecret,
          GOOGLE_CLIENT_ID: "google-client-test.apps.googleusercontent.com",
          GOOGLE_CLIENT_SECRET: googleClientSecret,
          PUBLIC_BASE_URL: "https://api.example/",
          PAID_CHECKOUT_ENABLED: "false",
          POLAR_ACCESS_TOKEN: polarAccessToken,
          POLAR_SERVER: "sandbox",
          POLAR_MONTHLY_PRODUCT_ID: "11111111-1111-4111-8111-111111111111",
          POLAR_YEARLY_PRODUCT_ID: "22222222-2222-4222-a222-222222222222",
          POLAR_WEBHOOK_SECRET: polarWebhookSecret,
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
