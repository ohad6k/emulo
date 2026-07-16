import { SELF } from "cloudflare:test";
import { describe, expect, it } from "vitest";

describe("authenticated Worker integration", () => {
  it("serves bounded account and pending-payment pages", async () => {
    const account = await SELF.fetch("https://api.example/account");
    expect(account.status).toBe(200);
    expect(account.headers.get("cache-control")).toBe("no-store");
    const accountBody = await account.text();
    expect(accountBody).toContain("local Emulo control center");
    expect(accountBody).toContain('data-plan="monthly"');
    expect(accountBody).toContain('data-plan="yearly"');
    expect(accountBody).toContain("disabled");
    expect(accountBody).toContain('/account.js');

    const script = await SELF.fetch("https://api.example/account.js");
    expect(script.status).toBe(200);
    expect(script.headers.get("content-type")).toBe(
      "text/javascript; charset=utf-8",
    );
    expect(await script.text()).toContain('fetch("/v1/billing/checkout"');

    const complete = await SELF.fetch(
      "https://api.example/v1/billing/complete",
    );
    expect(complete.status).toBe(200);
    const body = await complete.text();
    expect(body).toContain("verified Polar confirmation");
    expect(body).not.toContain("access is active");
  });

  it("keeps checkout disabled through the public Worker route", async () => {
    const response = await SELF.fetch(
      "https://api.example/v1/billing/checkout",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ plan: "yearly" }),
      },
    );
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ status: "checkout-disabled" });
  });

  it("keeps exact methods on account and billing routes", async () => {
    expect(
      (
        await SELF.fetch("https://api.example/account", { method: "POST" })
      ).status,
    ).toBe(405);
    expect(
      (
        await SELF.fetch("https://api.example/account.js", { method: "POST" })
      ).status,
    ).toBe(405);
    expect(
      (
        await SELF.fetch("https://api.example/v1/billing/complete", {
          method: "POST",
        })
      ).status,
    ).toBe(405);
    expect(
      (
        await SELF.fetch("https://api.example/v1/billing/portal", {
          method: "GET",
        })
      ).status,
    ).toBe(405);
  });
});
