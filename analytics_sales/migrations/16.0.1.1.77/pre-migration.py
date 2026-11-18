# -*- coding: utf-8 -*-
"""Consolidate old temporary forms, without touching saved API parameters."""


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT to_regclass('analytics_sales_settings')")
    if not cr.fetchone()[0]:
        return
    # Old TransientModel rows were just per-user copies. The saved IDs and
    # cron links remain in ir.config_parameter and are reloaded on menu open.
    cr.execute("DELETE FROM analytics_sales_settings WHERE company_id IS NULL")
    cr.execute("""
        DELETE FROM analytics_sales_settings s
        USING (
            SELECT id, row_number() OVER (
                PARTITION BY company_id ORDER BY write_date DESC NULLS LAST, id DESC
            ) AS position
            FROM analytics_sales_settings
        ) old
        WHERE s.id = old.id AND old.position > 1
    """)
