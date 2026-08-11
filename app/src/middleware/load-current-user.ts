import { NextFunction, Request, Response } from "express";
import { eq } from "drizzle-orm";
import { db } from "../db/client";
import { users } from "../db/schema";

/**
 * Exposes the signed-in user to the views as `currentUser`. res.locals merges
 * into every res.render and EJS includes inherit the parent's data, so
 * partials/header.ejs sees it without any view passing it explicitly.
 * The password hash is never selected.
 */
export async function loadCurrentUser(
  req: Request,
  res: Response,
  next: NextFunction,
): Promise<void> {
  try {
    const userId = req.session.userId;
    if (!userId) {
      next();
      return;
    }

    const user = await db.query.users.findFirst({
      where: eq(users.id, userId),
      columns: { id: true, email: true },
    });

    if (user) {
      res.locals.currentUser = user;
    } else {
      // The session points at a user that no longer exists — treat as anonymous.
      delete req.session.userId;
    }
    next();
  } catch (err) {
    next(err);
  }
}
