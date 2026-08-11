import { Request, Router } from "express";
import { eq } from "drizzle-orm";
import { db } from "../db/client";
import { users } from "../db/schema";
import { parseCredentials } from "../lib/credentials";
import { AuthError, ValidationError } from "../lib/errors";
import { DUMMY_HASH, verifyPassword } from "../lib/password";

export const authRouter = Router();

const LOGIN_TITLE = "Sign in — TaskFlow";

function regenerateSession(req: Request): Promise<void> {
  return new Promise((resolve, reject) => {
    req.session.regenerate((err) => (err ? reject(err) : resolve()));
  });
}

function saveSession(req: Request): Promise<void> {
  return new Promise((resolve, reject) => {
    req.session.save((err) => (err ? reject(err) : resolve()));
  });
}

function destroySession(req: Request): Promise<void> {
  return new Promise((resolve, reject) => {
    req.session.destroy((err) => (err ? reject(err) : resolve()));
  });
}

function submittedEmail(body: unknown): string {
  if (typeof body !== "object" || body === null) return "";
  const { email } = body as { email?: unknown };
  return typeof email === "string" ? email.trim().toLowerCase() : "";
}

authRouter.get("/login", (req, res) => {
  if (req.session.userId) {
    res.redirect("/");
    return;
  }
  res.render("login", { title: LOGIN_TITLE, error: null, email: "" });
});

authRouter.post("/login", async (req, res, next) => {
  const email = submittedEmail(req.body);
  try {
    const credentials = parseCredentials(req.body);
    const user = await db.query.users.findFirst({
      where: eq(users.email, credentials.email),
    });

    // Always run a bcrypt compare, even when the lookup missed, so an unknown
    // email costs the same time as a wrong password.
    const passwordMatches = await verifyPassword(
      credentials.password,
      user ? user.passwordHash : DUMMY_HASH,
    );
    if (!user || !passwordMatches) {
      throw new AuthError();
    }

    // Regenerate before storing userId so a pre-existing anonymous session id
    // cannot be fixated onto the authenticated session.
    await regenerateSession(req);
    req.session.userId = user.id;
    await saveSession(req);
    res.redirect("/");
  } catch (err) {
    // The one documented exception to throw-and-next(err): a rejected login is
    // expected user flow, so the form re-renders itself inline with the status
    // and message taken off the error rather than routing to error.ejs.
    if (err instanceof ValidationError || err instanceof AuthError) {
      res.status(err.statusCode).render("login", { title: LOGIN_TITLE, error: err.message, email });
      return;
    }
    next(err);
  }
});

authRouter.post("/logout", async (req, res, next) => {
  try {
    await destroySession(req);
    res.clearCookie("taskflow.sid");
    res.redirect("/login");
  } catch (err) {
    next(err);
  }
});
