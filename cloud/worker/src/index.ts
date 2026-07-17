import { resolveAccountStatus } from "./account-status";
import {
  accountScript,
  accountStyles,
  renderAccountPage,
  renderPaymentPage,
  unavailablePage,
} from "./account-ui";
import type { Env } from "./contracts";
import { beginGitHubOAuth, completeGitHubOAuth } from "./github-auth";
import {
  beginGoogleOAuth,
  completeGoogleOAuth,
  isGoogleOAuthConfigured,
} from "./google-auth";
import { legalStyles, renderWorkerPolicy } from "./legal-pages";
import {
  handleListDevices,
  handlePairComplete,
  handlePairStart,
  handleRevokeDevice,
} from "./device-auth";
import {
  handleDeleteContinuity,
  handleContinuityExport,
  handleContinuityGeneration,
  handleContinuityHead,
  handleContinuityUpload,
} from "./continuity-routes";
import { handlePolarWebhook } from "./polar";
import { handlePolarCheckout, handlePolarPortal } from "./polar-client";
import emuloIcon from "../../../assets/emulo-oauth.png";

function json(status: number, body: unknown): Response {
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
    if (url.pathname === "/emulo.png" || url.pathname === "/assets/emulo.png") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return new Response(emuloIcon, {
        headers: {
          "cache-control": "public, max-age=86400, immutable",
          "content-type": "image/png",
          "x-content-type-options": "nosniff",
        },
      });
    }
    if (url.pathname === "/legal.css") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return legalStyles();
    }
    if (
      url.pathname === "/privacy.html" ||
      url.pathname === "/terms.html" ||
      url.pathname === "/refunds.html"
    ) {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return renderWorkerPolicy(url.pathname);
    }
    if (url.pathname === "/account") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      try {
        return renderAccountPage(await resolveAccountStatus(request, env), {
          googleEnabled: isGoogleOAuthConfigured(env),
        });
      } catch {
        return unavailablePage();
      }
    }
    if (url.pathname === "/account.js") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return accountScript();
    }
    if (url.pathname === "/account.css") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return accountStyles();
    }
    if (url.pathname === "/v1/billing/complete") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      try {
        return renderPaymentPage(await resolveAccountStatus(request, env), {
          googleEnabled: isGoogleOAuthConfigured(env),
        });
      } catch {
        return unavailablePage();
      }
    }
    if (url.pathname === "/v1/account/status") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      try {
        const status = await resolveAccountStatus(request, env);
        return status.authenticated
          ? json(200, status)
          : json(401, { status: "unauthenticated" });
      } catch {
        return json(503, { status: "unavailable" });
      }
    }
    if (url.pathname === "/v1/billing/webhooks/polar") {
      if (request.method !== "POST") {
        return json(405, { status: "method-not-allowed" });
      }
      return handlePolarWebhook(request, env);
    }
    if (url.pathname === "/v1/devices/pair/start") {
      if (request.method !== "POST") return json(405, { status: "method-not-allowed" });
      return handlePairStart(request, env);
    }
    if (url.pathname === "/v1/devices/pair/complete") {
      if (request.method !== "POST") return json(405, { status: "method-not-allowed" });
      return handlePairComplete(request, env);
    }
    if (url.pathname === "/v1/devices") {
      if (request.method !== "GET") return json(405, { status: "method-not-allowed" });
      return handleListDevices(request, env);
    }
    if (url.pathname.startsWith("/v1/devices/")) {
      if (request.method !== "DELETE") return json(405, { status: "method-not-allowed" });
      return handleRevokeDevice(request, env, url.pathname.slice("/v1/devices/".length));
    }
    if (url.pathname === "/v1/continuity/head") {
      if (request.method !== "GET") return json(405, { status: "method-not-allowed" });
      return handleContinuityHead(request, env);
    }
    if (url.pathname === "/v1/continuity/export") {
      if (request.method !== "GET") return json(405, { status: "method-not-allowed" });
      return handleContinuityExport(request, env);
    }
    if (url.pathname === "/v1/continuity") {
      if (request.method !== "DELETE") return json(405, { status: "method-not-allowed" });
      return handleDeleteContinuity(request, env);
    }
    if (url.pathname === "/v1/continuity/generations") {
      if (request.method !== "POST") return json(405, { status: "method-not-allowed" });
      return handleContinuityUpload(request, env);
    }
    if (url.pathname.startsWith("/v1/continuity/generations/")) {
      if (request.method !== "GET") return json(405, { status: "method-not-allowed" });
      return handleContinuityGeneration(
        request,
        env,
        url.pathname.slice("/v1/continuity/generations/".length),
      );
    }
    if (url.pathname === "/v1/auth/github/start") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return beginGitHubOAuth(env);
    }
    if (url.pathname === "/v1/auth/google/start") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return beginGoogleOAuth(env);
    }
    if (url.pathname === "/v1/auth/google/callback") {
      if (request.method !== "GET") {
        return json(405, { status: "method-not-allowed" });
      }
      return completeGoogleOAuth(request, env);
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
