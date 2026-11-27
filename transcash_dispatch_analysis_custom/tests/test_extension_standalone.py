"""Run without Odoo: python -m unittest discover -s tests -p 'test_extension_standalone.py'.
Requires the original transcash_dispatch_analysis folder beside this extension.
"""
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from importlib.util import spec_from_file_location, module_from_spec
from unittest.mock import patch
from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'transcash_dispatch_analysis'
sys.path.insert(0, str(BASE / 'tests'))
from test_dashboard_standalone import module, Environment, data, InvoiceModel
from test_import_queue_standalone import Field
from dispatch_queue_test.services.engine import evaluate, invoice_key
import dispatch_queue_test.services.engine as engine
import dispatch_queue_test.services.timeliness as timeliness

# Load real extension using native dashboard class with a read-only fake ORM.
odoo = ModuleType('odoo')
odoo.api = SimpleNamespace(model=lambda f: f)
odoo.fields = SimpleNamespace(Date=Field())
odoo.models = SimpleNamespace(AbstractModel=module.DispatchDashboard)
odoo._ = lambda s: s
errors = ModuleType('odoo.exceptions')
errors.ValidationError = ValueError
for name, path in [('dispatch_extension_test', ROOT), ('dispatch_extension_test.models', ROOT/'models'), ('dispatch_extension_test.services', ROOT/'services')]:
    pkg = ModuleType(name); pkg.__path__ = [str(path)]; sys.modules[name] = pkg
aliases = {'odoo': odoo, 'odoo.exceptions': errors,
           'odoo.addons.transcash_dispatch_analysis.services.engine': engine,
           'odoo.addons.transcash_dispatch_analysis.services.timeliness': timeliness}
with patch.dict(sys.modules, aliases):
    spec = spec_from_file_location('dispatch_extension_test.models.dashboard', ROOT/'models/dashboard.py')
    ext = module_from_spec(spec); sys.modules[spec.name] = ext; spec.loader.exec_module(ext)

class AnnualInvoiceModel(InvoiceModel):
    def matching(self, domain):
        if '|' not in domain:
            return super().matching(domain)
        i = domain.index('|')
        common = domain[:i] + domain[i+3:]
        # PostgreSQL/Odoo date false never satisfies >=.
        result = []
        for row in super().matching(common):
            for key, op, value in domain[i+1:i+3]:
                actual = row.get(key)
                if key == 'line_ids.last_dispatch_date':
                    ok = any(d >= value for d in row.get('line_dispatch_dates', []))
                else:
                    ok = bool(actual and actual >= value)
                if ok:
                    result.append(row); break
        return result

class ExtensionTests(unittest.TestCase):
    def service(self, rows, lines):
        service = ext.DispatchDashboardCustom(); service.env = Environment(rows, lines)
        service.env.models['dispatch.invoice'] = AnnualInvoiceModel(rows)
        return service

    def test_annual_pending_sum(self):
        rows = [dict(id=i, invoice_date='2026-01-01', cutoff_date='2026-11-27', pending=True) for i in range(5)]
        rows += [dict(id=i, invoice_date='2026-02-01', cutoff_date='2026-11-27', pending=True) for i in range(5,8)]
        rows += [dict(id=9, invoice_date='2025-12-01', cutoff_date='2026-11-27', pending=True)]
        result = ext.monthly_dispatch(rows, 2026)
        self.assertEqual([m['pending_accumulated'] for m in result['months']], [5]+[8]*11)
        self.assertEqual(result['pending_total'],8)

    def test_delay_rate(self):
        base = dict(id=1, invoice_date='2026-01-01', completion_date='2026-02-01', cutoff_date='2026-02-10', deadline='2026-01-04', pending=False, physically_completed=True, eligible=True, sla_configured=True, sla_status='late')
        rows = [base, {**base, 'id':2, 'deadline':'2026-02-02', 'sla_status':'on_time'}, {**base, 'id':3, 'sla_configured':False}]
        feb = ext.monthly_dispatch(rows,2026)['months'][1]
        self.assertEqual((feb['completed'],feb['late'],feb['measured'],feb['late_pct']),(3,1,2,50))

    def test_external_label_preserves_zeroes(self):
        self.assertEqual(ext.external_delay_label('0007347'),'FA/0007347')
        self.assertEqual(ext.external_delay_label('FAC/7347'),'FA/7347')
        self.assertEqual(ext.external_delay_label('FA/7347'),'FA/7347')
        self.assertEqual(ext.external_delay_label(False),'FA/SIN NÚMERO EXTERNO')

    def test_full_dashboard_and_native_detail(self):
        rows, lines = data()
        rows[0].update(external_number='7347', name='FA 343475', completion_date='2026-01-06', sla_status='late', deadline='2026-01-04')
        filters = {'date_from':'2026-01-01','date_to':'2026-02-28'}
        svc = self.service(rows,lines)
        native = module.DispatchDashboard(); native.env = svc.env
        before = native.get_data(filters)
        after = svc.get_data(filters)
        self.assertEqual(before['stats'],after['stats'])
        item = after['timeliness']['delays']['completed']['top'][0]
        self.assertEqual(item['name'],'FA 343475')
        self.assertEqual(item['custom_external_label'],'FA/7347')
        self.assertEqual(after['monthly']['pending_total'],2)
        self.assertNotIn('monthly',svc.get_data(filters,False,True))

    def test_annual_independent_of_card_period(self):
        rows, lines = data(); svc = self.service(rows,lines)
        result = svc.get_data({'date_from':'2026-02-01','date_to':'2026-02-28'})
        self.assertEqual(result['stats']['total'],2)
        self.assertEqual(result['monthly']['months'][0]['completed'],1)
        self.assertEqual(result['monthly']['months'][1]['pending_accumulated'],2)

    def test_warehouse_scoping(self):
        rows, lines = data()
        raw = {'TipoFactura':'FA','NumeroFactura':'9','Ciudad':'GUAYAQUIL','Cond_Entrega':'Entrega Transcash', 'FechaFactura':'2025-12-31','Facturado':1,'DespachoFisico':1,'Pendiente':0,'UltimoDespacho':'2026-01-02'}
        rows[:] = [{**rows[1], 'id':9,'invoice_date':'2025-12-31','invoice_key':invoice_key(raw),'snapshot_id':[1,'Cut'],'warehouse_ids':[10,20],'line_dispatch_dates':['2026-01-02']}]
        lines[:] = [{'id':1,'invoice_id':[9,'FA'],'warehouse_id':[10,'A'],'raw_data':{**raw,'CodBodega':'10'}}, {'id':2,'invoice_id':[9,'FA'],'warehouse_id':[20,'B'],'raw_data':{**raw,'CodBodega':'20','DespachoFisico':0,'Pendiente':1,'UltimoDespacho':False}}]
        svc = self.service(rows,lines)
        svc.env.models['dispatch.snapshot'].browse = lambda ids: [SimpleNamespace(id=1,policy_pack={'rules':[{'max_days':3,'day_type':'calendar'}]})]
        one = svc._annual_statistics({'warehouse_ids':[10],'date_to':'2026-02-28'})
        both = svc._annual_statistics({'warehouse_ids':[10,20],'date_to':'2026-02-28'})
        self.assertEqual(one['months'][0]['completed'],1)
        self.assertEqual(both['completed_total'],0)

    def test_template_only_targets_delay_and_charts(self):
        native = etree.parse(str(BASE/'static/src/dashboard.xml'))
        extension = etree.parse(str(ROOT/'static/src/dashboard_extension.xml'))
        targets = extension.xpath('//xpath')
        self.assertEqual(len(targets),2)
        for target in targets:
            self.assertEqual(len(native.xpath(target.get('expr'))),1)
        self.assertEqual(extension.xpath('//attribute[@name="t-esc"]')[0].text,'invoice.custom_external_label || invoice.name')
        self.assertEqual(len(extension.xpath('//section[contains(@class,"td-monthly-panel")]')),2)
        self.assertNotIn('Acumulado =', (ROOT/'static/src/dashboard_extension.xml').read_text())

if __name__ == '__main__': unittest.main()
