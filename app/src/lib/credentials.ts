import { ValidationError } from "./errors";

export interface Credentials {
  email: string;
  password: string;
}

/**
 * Parses a login form body. Follows the parsePriority pattern in task-priority.ts:
 * narrow unknown values with real type checks and throw ValidationError on bad input.
 * The email is trimmed and lowercased; the password is never trimmed, because
 * leading and trailing whitespace is significant in a password.
 */
export function parseCredentials(body: unknown): Credentials {
  if (typeof body !== "object" || body === null) {
    throw new ValidationError("Email and password are required");
  }
  const { email, password } = body as { email?: unknown; password?: unknown };

  if (typeof email !== "string" || email.trim() === "") {
    throw new ValidationError("Email and password are required");
  }
  if (typeof password !== "string" || password === "") {
    throw new ValidationError("Email and password are required");
  }

  return { email: email.trim().toLowerCase(), password };
}
