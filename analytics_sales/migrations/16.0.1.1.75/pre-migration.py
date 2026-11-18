# -*- coding: utf-8 -*-
"""Convert the previous warehouse links before Odoo initializes the new field."""


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT to_regclass('analytics_sales_warehouse')")
    if not cr.fetchone()[0]:
        return
    cr.execute("""SELECT attname FROM pg_attribute
                  WHERE attrelid = 'analytics_sales_warehouse'::regclass
                    AND attnum > 0 AND NOT attisdropped""")
    columns = {row[0] for row in cr.fetchall()}
    if not {'local_id', 'direct_establishment_id'} <= columns:
        return
    cr.execute("ALTER TABLE analytics_sales_warehouse ADD COLUMN IF NOT EXISTS establishment_id integer")
    cr.execute("""
        UPDATE analytics_sales_warehouse w
           SET establishment_id = e.id
          FROM analytics_sales_establishment e
         WHERE w.establishment_id IS NULL
           AND w.direct_establishment_id = e.id
           AND w.company_id = e.company_id
    """)
    cr.execute("""
        WITH candidates AS (
            SELECT w.id AS warehouse_id, MIN(e.id) AS establishment_id
              FROM analytics_sales_warehouse w
              JOIN analytics_sales_local l ON l.id = w.local_id AND l.company_id = w.company_id
              JOIN analytics_sales_establishment_local_rel rel ON rel.local_id = l.id
              JOIN analytics_sales_establishment e ON e.id = rel.establishment_id
                 AND e.company_id = w.company_id AND e.active IS TRUE
             WHERE w.establishment_id IS NULL
             GROUP BY w.id HAVING COUNT(DISTINCT e.id) = 1
        )
        UPDATE analytics_sales_warehouse w
           SET establishment_id = c.establishment_id
          FROM candidates c WHERE w.id = c.warehouse_id AND w.establishment_id IS NULL
    """)
    # Release obsolete foreign-key references. Unresolved/ambiguous links remain unassigned.
    cr.execute("UPDATE analytics_sales_warehouse SET local_id = NULL, direct_establishment_id = NULL WHERE local_id IS NOT NULL OR direct_establishment_id IS NOT NULL")
