import { Hono } from "hono";

const app = new Hono();

app.get("/", (context) => context.json({ service: "hono", status: "ok" }));
app.get("/health", (context) => context.json({ status: "ok" }));

export default app;
