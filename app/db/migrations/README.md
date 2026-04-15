# Database migrations

SQL migrations for the Supabase Postgres database.

## Naming

`YYYYMMDD_NN_<description>.sql` — timestamp-prefixed for lexicographic
ordering. `NN` is a 2-digit sequence number for the same day.

## Applying

This project does **not** use the Supabase CLI migration tooling. Apply
migrations manually via the Supabase dashboard SQL editor:

1. Open the project dashboard → SQL Editor → New query.
2. Paste the migration contents.
3. Run (Ctrl+Enter). Expect `Success. No rows returned`.
4. Verify the change lands by running a quick `SELECT` against the
   affected table.

## Conventions

- **Idempotent by default.** Use `IF NOT EXISTS` on `CREATE`,
  `ADD COLUMN IF NOT EXISTS`, `DROP ... IF EXISTS`, etc., so a migration
  can be safely re-run if its state is uncertain.
- **Non-destructive by default.** Prefer `ADD COLUMN` over `ALTER`, and
  `ALTER` over `DROP`. Destructive changes require a migration file with
  `_destructive` in the name and a comment block explaining the blast
  radius.
- **One concern per migration.** Don't bundle unrelated schema changes
  into the same file — it makes rollbacks painful.
- **End every migration with `NOTIFY pgrst, 'reload schema';`** so
  PostgREST picks up the new shape without waiting for its periodic
  refresh. Supabase usually auto-notifies but being explicit is free.
- **Keep `app/db/redditflow_schema.sql`** as the canonical full-schema
  snapshot. Update it when a migration lands so newcomers can reconstruct
  the DB from scratch with one file.
