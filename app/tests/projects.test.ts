import "dotenv/config";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import request from "supertest";
import { sql } from "drizzle-orm";
import { app } from "../src/app";
import { db, pool } from "../src/db/client";
import { projects, sessions, tasks, users } from "../src/db/schema";

beforeAll(async () => {
  await db.execute(
    sql`TRUNCATE TABLE ${tasks}, ${projects}, ${sessions}, ${users} RESTART IDENTITY CASCADE`,
  );
});

afterAll(async () => {
  await pool.end();
});

describe("projects API", () => {
  it("starts with no projects", async () => {
    const res = await request(app).get("/api/projects");
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it("creates a project", async () => {
    const res = await request(app).post("/api/projects").send({ name: "Test Project" });
    expect(res.status).toBe(201);
    expect(res.body.name).toBe("Test Project");
  });

  it("rejects a project without a name", async () => {
    const res = await request(app).post("/api/projects").send({});
    expect(res.status).toBe(400);
  });

  it("fetches a project with its tasks", async () => {
    const created = await request(app).post("/api/projects").send({ name: "With Tasks" });
    const projectId = created.body.id;

    await request(app).post(`/api/projects/${projectId}/tasks`).send({ title: "First task" });

    const res = await request(app).get(`/api/projects/${projectId}`);
    expect(res.status).toBe(200);
    expect(res.body.tasks).toHaveLength(1);
    expect(res.body.tasks[0].title).toBe("First task");
  });

  it("404s for a missing project", async () => {
    const res = await request(app).get("/api/projects/999999");
    expect(res.status).toBe(404);
  });

  it("defaults a task's priority to medium", async () => {
    const created = await request(app).post("/api/projects").send({ name: "Priority Default" });
    const res = await request(app)
      .post(`/api/projects/${created.body.id}/tasks`)
      .send({ title: "No priority given" });
    expect(res.status).toBe(201);
    expect(res.body.priority).toBe("medium");
  });

  it("persists an explicit task priority", async () => {
    const created = await request(app).post("/api/projects").send({ name: "Priority Explicit" });
    const res = await request(app)
      .post(`/api/projects/${created.body.id}/tasks`)
      .send({ title: "Urgent task", priority: "high" });
    expect(res.status).toBe(201);
    expect(res.body.priority).toBe("high");
  });

  it("rejects an invalid task priority", async () => {
    const created = await request(app).post("/api/projects").send({ name: "Priority Invalid" });
    const res = await request(app)
      .post(`/api/projects/${created.body.id}/tasks`)
      .send({ title: "Bad priority", priority: "urgent" });
    expect(res.status).toBe(400);
  });

  it("sorts a project's tasks by priority (high to low), then by creation order", async () => {
    const created = await request(app).post("/api/projects").send({ name: "Priority Sort" });
    const projectId = created.body.id;
    await request(app).post(`/api/projects/${projectId}/tasks`).send({ title: "low one", priority: "low" });
    await request(app).post(`/api/projects/${projectId}/tasks`).send({ title: "high one", priority: "high" });
    await request(app).post(`/api/projects/${projectId}/tasks`).send({ title: "medium one", priority: "medium" });

    const res = await request(app).get(`/api/projects/${projectId}`);
    expect(res.body.tasks.map((t: { title: string }) => t.title)).toEqual([
      "high one",
      "medium one",
      "low one",
    ]);
  });

  it("deletes a task", async () => {
    const created = await request(app).post("/api/projects").send({ name: "Delete Task" });
    const projectId = created.body.id;
    const task = await request(app)
      .post(`/api/projects/${projectId}/tasks`)
      .send({ title: "Doomed task" });

    const del = await request(app).delete(`/api/projects/${projectId}/tasks/${task.body.id}`);
    expect(del.status).toBe(204);

    const res = await request(app).get(`/api/projects/${projectId}`);
    expect(res.body.tasks).toHaveLength(0);
  });

  it("404s deleting a task that doesn't belong to the project", async () => {
    const created = await request(app).post("/api/projects").send({ name: "Wrong Project" });
    const other = await request(app).post("/api/projects").send({ name: "Other Project" });
    const task = await request(app)
      .post(`/api/projects/${other.body.id}/tasks`)
      .send({ title: "Not yours" });

    const del = await request(app).delete(`/api/projects/${created.body.id}/tasks/${task.body.id}`);
    expect(del.status).toBe(404);
  });

  it("deletes a project and cascades its tasks", async () => {
    const created = await request(app).post("/api/projects").send({ name: "Delete Project" });
    const projectId = created.body.id;
    await request(app).post(`/api/projects/${projectId}/tasks`).send({ title: "Goes too" });

    const del = await request(app).delete(`/api/projects/${projectId}`);
    expect(del.status).toBe(204);

    const res = await request(app).get(`/api/projects/${projectId}`);
    expect(res.status).toBe(404);
  });

  it("404s deleting a project that doesn't exist", async () => {
    const del = await request(app).delete("/api/projects/999999");
    expect(del.status).toBe(404);
  });
});
