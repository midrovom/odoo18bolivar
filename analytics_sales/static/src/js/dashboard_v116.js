/** @odoo-module **/
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { Component, onMounted, onWillStart, onWillUnmount, useState } from '@odoo/owl';

class AnalyticsSalesDashboard extends Component {
    setup() {
        this.orm = useService('orm');
        this.notification = useService('notification');
        this.action = useService('action');
        this.state = useState({
            loading: true, refreshing: false, syncing: false, guideOpen: false, period: 'year', error: '', data: null,
            openDropdown: '',
            projectionDays: 15,
            sort: 'sales',
            filters: {scope: 'moda', establishment_id: 'all', local_id: 'all', line: 'all', brand: 'all', seller: 'all',
                      date_from: '', date_to: ''},
        });
        this.lastRequest = 0;
        this.autoRefreshInterval = null;
        this.visibilityCallback = () => {
            if (document.visibilityState === 'visible' && !this.state.syncing && !this.state.refreshing) {
                this.loadData(true);
            }
        };
        onWillStart(async () => { await this.loadData(); });
        onMounted(() => {
            // Recargar datos YA SINCRONIZADOS cada dos minutos. No llama a API Administrator.
            // Los cron siguen siendo los únicos que consultan las APIs externas.
            this.autoRefreshInterval = window.setInterval(() => {
                if (document.visibilityState === 'visible' && !this.state.syncing && !this.state.refreshing) {
                    this.loadData(true);
                }
            }, 120000);
            document.addEventListener('visibilitychange', this.visibilityCallback);
        });
        onWillUnmount(() => {
            if (this.autoRefreshInterval !== null) window.clearInterval(this.autoRefreshInterval);
            document.removeEventListener('visibilitychange', this.visibilityCallback);
        });
    }
    async loadData(silent = false) {
        const token = ++this.lastRequest;
        if (!silent) this.state.refreshing = true;
        try {
            const payload = await this.orm.call('analytics.sales.dashboard', 'get_dashboard', [{...this.state.filters, period:this.state.period, projection_days:this.state.projectionDays}]);
            if (token !== this.lastRequest) return;
            this.state.data = payload;
            // Tienda nunca muestra un conjunto de locales; siempre refleja
            // el único nlocal devuelto/validado por el servidor.
            if (payload.role === 'tienda' && payload.selected_local_id) {
                this.state.filters.local_id = String(payload.selected_local_id);
            }
            this.state.error = '';
            if (!this.isAdmin && this.state.sort === 'profit') this.state.sort = 'sales';
        } catch (e) {
            if (token !== this.lastRequest) return;
            this.state.error = (e.data && e.data.message) || e.message || 'No fue posible obtener el dashboard.';
        } finally {
            if (token === this.lastRequest) {
                this.state.loading = false;
                this.state.refreshing = false;
            }
        }
    }
    get hasData() { return Boolean(this.state.data); }
    get isAdmin() { return this.hasData && this.state.data.role === 'administrador'; }
    get isStore() { return this.hasData && this.state.data.role === 'tienda'; }
    get isSupervisor() { return this.hasData && this.state.data.role === 'supervisor'; }
    get roleClass() { return this.hasData ? `as-profile-${this.state.data.role}` : ''; }
    get selectedLocalName() {
        if (!this.hasData) return '';
        const id = String(this.state.data.selected_local_id || this.state.filters.local_id);
        const local = this.state.data.options.locals.find(item => String(item.id) === id);
        return local ? local.name : 'el local asignado';
    }
    get profileLabel() {
        if (this.isStore) return `TIENDA · ${this.selectedLocalName}`;
        return this.isSupervisor ? 'SUPERVISOR' : 'ADMINISTRADOR';
    }
    isLocalSelected(localId) { return String(localId) === String(this.state.filters.local_id); }
    get title() {
        if (!this.hasData) return 'Analytics Sales';
        return {'administrador': 'Panel de rentabilidad', 'supervisor': 'Panel de supervisión', 'tienda': 'Panel de mi tienda'}[this.state.data.role] || 'Analytics Sales';
    }
    get subtitle() {
        return this.isAdmin ? 'Control integral de ventas, devoluciones, costos, margen bruto y desempeño de todo el negocio.' :
            this.isStore ? 'Consulta exclusivamente ventas, unidades, devoluciones, marcas y vendedores de tu local autorizado.' :
            'Monitorea las ventas, unidades, devoluciones y productividad de los locales a tu cargo, sin información de costos.';
    }
    // Menús propios del dashboard: fondo y texto oscuros de manera uniforme,
    // también donde el sistema operativo ignora los estilos de <option>.
    filterTitle(field) {
        const names = {establishment_id:'Establecimiento', local_id:'Local (nlocal)', line:'Línea de productos', brand:'Marca', seller:'Vendedor'};
        return names[field] || field;
    }
    filterValue(field) {
        if (!this.hasData) return '';
        const value = String(this.state.filters[field] || 'all');
        const labels = {establishment_id:'Todos los establecimientos', local_id:'Todos los autorizados', line:'Todas las líneas', brand:'Todas las marcas', seller:'Todos los vendedores'};
        if (field === 'establishment_id') {
            const item = (this.state.data.options.establishments || []).find(x => String(x.id) === value);
            return item ? item.name : labels[field];
        }
        if (field === 'local_id') {
            const item = this.state.data.options.locals.find(x => String(x.id) === value);
            return item ? item.name : labels[field];
        }
        return value === 'all' ? labels[field] : value;
    }
    get filterFields() {
        if (!this.hasData) return [];
        const opt = this.state.data.options;
        const establishments = opt.establishments || [];
        const selected = establishments.find(x => String(x.id) === String(this.state.filters.establishment_id));
        const localOptions = selected ? opt.locals.filter(x => selected.local_ids.includes(x.id)) : opt.locals;
        return [
            {key:'establishment_id', title:'Establecimiento', all:'Todos los establecimientos',
             choices:establishments.map(x => ({value:String(x.id),label:x.name})), allowAll:true, disabled:false},
            {key:'local_id', title:'Local (nlocal)', all:'Todos los autorizados',
             choices:localOptions.map(x => ({value:String(x.id),label:x.name})), allowAll:!this.isStore, disabled:this.isStore && localOptions.length <= 1},
            {key:'line', title:'Línea de productos', all:'Todas las líneas', choices:opt.lines.map(x => ({value:x,label:x})), allowAll:true, disabled:false},
            {key:'brand', title:'Marca', all:'Todas las marcas', choices:opt.brands.map(x => ({value:x,label:x})), allowAll:true, disabled:false},
            {key:'seller', title:'Vendedor', all:'Todos los vendedores', choices:opt.sellers.map(x => ({value:x,label:x})), allowAll:true, disabled:false},
        ];
    }
    onDropdownToggle(ev) {
        const field = ev.currentTarget.dataset.field;
        if (field === 'local_id' && this.isStore && this.state.data.options.locals.length <= 1) return;
        this.state.openDropdown = this.state.openDropdown === field ? '' : field;
    }
    async onDropdownChoose(ev) {
        const {field, value} = ev.currentTarget.dataset;
        if (!Object.prototype.hasOwnProperty.call(this.state.filters, field)) return;
        this.state.openDropdown = '';
        if (String(this.state.filters[field]) === value) return;
        this.state.filters[field] = value;
        if (field === 'establishment_id') this.state.filters.local_id = 'all';
        await this.loadData();
    }
    onDropdownDismiss() { this.state.openDropdown = ''; }
    onDropdownKeydown(ev) {
        if (ev.key === 'Escape') { ev.preventDefault(); this.state.openDropdown = ''; return; }
        if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
        const options = [...ev.currentTarget.querySelectorAll('.as-dropdown-option')];
        if (!options.length) return;
        ev.preventDefault();
        const index = options.indexOf(ev.target);
        const direction = ev.key === 'ArrowDown' ? 1 : -1;
        const next = index < 0 ? (direction > 0 ? 0 : options.length - 1) : (index + direction + options.length) % options.length;
        options[next].focus();
    }
    money(x) { return x == null ? 'N/D' : new Intl.NumberFormat('es-EC', {style:'currency',currency:'USD',maximumFractionDigits:2}).format(x || 0); }
    num(x) { return x == null ? 'N/D' : new Intl.NumberFormat('es-EC', {maximumFractionDigits:2}).format(x || 0); }
    pct(x) { return x == null ? 'N/D' : `${this.num(x)}%`; }
    get cards() {
        const m = this.hasData ? this.state.data.metrics : {};
        const list = [
            {key:'invoices', label:'Facturas FA únicas', val:this.num(m.invoices), detail:'Sin duplicar líneas de factura', accent:'violet'},
            {key:'fa_sales', label:'Facturado FA', val:this.money(m.fa_sales), detail:'Importe de venta antes de devoluciones', accent:'sky'},
            {key:'de_sales', label:'Devuelto DE', val:this.money(m.de_sales), detail:'Importe de notas de devolución', accent:'pink'},
            {key:'sales', label:'Venta neta', val:this.money(m.sales), detail:'Facturado FA menos devuelto DE', accent:'mint'},
            {key:'units', label:'Unidades netas', val:this.num(m.units), detail:'Unidades FA − unidades DE', accent:'sky'},
            {key:'ticket', label:'Ticket promedio FA', val:this.money(m.ticket), detail:'Facturado FA / facturas únicas', accent:'amber'},
            {key:'fa_units', label:'Unidades FA', val:this.num(m.fa_units), detail:'Antes de devoluciones', accent:'sky'},
            {key:'de_units', label:'Unidades DE', val:this.num(m.de_units), detail:'Unidades devueltas', accent:'pink'},
            {key:'units_per_invoice', label:'Unidades por factura', val:this.num(m.units_per_invoice), detail:'Unidades FA / facturas FA', accent:'violet'},
            {key:'credit_notes', label:'Notas DE únicas', val:this.num(m.credit_notes), detail:this.money(m.de_sales)+' en devoluciones', accent:'pink'},
            {key:'return_rate', label:'Tasa devolución (valor)', val:this.pct(m.return_rate), detail:'DE / ventas brutas FA', accent:'pink'},
        ];
        if (this.isAdmin) list.push(
            {key:'profit', label:'Utilidad bruta', val:this.money(m.profit), detail:'Ventas netas − costo neto', accent:'amber'},
            {key:'margin', label:'Margen bruto', val:this.pct(m.margin), detail:'Utilidad / ventas netas', accent:'mint'},
            {key:'cost', label:'Costo neto', val:this.money(m.cost), detail:'Exclusivo administración', accent:'violet'}
        );
        return list;
    }
    rows(dim) {
        if (!this.hasData) return [];
        const source = (this.state.data.rankings || {})[dim] || [];
        const key = this.isAdmin || this.state.sort !== 'profit' ? this.state.sort : 'sales';
        return [...source].sort((a,b) => (b[key] ?? -Infinity) - (a[key] ?? -Infinity) || b.sales - a.sales).slice(0, dim === 'products' ? 12 : 10);
    }
    maxFor(dim) { return Math.max(1, ...this.rows(dim).map(r => Math.max(0, r[this.state.sort] || 0))); }
    barWidth(row, dim) { return `${Math.max(1, 100 * Math.max(0, row[this.state.sort] || 0) / this.maxFor(dim)).toFixed(2)}%`; }
    metricForSort(row) {
        const key = this.state.sort;
        return ['sales','profit'].includes(key) ? this.money(row[key]) : this.num(row[key]);
    }
    async onFilterChange(ev) {
        const field = ev.currentTarget.dataset.field;
        if (!(field in this.state.filters)) return;
        if (field === 'date_from' || field === 'date_to') {
            // Al elegir manualmente fechas fijar el otro límite visible,
            // evitando que el rango salte al recargar desde el servidor.
            if (this.state.period !== 'custom' && this.hasData) {
                this.state.filters.date_from = this.state.data.date_from;
                this.state.filters.date_to = this.state.data.date_to;
            }
            this.state.period = 'custom';
        }
        this.state.filters[field] = ev.currentTarget.value;
        if (field === 'establishment_id') this.state.filters.local_id = 'all';
        await this.loadData();
    }
    async onScope(ev) {
        this.state.filters.scope = ev.currentTarget.dataset.scope;
        this.state.filters.line = 'all'; this.state.filters.brand = 'all';
        this.state.filters.seller = 'all';
        await this.loadData();
    }
    async onPeriod(ev) {
        const days = ev.currentTarget.dataset.days;
        this.state.period = days;
        // No congelar la fecha final: al llegar nuevas ventas por el cron,
        // el servidor mueve automáticamente la ventana 30/90/Año.
        this.state.filters.date_from = '';
        this.state.filters.date_to = '';
        await this.loadData();
    }
    onSort(ev) { this.state.sort = ev.currentTarget.value; }
    async onSync() {
        if (!this.isAdmin || this.state.syncing) return;
        this.state.syncing = true;
        try {
            const res = await this.orm.call('analytics.sales.sync', 'action_sync_now', []);
            if (res.error) {
                this.notification.add(res.error, {title:'Error de sincronización', type:'danger', sticky:true});
            } else {
                this.notification.add(`Movimientos: ${res.rows}; nuevos: ${res.created}; modificados: ${res.updated}.`, {title:'Sincronización realizada',type:'success'});
                await this.loadData();
            }
        } catch (e) {
            this.notification.add((e.data && e.data.message) || e.message || 'No se pudo sincronizar', {title:'Error API',type:'danger',sticky:true});
        } finally { this.state.syncing = false; }
    }
    // El prototipo HTML es sólo una referencia visual. Los datos provienen del
    // backend de Odoo; los perfiles jamás se simulan en el navegador.
    get brandTitle() { return 'IDR MODA'; }
    get dataSourceLabel() {
        if (!this.hasData) return 'Sin datos';
        return this.state.data.source === 'api' ? 'API sincronizada' : 'Histórico Excel';
    }
    get apiFreshnessLabel() {
        if (!this.hasData || this.state.data.source !== 'api') return '';
        const value = this.state.data.api_synced_at;
        if (!value) return 'API: sin sincronización confirmada';
        const utc = new Date(value.replace(' ', 'T') + 'Z');
        if (Number.isNaN(utc.getTime())) return 'API sincronizada';
        const formatter = new Intl.DateTimeFormat('es-EC', {
            timeZone: 'America/Guayaquil', day:'2-digit', month:'2-digit',
            year:'numeric', hour:'2-digit', minute:'2-digit', hour12:false,
        });
        return `Última sincronización: ${formatter.format(utc)} (Ecuador)`;
    }
    get periodDays() {
        if (!this.hasData) return 1;
        const a = new Date(this.state.data.date_from + 'T12:00:00');
        const b = new Date(this.state.data.date_to + 'T12:00:00');
        const days = Math.round((b.getTime() - a.getTime()) / 86400000) + 1;
        return Number.isFinite(days) ? Math.max(1, days) : 1;
    }
    top(dim, count=8, key='sales') {
        const rows = this.hasData ? (this.state.data.rankings[dim] || []) : [];
        return [...rows].sort((a,b) => (b[key] || 0) - (a[key] || 0) || a.name.localeCompare(b.name)).slice(0,count);
    }
    width(value, topValue) {
        if (!(topValue > 0) || !(value > 0)) return '0%';
        return Math.min(100, Math.max(0, 100 * value / topValue)).toFixed(2) + '%';
    }
    get salesLines() { return this.top('lines', 8); }
    get salesBrands() { return this.top('brands', 7); }
    get salesSellers() { return this.top('sellers', 5); }
    get velocityProducts() { return this.top('products', 7, 'velocity'); }
    get sellerInvoices() { return this.top('sellers', 8, 'invoices'); }
    get productTable() { return this.top('products', 8, 'units'); }
    get storeTable() { return this.top('stores', 9, this.isAdmin ? 'profit' : 'sales'); }
    get storeOrSellerTable() {
        return this.isStore ? this.top('sellers', 9, 'sales') : this.storeTable;
    }
    get localComparison() {
        if (!this.hasData) return [];
        const dimension = this.isStore ? 'sellers' : 'stores';
        const rows = this.state.data.rankings[dimension] || [];
        return [...rows].sort((a,b) => b.sales - a.sales || a.name.localeCompare(b.name));
    }
    get maxLocalSales() { return Math.max(1, ...this.localComparison.map(r => Math.max(0, r.sales || 0))); }
    get dailyProjection() {
        return this.hasData ? (this.state.data.daily_projection || null) : null;
    }
    get dailyBars() {
        const info = this.dailyProjection;
        if (!info) return [];
        return [...(info.history || []).map(x => ({...x, projected:false})),
                ...(info.forecast || []).map(x => ({...x, projected:true}))];
    }
    get maxDailyValue() {
        return Math.max(1, ...this.dailyBars.map(x => Math.abs(x.sales || 0)));
    }
    dailyBarHeight(value) {
        return Math.max(2, Math.round(165 * Math.abs(value || 0) / this.maxDailyValue)) + 'px';
    }
    dayShort(value) {
        return value ? value.slice(8,10) + '/' + value.slice(5,7) : '';
    }
    async onProjectionDays(ev) {
        const raw = Number(ev.currentTarget.value);
        if (!Number.isInteger(raw) || raw < 1 || raw > 90) {
            this.notification.add('Seleccione entre 1 y 90 días.', {type:'warning'});
            ev.currentTarget.value = String(this.state.projectionDays);
            return;
        }
        if (raw !== this.state.projectionDays) {
            this.state.projectionDays = raw;
            await this.loadData();
        }
    }
    get profitBrands() { return this.top('brands', 8, 'profit'); }
    get returnLines() {
        const data = this.hasData ? (this.state.data.rankings.lines || []) : [];
        return [...data].filter(x => x.de_sales > 0).sort((a,b) => (b.return_rate || 0) - (a.return_rate || 0)).slice(0,7);
    }
    get trendPlot() {
        const series = this.hasData ? (this.state.data.trend || []) : [];
        if (!series.length) return null;
        const max = Math.max(1, ...series.map(x => Math.max(0, x.fa_sales || 0, x.de_sales || 0)));
        const x = i => series.length === 1 ? 338 : 38 + i * 598 / (series.length - 1);
        const y = v => 196 - Math.max(0, v || 0) / max * 172;
        const fa = series.map((p,i) => ({x:x(i), y:y(p.fa_sales), label:p.month, value:p.fa_sales}));
        const de = series.map((p,i) => ({x:x(i), y:y(p.de_sales), label:p.month, value:p.de_sales}));
        const path = arr => arr.map((p,i) => `${i ? 'L' : 'M'}${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ');
        return {fa, de, faPath:path(fa), dePath:path(de), area:`${path(fa)} L${fa[fa.length-1].x},196 L${fa[0].x},196 Z`,
                axis: [0,0.25,0.5,0.75,1].map(v => ({y:y(max*v), value:max*v})),
                labels:series.map((p,i) => ({x:x(i), name:p.month.slice(5) + '/' + p.month.slice(2,4)}))};
    }
    get invoiceMonths() { return this.hasData ? (this.state.data.trend || []) : []; }
    get maxInvoices() { return Math.max(1, ...this.invoiceMonths.map(x => x.invoices || 0)); }
    get abcBreakdown() {
        const rows = this.hasData ? (this.state.data.rankings.products || []) : [];
        const labels = ['A','B','C'];
        const total = rows.reduce((n,r) => n + Math.max(0,r.sales || 0),0);
        return labels.map(label => {
            const group = rows.filter(r => r.abc === label);
            const amount = group.reduce((n,r) => n + Math.max(0,r.sales || 0), 0);
            return {label, products:group.length, sales:amount, share:total ? amount*100/total : 0};
        });
    }
    get decisions() {
        if (!this.hasData) return [];
        const m = this.state.data.metrics;
        const sellers = this.top('sellers',1,'invoices');
        const ret = this.top('lines',1,'de_sales').filter(x => x.de_sales > 0);
        const items = [];
        if (ret.length) items.push({kind:'warn', label:'Revisar devoluciones', title:this.isStore ? 'Tu local · ' + this.selectedLocalName : ret[0].name,
            detail:`${this.money(ret[0].de_sales)} en notas DE; verificar motivos y fechas originales.`});
        if (sellers.length) items.push({kind:'good',label:'Productividad comercial',title:sellers[0].name,
            detail:`${this.num(sellers[0].invoices)} facturas FA · ${this.money(sellers[0].sales)} en ventas netas.`});
        if (this.isAdmin && this.hasCompleteCosts) {
            const best = this.top('stores', 1, 'profit')[0];
            if (best) items.push({kind:'good',label:'Utilidad del local',title:best.name,
                detail:`${this.money(best.profit)} de utilidad bruta en el filtro actual.`});
        } else {
            items.push({kind:'',label:'Calidad de facturación',title:`${this.num(m.invoices)} facturas únicas`,
                detail:`${this.num(m.credit_notes)} notas DE · ${this.pct(m.return_rate)} del importe FA. Una factura con varios SKU cuenta una vez.`});
        }
        return items;
    }
    get breakdown() {
        if (!this.hasData) return [];
        const m = this.state.data.metrics;
        return [{label:'Facturación FA', value:m.fa_sales, accent:'mint'},
                {label:'Devoluciones DE', value:m.de_sales, accent:'pink'},
                {label:'Venta neta',value:m.sales,accent:'violet'}];
    }
    get roleInsights() {
        if (!this.hasData) return [];
        const source = this.state.data.insights || [];
        if (this.isStore) return source.filter(x => !/Local líder|Mayor utilidad|Calidad de costos/i.test(x.label)).slice(0,3);
        if (this.isSupervisor) return source.filter(x => !/Mayor utilidad|Calidad de costos/i.test(x.label)).slice(0,3);
        // Gerencia: priorizar el hallazgo de rentabilidad del HTML cuando
        // los costos están completos y ese indicador viene del backend.
        const profitability = source.find(x => x.label === 'Mayor utilidad bruta');
        return profitability ? [profitability, ...source.filter(x => x !== profitability)].slice(0,3) : source.slice(0,3);
    }
    get hasCompleteCosts() { return this.isAdmin && Boolean(this.state.data.metrics.cost_complete); }
    async onSelectLine(ev) {
        const line = ev.currentTarget.dataset.line;
        this.state.filters.line = this.state.filters.line === line ? 'all' : line;
        this.state.filters.brand = 'all'; this.state.filters.seller = 'all';
        await this.loadData();
    }
    async onImport() {
        if (!this.isAdmin) return;
        await this.action.doAction('analytics_sales.action_analytics_sales_excel_import', {
            onClose: () => { this.loadData(); },
        });
    }
    onGuide() { this.state.guideOpen = true; }
    onCloseGuide() { this.state.guideOpen = false; }
    onExport() {
        if (!this.hasData) return;
        const heads = ['Grupo','Nombre','Facturas FA','Unidades FA','Unidades DE','Unidades netas','Venta FA','Devoluciones DE','Venta neta','Ticket FA','Unidades por factura'];
        if (this.isAdmin) heads.push('Costo neto','Utilidad','Margen %');
        const output = [heads];
        for (const kind of ['stores','lines','brands','sellers','products']) {
            for (const item of (this.state.data.rankings[kind] || [])) {
                const rec = [kind,item.name,item.invoices,item.fa_units,item.de_units,item.units,item.fa_sales,item.de_sales,item.sales,item.ticket,item.units_per_invoice];
                if (this.isAdmin) rec.push(item.cost,item.profit,item.margin);
                output.push(rec);
            }
        }
        const csv = '\ufeff' + output.map(x=>x.map(v=>'"'+String(v ?? '').replace(/"/g,'""')+'"').join(';')).join('\r\n');
        const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
        const a=document.createElement('a');a.href=url;a.download='Analytics_Sales_Analisis_'+new Date().toISOString().slice(0,10)+'.csv';a.click();
        URL.revokeObjectURL(url);
    }
}
AnalyticsSalesDashboard.template = 'analytics_sales.Dashboard';
registry.category('actions').add('analytics_sales.Dashboard', AnalyticsSalesDashboard);
