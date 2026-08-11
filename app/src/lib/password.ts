import bcrypt from "bcryptjs";

const COST_FACTOR = 10;

/**
 * A real bcrypt hash of a value nobody can supply. Compared against on the
 * user-lookup-miss path in POST /login so an unknown email costs the same time
 * as a wrong password — otherwise the timing difference discloses which emails
 * are registered.
 */
export const DUMMY_HASH = "$2b$10$bBFnVQL/qshRyaRcPx2MyeO835ZfGCFMGtDK/q7O.k6A.kLeU9JK6";

export async function hashPassword(plain: string): Promise<string> {
  return bcrypt.hash(plain, COST_FACTOR);
}

export async function verifyPassword(plain: string, hash: string): Promise<boolean> {
  return bcrypt.compare(plain, hash);
}
