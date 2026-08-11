import express, { NextFunction, Request, Response } from "express";
import path from "path";
import { and, eq, sql } from "drizzle-orm";
import { db } from "./db/client";
import { projects, tasks } from "./db/schema";
import { authRouter } from "./routes/auth.routes";
import { projectsRouter } from "./routes/projects.routes";
import { AppError } from "./lib/errors";
import { createSessionMiddleware } from "./lib/session";
import { parsePriority } from "./lib/task-priority";
import { loadCurrentUser } from "./middleware/load-current-user";
import { requireAuth } from "./middleware/require-auth";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const byPriorityThenCreatedAt = (t: any, { asc }: any) => [
  sql`case ${t.priority} when 'high' then 0 when 'medium' then 1 else 2 end`,
  asc(t.createdAt),
];

export const app = express();

app.set("view engine", "ejs");
app.set("views", path.join(__dirname, "views"));
app.use(express.static(path.join(__dirname, "public")));
app.use(express.urlencoded({ extended: true }));
app.use(express.json());

// Sessions come after the body parsers and before every router, so all downstream
// handlers see req.session. express.static stays above this, so asset requests
// never touch the session store.
app.use(createSessionMiddleware());
app.use(loadCurrentUser);

app.use(authRouter);
app.use(projectsRouter);

app.get("/about", (_req, res) => {
  res.render("about");
});

app.get("/terms", (_req, res) => {
  res.render("terms");
});

app.get("/privacy", (_req, res) => {
  res.render("privacy");
});

app.get("/", async (_req, res, next) => {
  try {
    const rows = await db.query.projects.findMany({
      with: { tasks: { orderBy: byPriorityThenCreatedAt } },
      orderBy: (p, { asc }) => [asc(p.createdAt)],
    });
    res.render("dashboard", { projects: rows });
  } catch (err) {
    next(err);
  }
});

app.post("/projects", requireAuth, async (req, res, next) => {
  try {
    const { name, description } = req.body;
    await db.insert(projects).values({ name, description });
    res.redirect("/");
  } catch (err) {
    next(err);
  }
});

app.get("/projects/:id", async (req, res, next) => {
  try {
    const id = Number(req.params.id);
    const project = await db.query.projects.findFirst({
      where: eq(projects.id, id),
      with: { tasks: { orderBy: byPriorityThenCreatedAt } },
    });
    if (!project) {
      res.status(404).render("error", { message: "Project not found" });
      return;
    }
    res.render("project", { project });
  } catch (err) {
    next(err);
  }
});

app.post("/projects/:id/delete", requireAuth, async (req, res, next) => {
  try {
    const id = Number(req.params.id);
    await db.delete(projects).where(eq(projects.id, id));
    res.redirect("/");
  } catch (err) {
    next(err);
  }
});

app.post("/projects/:id/tasks", requireAuth, async (req, res, next) => {
  try {
    const projectId = Number(req.params.id);
    const { title } = req.body;
    const priority = parsePriority(req.body.priority);
    await db.insert(tasks).values({ projectId, title, ...(priority && { priority }) });
    res.redirect(`/projects/${projectId}`);
  } catch (err) {
    next(err);
  }
});

app.post("/projects/:projectId/tasks/:id/delete", requireAuth, async (req, res, next) => {
  try {
    const projectId = Number(req.params.projectId);
    const id = Number(req.params.id);
    await db.delete(tasks).where(and(eq(tasks.id, id), eq(tasks.projectId, projectId)));
    res.redirect(`/projects/${projectId}`);
  } catch (err) {
    next(err);
  }
});

app.use((err: Error, req: Request, res: Response, _next: NextFunction) => {
  const statusCode = err instanceof AppError ? err.statusCode : 500;
  if (req.path.startsWith("/api")) {
    res.status(statusCode).json({ error: err.message });
    return;
  }
  res.status(statusCode).render("error", { message: err.message });
});
