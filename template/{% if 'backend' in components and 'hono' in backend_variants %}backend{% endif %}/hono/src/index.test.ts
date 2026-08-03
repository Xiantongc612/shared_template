import { describe, expect, test } from "bun:test";

import app from "./index";

describe("Hono service", () => {
  test("reports its health", async () => {
    const response = await app.request("/health");

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: "ok" });
  });
});
