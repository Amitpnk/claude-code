import "dotenv/config";
import { db, pool } from "./client";
import { hashPassword } from "../lib/password";
import { projects, tasks, users } from "./schema";

// Plaintext here by design so the login page is usable straight after setup.
// Only the hash reaches the database.
const DEMO_USERS = [
  { email: "amit@taskflow.dev", password: "taskflow123" },
  { email: "dev@taskflow.dev", password: "taskflow456" },
  { email: "test@test.dev", password: "test123" },
];

async function main() {
  await db.insert(users).values(
    await Promise.all(
      DEMO_USERS.map(async (user) => ({
        email: user.email,
        passwordHash: await hashPassword(user.password),
      })),
    ),
  );

  const [website, mobile] = await db
    .insert(projects)
    .values([
      { name: "Website Redesign", description: "Refresh the marketing site" },
      { name: "Mobile App", description: "TaskFlow companion app" },
    ])
    .returning();

  await db.insert(tasks).values([
    { projectId: website.id, title: "Wireframe homepage", status: "done", priority: "medium" },
    { projectId: website.id, title: "Build hero section", status: "in_progress", priority: "high" },
    { projectId: website.id, title: "Write copy", status: "todo", priority: "low" },
    { projectId: mobile.id, title: "Set up project skeleton", status: "done", priority: "medium" },
    { projectId: mobile.id, title: "Design onboarding flow", status: "todo", priority: "high" },
  ]);

  console.log("Seeded sample projects and tasks.");
  console.log("Demo credentials:");
  for (const user of DEMO_USERS) {
    console.log(`  ${user.email} / ${user.password}`);
  }
  await pool.end();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
