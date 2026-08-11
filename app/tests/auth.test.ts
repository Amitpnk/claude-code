import "dotenv/config";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import request from "supertest";
import { sql } from "drizzle-orm";
import { app } from "../src/app";
import { db, pool } from "../src/db/client";
import { projects, sessions, tasks, users } from "../src/db/schema";
import { hashPassword } from "../src/lib/password";

const KNOWN_EMAIL = "auth-test@taskflow.dev";
const KNOWN_PASSWORD = "correct-horse-battery";
const UNKNOWN_EMAIL = "nobody@taskflow.dev";

beforeAll(async () => {
  await db.execute(
    sql`TRUNCATE TABLE ${tasks}, ${projects}, ${sessions}, ${users} RESTART IDENTITY CASCADE`,
  );
  await db.insert(users).values({
    email: KNOWN_EMAIL,
    passwordHash: await hashPassword(KNOWN_PASSWORD),
  });
});

afterAll(async () => {
  await pool.end();
});

function login(agent: ReturnType<typeof request.agent>, email: string, password: string) {
  return agent.post("/login").type("form").send({ email, password });
}

describe("GET /login", () => {
  it("renders the login form", async () => {
    const res = await request(app).get("/login");
    expect(res.status).toBe(200);
    expect(res.text).toContain('action="/login"');
    expect(res.text).toContain('name="email"');
    expect(res.text).toContain('name="password"');
  });

  it("redirects an authenticated visitor to /", async () => {
    const agent = request.agent(app);
    await login(agent, KNOWN_EMAIL, KNOWN_PASSWORD);

    const res = await agent.get("/login");
    expect(res.status).toBe(302);
    expect(res.headers.location).toBe("/");
  });
});

describe("POST /login", () => {
  it("establishes a session and redirects to / on correct credentials", async () => {
    const res = await login(request.agent(app), KNOWN_EMAIL, KNOWN_PASSWORD);
    expect(res.status).toBe(302);
    expect(res.headers.location).toBe("/");

    const cookies = res.headers["set-cookie"];
    expect(cookies).toBeDefined();
    expect(String(cookies)).toContain("taskflow.sid");
    expect(String(cookies)).toContain("HttpOnly");
  });

  it("succeeds when the email differs only in case", async () => {
    const res = await login(request.agent(app), "Auth-Test@TaskFlow.DEV", KNOWN_PASSWORD);
    expect(res.status).toBe(302);
    expect(res.headers.location).toBe("/");
  });

  it("rejects a wrong password with 401 and a generic message", async () => {
    const res = await login(request.agent(app), KNOWN_EMAIL, "not-the-password");
    expect(res.status).toBe(401);
    expect(res.text).toContain("Invalid email or password");
  });

  it("rejects an unknown email with the same status and message as a wrong password", async () => {
    const res = await login(request.agent(app), UNKNOWN_EMAIL, "not-the-password");
    expect(res.status).toBe(401);
    expect(res.text).toContain("Invalid email or password");
  });

  it("renders an identical page for an unknown email and a wrong password", async () => {
    // The submitted email is echoed back into the form, and the attacker already
    // knows what they submitted. Normalising it out is what makes the comparison
    // meaningful: everything else about the two responses must be identical, so
    // the response never discloses which emails are registered.
    const wrongPassword = await login(request.agent(app), KNOWN_EMAIL, "not-the-password");
    const unknownEmail = await login(request.agent(app), UNKNOWN_EMAIL, "not-the-password");

    expect(unknownEmail.status).toBe(wrongPassword.status);
    expect(unknownEmail.text.split(UNKNOWN_EMAIL).join("EMAIL")).toBe(
      wrongPassword.text.split(KNOWN_EMAIL).join("EMAIL"),
    );
  });

  it("never echoes the submitted password back into the page", async () => {
    const secret = "super-secret-value-9f3a";
    const res = await login(request.agent(app), KNOWN_EMAIL, secret);
    expect(res.status).toBe(401);
    expect(res.text).not.toContain(secret);
  });

  it("rejects a missing password with 400 without querying the users table", async () => {
    const lookup = vi.spyOn(db.query.users, "findFirst");
    try {
      const res = await request(app).post("/login").type("form").send({ email: KNOWN_EMAIL });
      expect(res.status).toBe(400);
      expect(res.text).toContain("Email and password are required");
      expect(lookup).not.toHaveBeenCalled();
    } finally {
      lookup.mockRestore();
    }
  });

  it("rejects a missing email with 400", async () => {
    const res = await request(app).post("/login").type("form").send({ password: KNOWN_PASSWORD });
    expect(res.status).toBe(400);
    expect(res.text).toContain("Email and password are required");
  });
});

describe("session lifetime", () => {
  beforeEach(async () => {
    await db.delete(sessions);
  });

  it("is recognised on a subsequent request and shows the email in the header", async () => {
    const agent = request.agent(app);
    await login(agent, KNOWN_EMAIL, KNOWN_PASSWORD);

    const res = await agent.get("/");
    expect(res.status).toBe(200);
    expect(res.text).toContain(KNOWN_EMAIL);
    expect(res.text).toContain('action="/logout"');
  });

  it("stores the session in Postgres on login and removes it on logout", async () => {
    const agent = request.agent(app);
    await login(agent, KNOWN_EMAIL, KNOWN_PASSWORD);
    expect(await db.select().from(sessions)).toHaveLength(1);

    await agent.post("/logout");
    expect(await db.select().from(sessions)).toHaveLength(0);
  });

  it("writes no session row for an anonymous request", async () => {
    await request(app).get("/");
    expect(await db.select().from(sessions)).toHaveLength(0);
  });
});

describe("POST /logout", () => {
  it("ends the session and redirects to /login", async () => {
    const agent = request.agent(app);
    await login(agent, KNOWN_EMAIL, KNOWN_PASSWORD);

    const res = await agent.post("/logout");
    expect(res.status).toBe(302);
    expect(res.headers.location).toBe("/login");

    const after = await agent.get("/");
    expect(after.text).not.toContain(KNOWN_EMAIL);
    expect(after.text).toContain('href="/login"');
  });

  it("redirects without erroring when there is no session", async () => {
    const res = await request(app).post("/logout");
    expect(res.status).toBe(302);
    expect(res.headers.location).toBe("/login");
  });
});

describe("route guards", () => {
  it("redirects an unauthenticated project creation to /login and creates nothing", async () => {
    const before = await db.select().from(projects);

    const res = await request(app).post("/projects").type("form").send({ name: "Anonymous" });
    expect(res.status).toBe(302);
    expect(res.headers.location).toBe("/login");

    expect(await db.select().from(projects)).toHaveLength(before.length);
  });

  it("guards every mutating HTML route", async () => {
    const guarded = [
      "/projects",
      "/projects/1/delete",
      "/projects/1/tasks",
      "/projects/1/tasks/1/delete",
    ];

    for (const path of guarded) {
      const res = await request(app).post(path).type("form").send({});
      expect(res.status, path).toBe(302);
      expect(res.headers.location, path).toBe("/login");
    }
  });

  it("leaves the read routes publicly readable", async () => {
    const [project] = await db.insert(projects).values({ name: "Public Read" }).returning();
    const paths = ["/", `/projects/${project.id}`, "/about", "/terms", "/privacy"];

    for (const path of paths) {
      const res = await request(app).get(path);
      expect(res.status, path).toBe(200);
    }
  });

  it("lets an authenticated user create a project and a task end to end", async () => {
    const agent = request.agent(app);
    await login(agent, KNOWN_EMAIL, KNOWN_PASSWORD);

    const created = await agent.post("/projects").type("form").send({ name: "Authed Project" });
    expect(created.status).toBe(302);

    const rows = await db.select().from(projects);
    const project = rows.find((row) => row.name === "Authed Project");
    expect(project).toBeDefined();

    const task = await agent
      .post(`/projects/${project?.id}/tasks`)
      .type("form")
      .send({ title: "Authed task", priority: "high" });
    expect(task.status).toBe(302);

    const page = await agent.get(`/projects/${project?.id}`);
    expect(page.text).toContain("Authed task");
  });
});
