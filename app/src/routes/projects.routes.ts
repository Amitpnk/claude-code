import { Router } from "express";
import { and, eq, sql } from "drizzle-orm";
import { db } from "../db/client";
import { projects, tasks } from "../db/schema";
import { NotFoundError, ValidationError } from "../lib/errors";
import { parsePriority } from "../lib/task-priority";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const byPriorityThenCreatedAt = (t: any, { asc }: any) => [
  sql`case ${t.priority} when 'high' then 0 when 'medium' then 1 else 2 end`,
  asc(t.createdAt),
];

export const projectsRouter = Router();

projectsRouter.get("/api/projects", async (_req, res, next) => {
  try {
    const rows = await db.query.projects.findMany({
      with: { tasks: { orderBy: byPriorityThenCreatedAt } },
      orderBy: (p, { asc }) => [asc(p.createdAt)],
    });
    res.json(rows);
  } catch (err) {
    next(err);
  }
});

projectsRouter.post("/api/projects", async (req, res, next) => {
  try {
    const { name, description } = req.body;
    if (!name || typeof name !== "string") {
      throw new ValidationError("name is required");
    }
    const [created] = await db.insert(projects).values({ name, description }).returning();
    res.status(201).json(created);
  } catch (err) {
    next(err);
  }
});

projectsRouter.get("/api/projects/:id", async (req, res, next) => {
  try {
    const id = Number(req.params.id);
    const project = await db.query.projects.findFirst({
      where: eq(projects.id, id),
      with: { tasks: { orderBy: byPriorityThenCreatedAt } },
    });
    if (!project) throw new NotFoundError("Project not found");
    res.json(project);
  } catch (err) {
    next(err);
  }
});

projectsRouter.delete("/api/projects/:id", async (req, res, next) => {
  try {
    const id = Number(req.params.id);
    const project = await db.query.projects.findFirst({ where: eq(projects.id, id) });
    if (!project) throw new NotFoundError("Project not found");
    await db.delete(projects).where(eq(projects.id, id));
    res.status(204).send();
  } catch (err) {
    next(err);
  }
});

projectsRouter.post("/api/projects/:id/tasks", async (req, res, next) => {
  try {
    const projectId = Number(req.params.id);
    const { title } = req.body;
    if (!title || typeof title !== "string") {
      throw new ValidationError("title is required");
    }
    const priority = parsePriority(req.body.priority);
    const project = await db.query.projects.findFirst({ where: eq(projects.id, projectId) });
    if (!project) throw new NotFoundError("Project not found");

    const [created] = await db
      .insert(tasks)
      .values({ projectId, title, ...(priority && { priority }) })
      .returning();
    res.status(201).json(created);
  } catch (err) {
    next(err);
  }
});

projectsRouter.delete("/api/projects/:projectId/tasks/:id", async (req, res, next) => {
  try {
    const projectId = Number(req.params.projectId);
    const id = Number(req.params.id);
    const task = await db.query.tasks.findFirst({
      where: and(eq(tasks.id, id), eq(tasks.projectId, projectId)),
    });
    if (!task) throw new NotFoundError("Task not found");
    await db.delete(tasks).where(eq(tasks.id, id));
    res.status(204).send();
  } catch (err) {
    next(err);
  }
});
