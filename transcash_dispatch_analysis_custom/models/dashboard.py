from collections import defaultdict
from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.transcash_dispatch_analysis.services.engine import aggregate_invoice, as_date, evaluate
from ..services.monthly import monthly_dispatch


def external_delay_label(value):
    text = "" if value is None or value is False else str(value).strip()
    for prefix in ("FAC/", "FA/"):
        if text.upper().startswith(prefix):
            text = text[len(prefix):].strip()
            break
    return "FA/" + (text or "SIN NÚMERO EXTERNO")


def previous_delay_label(value):
    text = "" if value is None or value is False else str(value).strip()
    if not text:
        return ""
    upper = text.upper()
    if upper.startswith("FAC/") or upper.startswith("FA/"):
        prefix = text[:text.find('/')]
        suffix = text[text.find('/') + 1:].strip()
        return prefix.upper() + "/" + suffix if suffix else prefix.upper()
    parts = text.split()
    if len(parts) >= 2 and parts[0].isalpha():
        return parts[0].upper() + "/" + " ".join(parts[1:]).strip()
    return text


def combined_delay_label(previous_value, external_value):
    previous = previous_delay_label(previous_value)
    external = external_delay_label(external_value)
    if previous and external and previous != external:
        return f"{previous} / {external}"
    return previous or external


class DispatchDashboardCustom(models.AbstractModel):
    _inherit = "dispatch.dashboard"

    @api.model
    def get_data(self, filters=None, board_id=False, include_ids=False):
        result = super().get_data(filters, board_id, include_ids)
        # Do not run annual statistics when opening native detail actions.
        if not include_ids:
            cohorts = result["timeliness"]["delays"]
            top = [row for cohort in cohorts.values() for row in cohort["top"]]
            ids = list({row["id"] for row in top})
            headers = self.env["dispatch.invoice"].search_read(
                [("id", "in", ids)], ["external_number"]) if ids else []
            external = {row["id"]: row["external_number"] for row in headers}
            for row in top:
                row["custom_external_label"] = combined_delay_label(row.get("name"), external.get(row["id"]))
            result["monthly"] = self._annual_statistics(filters or {})
        return result

    @api.model
    def _scope_warehouse_rows(self, rows, transport_lines):
        if not rows:
            return []
        line_groups = defaultdict(list)
        for line in transport_lines:
            if line.get("raw_data"): line_groups[line["invoice_id"][0]].append(line["raw_data"])
        snapshots_for_scope = self.env["dispatch.snapshot"].browse(sorted({r["snapshot_id"][0] for r in rows}))
        packs_for_scope = {snapshot.id:snapshot.policy_pack or {} for snapshot in snapshots_for_scope}
        scoped = []
        for row in rows:
            if row["id"] not in line_groups: continue
            summary = aggregate_invoice(row["invoice_key"],line_groups[row["id"]],row["cutoff_date"])
            evaluated = {**row, **evaluate(summary, packs_for_scope.get(row["snapshot_id"][0], {}))}
            scoped.append({key: evaluated.get(key) for key in (
                "id", "name", "invoice_date", "completion_date", "cutoff_date", "pending",
                "physically_completed", "eligible", "sla_configured", "quality_issue",
                "has_adjustment", "sla_status", "deadline", "customer", "city")})
        return scoped

    @api.model
    def _annual_statistics(self, filters):
        # The yearly charts have their own explicitly labelled date scope; other
        # filters and the selected snapshot are identical to the dashboard.
        anchor = as_date(filters.get("date_to") or filters.get("date_from"))
        if not anchor and filters.get("snapshot_id"):
            # _domain in get_data has already validated the selected cut.
            anchor = self.env["dispatch.snapshot"].browse(int(filters["snapshot_id"])).cutoff_date
        year = (anchor or fields.Date.context_today(self)).year
        start, end = date(year, 1, 1).isoformat(), date(year, 12, 31).isoformat()
        base = {key: value for key, value in filters.items() if key not in ("date_from", "date_to")}
        domain = self._domain({**base, "date_to": end})
        warehouse_ids = base.get("warehouse_ids") or []
        # Earlier invoices may complete this year. With a warehouse selection,
        # the scoped completion date may differ from the full invoice's date.
        completion_field = "line_ids.last_dispatch_date" if warehouse_ids else "completion_date"
        domain += ["|", ("invoice_date", ">=", start), (completion_field, ">=", start)]
        invoices = self.env["dispatch.invoice"]
        if invoices.search_count(domain) > 200_000:
            return {"year": year, "available": False, "months": [],
                    "reason": "El análisis anual supera 200.000 facturas. Selecciona una fuente o bodega para reducir el alcance."}
        annual_fields = ["name", "invoice_date", "completion_date", "cutoff_date", "pending",
                         "physically_completed", "eligible", "sla_configured", "quality_issue",
                         "has_adjustment", "sla_status", "deadline", "customer", "city"]
        if warehouse_ids:
            annual_fields += ["invoice_key", "snapshot_id"]
        rows = invoices.search_read(domain, annual_fields)
        if warehouse_ids:
            scoped = []
            for offset in range(0, len(rows), 2000):
                batch = rows[offset:offset + 2000]
                lines = self.env["dispatch.invoice.line"].search_read([
                    ("invoice_id", "in", [row["id"] for row in batch]),
                    ("warehouse_id", "in", warehouse_ids)], ["invoice_id", "raw_data"])
                scoped.extend(self._scope_warehouse_rows(batch, lines))
            rows = scoped
        return monthly_dispatch(rows, year)

    @api.model
    def _active_filter_scope(self):
        """Keep preferences separate for each set of enabled companies."""
        return ",".join(str(company_id) for company_id in sorted(self.env.companies.ids))

    @api.model
    def get_active_filter_state(self):
        """Compatibility with cached dashboard assets from previous versions."""
        return self.get_custom_active_filter_state()

    @api.model
    def save_active_filter_state(self, filters=None, board_id=False, favorite_id=False):
        """Use the same validated preference store as the custom dashboard."""
        return self.save_custom_active_filter_state(filters, board_id, favorite_id)

    @api.model
    def get_custom_active_filter_state(self):
        """Restore the user's last *applied* selection, not default dates."""
        self._access()
        record = self.env["dispatch.dashboard.custom.state"].sudo().search([
            ("user_id", "=", self.env.uid),
            ("company_scope", "=", self._active_filter_scope()),
        ], limit=1)
        if not record:
            return False
        filters = record.filters_json if isinstance(record.filters_json, dict) else {}
        allowed_keys = ("source_id", "snapshot_id", "date_from", "date_to", "city", "delivery",
                        "planning_scope", "planning_grouping", "warehouse_ids")
        # A board can become private or be deleted after it was selected.
        board_id = record.board_id.id if record.board_id and self.env["dispatch.board"].search([
            ("id", "=", record.board_id.id)], limit=1) else False
        favorites = self.get_saved_filters() if record.favorite_id else []
        favorite_id = record.favorite_id.id if any(
            favorite["id"] == record.favorite_id.id for favorite in favorites) else False
        return {
            "filters": {key: filters[key] for key in allowed_keys if key in filters},
            "board_id": board_id,
            "favorite_id": favorite_id,
        }

    @api.model
    def save_custom_active_filter_state(self, filters=None, board_id=False, favorite_id=False):
        """Remember only validated filters successfully applied to the dashboard."""
        self._access()
        if not isinstance(filters, dict):
            raise ValidationError(_("Filtros inválidos."))
        allowed_keys = ("source_id", "snapshot_id", "date_from", "date_to", "city", "delivery",
                        "planning_scope", "planning_grouping", "warehouse_ids")
        allowed = {key: filters[key] for key in allowed_keys if key in filters}
        self._domain(allowed)
        if allowed.get("planning_scope", "transcash") not in ("transcash", "filtered"):
            raise ValidationError(_("Alcance de planificación no permitido."))
        if allowed.get("planning_grouping", "warehouse") not in ("warehouse", "destination"):
            raise ValidationError(_("Forma de agrupar la carga no permitida."))
        if board_id:
            board = self.env["dispatch.board"].browse(int(board_id)).exists()
            if not board:
                board_id = False
            else:
                board.check_access_rights("read")
                board.check_access_rule("read")
                board_id = board.id
        if favorite_id:
            try:
                favorite_id = int(favorite_id)
            except (TypeError, ValueError):
                favorite_id = False
            if favorite_id and not any(f["id"] == favorite_id for f in self.get_saved_filters()):
                favorite_id = False
        values = {"filters_json": allowed, "board_id": board_id or False,
                  "favorite_id": favorite_id or False}
        # A user may open multiple tabs; serialize preference creation/update.
        self.env.cr.execute("SELECT pg_advisory_xact_lock(%s, %s)", (1801807, self.env.uid))
        model = self.env["dispatch.dashboard.custom.state"].sudo()
        record = model.search([
            ("user_id", "=", self.env.uid),
            ("company_scope", "=", self._active_filter_scope()),
        ], limit=1)
        if record:
            record.write(values)
        else:
            model.create({**values, "user_id": self.env.uid,
                          "company_scope": self._active_filter_scope()})
        return True

