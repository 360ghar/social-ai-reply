"""Tests for the SQL statement splitter in run_migrations."""

from app.db.run_migrations import _split_statements


class TestSplitStatements:
    """Verify _split_statements handles dollar-quoting correctly."""

    def test_simple_statements(self):
        sql = "CREATE TABLE foo (id INT); CREATE TABLE bar (id INT);"
        assert _split_statements(sql) == [
            "CREATE TABLE foo (id INT)",
            "CREATE TABLE bar (id INT)",
        ]

    def test_dollar_quoted_block_preserved(self):
        """DO $$ ... END $$ blocks must not be split on internal semicolons."""
        sql = """\
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'foo' AND column_name = 'bar') THEN
        ALTER TABLE foo ADD COLUMN bar BOOLEAN DEFAULT TRUE;
    END IF;
END $$;"""
        stmts = _split_statements(sql)
        assert len(stmts) == 1
        assert "DO $$" in stmts[0]
        assert "END $$" in stmts[0]
        assert "END IF;" in stmts[0]

    def test_multiple_dollar_blocks(self):
        sql = """\
DO $$
BEGIN
    ALTER TABLE foo ADD COLUMN a TEXT;
END $$;

CREATE TABLE IF NOT EXISTS baz (id SERIAL PRIMARY KEY);

DO $$
BEGIN
    ALTER TABLE bar ADD COLUMN b TEXT;
END $$;"""
        stmts = _split_statements(sql)
        assert len(stmts) == 3
        assert "ALTER TABLE foo" in stmts[0]
        assert "CREATE TABLE" in stmts[1]
        assert "ALTER TABLE bar" in stmts[2]

    def test_notify_skipped_by_caller(self):
        """NOTIFY statements are returned but should be skipped by the caller."""
        sql = "CREATE TABLE foo (id INT);\nNOTIFY pgrst, 'reload schema';"
        stmts = _split_statements(sql)
        assert len(stmts) == 2
        assert stmts[1].startswith("NOTIFY")

    def test_empty_and_whitespace(self):
        assert _split_statements("") == []
        assert _split_statements("  ; ; ") == []
        assert _split_statements("  SELECT 1  ") == ["SELECT 1"]

    def test_trailing_no_semicolon(self):
        sql = "CREATE TABLE foo (id INT)"
        assert _split_statements(sql) == ["CREATE TABLE foo (id INT)"]

    def test_real_migration_20260617(self):
        """Regression test: the full 20260617_01 migration must split correctly."""
        sql = """\
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'personas_v1' AND column_name = 'is_active') THEN
        ALTER TABLE personas_v1 ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'personas_v1' AND column_name = 'source') THEN
        ALTER TABLE personas_v1 ADD COLUMN source TEXT;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS activity_logs (
    id              SERIAL PRIMARY KEY,
    workspace_id    INTEGER NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

NOTIFY pgrst, 'reload schema';"""
        stmts = _split_statements(sql)
        # Should be: DO block, CREATE TABLE, NOTIFY — not 6+ broken fragments
        assert len(stmts) == 3
        assert stmts[0].startswith("DO $$")
        assert "END IF;" in stmts[0]  # internal semicolons preserved
        assert "CREATE TABLE" in stmts[1]
        assert stmts[2].startswith("NOTIFY")
