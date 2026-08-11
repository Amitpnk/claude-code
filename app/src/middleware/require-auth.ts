import { NextFunction, Request, Response } from "express";

/**
 * Guards the HTML routes that mutate data. A browser form flow gets a redirect
 * to the login page, not a 401 error page.
 */
export function requireAuth(req: Request, res: Response, next: NextFunction): void {
  if (!req.session.userId) {
    res.redirect("/login");
    return;
  }
  next();
}
