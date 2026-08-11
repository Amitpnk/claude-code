import connectPgSimple from "connect-pg-simple";
import session from "express-session";
import { pool } from "../db/client";

const ONE_DAY_MS = 24 * 60 * 60 * 1000;

/**
 * Builds the session middleware. The secret is validated here rather than at
 * module load so a missing SESSION_SECRET fails with a stack that points at app
 * construction — every test file imports src/app.ts, so a bare top-level throw
 * would break the whole suite with an error that says nothing about auth.
 */
export function createSessionMiddleware() {
  const secret = process.env.SESSION_SECRET;
  if (!secret) {
    throw new Error(
      "SESSION_SECRET is not set. Add it to app/.env (see .env.example) before starting TaskFlow.",
    );
  }

  const PgStore = connectPgSimple(session);

  return session({
    name: "taskflow.sid",
    secret,
    store: new PgStore({
      pool,
      // The store's default table name is the singular "sessions" -> "session";
      // point it at the table src/db/schema.ts owns instead of creating its own.
      tableName: "sessions",
      createTableIfMissing: false,
      // The periodic prune keeps a timer alive that outlives pool.end() in vitest.
      pruneSessionInterval: process.env.NODE_ENV === "test" ? false : 60,
    }),
    resave: false,
    // Load-bearing: with this true every anonymous request writes a sessions row.
    saveUninitialized: false,
    cookie: {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      maxAge: ONE_DAY_MS,
    },
  });
}
