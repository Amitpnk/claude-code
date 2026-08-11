import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    // Test files share one Postgres database and truncate each other's tables in
    // beforeAll, so they must not run concurrently.
    fileParallelism: false,
    hookTimeout: 20000,
    testTimeout: 20000,
  },
});
