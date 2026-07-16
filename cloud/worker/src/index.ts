import type { Env } from "./contracts";
import { beginGitHubOAuth, completeGitHubOAuth } from "./github-auth";
import { handlePolarWebhook } from "./polar";
import { handlePolarCheckout, handlePolarPortal } from "./polar-client";

function json(status: number, body: Record<string, string>): Response {
  return Response.json(body, {
    status,
    headers: {
      "cache-control": "no-store",
    },
  });
}

export default {
  async fetch(request, env, _context?): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/healthz") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return json(200, {
        service: "emulo-autopilot-api",
        status: "ok",
      });
    }
    if (url.pathname === "/v1/billing/webhooks/polar") {
      if (request.method !== "POST") {
        return json(405, { status: "method-not-allowed" });
      }
      return handlePolarWebhook(request, env);
    }
    if (url.pathname === "/v1/auth/github/start") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return beginGitHubOAuth(env);
    }
    if (url.pathname === "/v1/auth/github/callback") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return completeGitHubOAuth(request, env);
    }
    if (url.pathname === "/v1/billing/checkout") {
      if (request.method !== "POST") {
        return json(405, { status: "method-not-allowed" });
      }
      return handlePolarCheckout(request, env);
    }
    if (url.pathname === "/v1/billing/portal") {
      if (request.method !== "POST") {
        return json(405, { status: "method-not-allowed" });
      }
      return handlePolarPortal(request, env);
    }
    return json(404, { status: "not-found" });
  },
} satisfies ExportedHandler<Env>;
