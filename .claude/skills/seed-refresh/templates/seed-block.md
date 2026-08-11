# Seed block template

Template for app/src/db/seed.ts — copy the shape, not the literal text.
Every row below exists to make one branch of the UI visible after a seed.
The comment on each row names that branch. If you add a row without being
able to write such a comment, it is probably redundant data.

```ts
const [website, mobile, archive, inbox] = await db
  .insert(projects)
  .values([
    { name: "Website Redesign", description: "Refresh the marketing site" },
    { name: "Mobile App", description: "TaskFlow companion app" },
    // No description: exercises the falsy branch at dashboard.ejs:17 and project.ejs:8.
    { name: "Archive" },
    { name: "Inbox", description: "Unsorted work" },
  ])
  .returning();

await db.insert(tasks).values([
  // Cover every value of every enum at least once. Mixed priorities inside one
  // project are what make the priority ordering visible on the page.
  { projectId: website.id, title: "Wireframe homepage", status: "done", priority: "medium" },
  { projectId: website.id, title: "Build hero section", status: "in_progress", priority: "high" },
  { projectId: website.id, title: "Write copy", status: "todo", priority: "low" },
  { projectId: mobile.id, title: "Set up project skeleton", status: "done", priority: "medium" },
  { projectId: mobile.id, title: "Design onboarding flow", status: "todo", priority: "high" },
  // Archive gets exactly one task: exercises the singular "1 task" label at
  // dashboard.ejs:21. It also omits status and priority entirely rather than
  // passing null, so the database defaults (todo/medium) are what render —
  // the same path a task created through the UI takes.
  { projectId: archive.id, title: "Decide what to keep" },
]);

// `inbox` is deliberately given no tasks at all. Without a project like it the
// empty .task-list state in project.ejs is unreachable without deleting data by
// hand, and the plural/singular label only ever renders one way.
```
