# Rules: testing

Applies to `app/tests/`. Run from `app/`.

## The suite runs against a real database

There is no mocking. `vitest` + `supertest` drive the real Express app against the
Postgres instance named by `DATABASE_URL`.

- `docker compose up -d` must be running before `npm run test`, or every test fails at
  connection time rather than on an assertion.
- `tests/projects.test.ts` runs `TRUNCATE TABLE tasks, projects RESTART IDENTITY CASCADE`
  in `beforeAll` — **once for the file, not per test**. Tests therefore share accumulated
  state and run order matters. A test that asserts on a global count (`expect(res.body)
  .toEqual([])`) only holds if nothing before it inserted.
- `afterAll` calls `pool.end()`. A new test file needs the same teardown or the run hangs
  on an open handle.
- Tests write to the same database as `npm run db:seed` and `npm run dev`. Running the
  suite destroys local seed data; re-seed afterwards.

## Writing tests

- Prefer creating the rows a test needs inside that test over relying on a previous
  test's leftovers.
- Assert the status code **and** the body shape. Status alone passes for the wrong reason
  when an error is being rendered as HTML.
- Cover the JSON surface via `request(app).get("/api/…")`. HTML routes are testable the
  same way — assert on the redirect (`302` + `location`) rather than parsing markup.
- Every new field needs three cases: the default value applied when omitted, an explicit
  valid value accepted, and an invalid value rejected with 400.

## Running

```bash
npm run test                                        # full suite
npx vitest run tests/projects.test.ts               # one file
npx vitest run -t "rejects a project without a name" # one test by name
```

`npm run lint` and `npm run test` must both pass clean before work is considered done.
