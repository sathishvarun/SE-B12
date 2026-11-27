"""Row-level security: a second lock inside PostgreSQL.

Every request that has a restaurant open runs its database work as the role `virundhu_tenant` with
`app.org_id` set to that restaurant (see app/database.py). For that role, PostgreSQL itself returns and accepts only
rows of that restaurant on every restaurant table, so a query that forgot `WHERE organization_id = ...` still can't
reach another restaurant. Background jobs, sign-in and the admin console run as the normal role, unaffected.

If the database user may not create roles, this migration skips itself and the app keeps working without it.

Revision ID: 0025
Revises: 0024
"""

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None

ROLE = "virundhu_tenant"
# Restaurant tables a tenant request reads or writes. Tables whose rows may have no restaurant (activity log, AI usage,
# product feedback) and the tables used to find the restaurant (memberships) stay outside, protected by the app.
TABLES = [
    "alert_logs", "alert_rules", "guest_recoveries", "import_batches", "invitations", "invoice_requests",
    "notifications", "outlets", "payments", "plan_reminders", "refunds", "review_requests", "reviews",
    "source_connections", "subscriptions", "support_tickets", "usage_counters", "weekly_reports",
]
# Child tables without their own organization_id: reachable only through their parent's restaurant.
CHILDREN = {
    "review_analyses": ("review_id", "reviews"),
    "review_corrections": ("review_id", "reviews"),
    "ticket_messages": ("ticket_id", "support_tickets"),
}


def upgrade() -> None:
    tables = ", ".join(f"'{t}'" for t in TABLES)
    children = ", ".join(f"('{t}', '{fk}', '{parent}')" for t, (fk, parent) in CHILDREN.items())
    op.execute(f"""
    DO $$
    DECLARE t text; c record;
    BEGIN
      BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN
          EXECUTE 'CREATE ROLE {ROLE} NOLOGIN';
        END IF;
        EXECUTE format('GRANT {ROLE} TO %I', current_user);
      EXCEPTION WHEN insufficient_privilege THEN
        RAISE NOTICE 'Row-level security skipped: this database user may not create roles';
        RETURN;
      END;
      EXECUTE format('GRANT USAGE ON SCHEMA public TO {ROLE}');
      EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ROLE}';
      EXECUTE 'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {ROLE}';
      EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {ROLE}';
      EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {ROLE}';
      FOREACH t IN ARRAY ARRAY[{tables}] LOOP
        IF to_regclass('public.' || t) IS NULL THEN CONTINUE; END IF;
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS tenant_only ON %I', t);
        EXECUTE format(
          'CREATE POLICY tenant_only ON %I TO {ROLE} '
          'USING (organization_id = current_setting(''app.org_id'')::int) '
          'WITH CHECK (organization_id = current_setting(''app.org_id'')::int)', t);
      END LOOP;
      FOR c IN SELECT * FROM (VALUES {children}) AS v(child, fk, parent) LOOP
        IF to_regclass('public.' || c.child) IS NULL THEN CONTINUE; END IF;
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', c.child);
        EXECUTE format('DROP POLICY IF EXISTS tenant_only ON %I', c.child);
        EXECUTE format(
          'CREATE POLICY tenant_only ON %I TO {ROLE} '
          'USING (EXISTS (SELECT 1 FROM %I p WHERE p.id = %I.%I)) '
          'WITH CHECK (EXISTS (SELECT 1 FROM %I p WHERE p.id = %I.%I))',
          c.child, c.parent, c.child, c.fk, c.parent, c.child, c.fk);
      END LOOP;
    END $$;
    """)


def downgrade() -> None:
    names = TABLES + list(CHILDREN)
    for t in names:
        op.execute(f"DROP POLICY IF EXISTS tenant_only ON {t}")
        op.execute(f"ALTER TABLE IF EXISTS {t} DISABLE ROW LEVEL SECURITY")
