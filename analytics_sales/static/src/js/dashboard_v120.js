/** @odoo-module **/
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';
import { rpc } from '@web/core/network/rpc';
import { user } from '@web/core/user';
import { Component, onWillStart, onMounted, onWillUnmount, useState } from '@odoo/owl';

class AnalyticsSalesDashboard extends Component {
    setup() {
        this.orm = useService('orm');
        this.notification = useService('notification');
        this.action = useService('action');
        this.state = useState({
            loading: true, refreshing: false, syncing: false, guideOpen: false, period: 'year', error: '', data: null,
            openDropdown: '',
            nativeMenuAvailable: false, nativeMenuOpen: false,
            historyDays: 15,
            sort: 'sales',
            filters: {scope: '', establishment_id: 'all', local_id: 'all', line: 'all', brand: 'all', seller: 'all',
                      date_from: '', date_to: ''},
        });
        this.lastRequest = 0;
        // Al abrir (incluido F5), consultar Odoo una vez con una URL nueva.
        // Sin temporizadores, eventos de visibilidad ni consultas a la API externa.
        onWillStart(async () => { await this.loadData(); });
        // Sólo durante esta acción: en móvil se usa la cabecera comercial.
        // No se registran workers, cachés ni nuevas consultas.
        onMounted(() => {
            this.state.nativeMenuAvailable = Boolean(document.querySelector('.o_main_navbar'));
            if (this.state.nativeMenuAvailable) {
                document.body.classList.add('as-sales-mobile-shell');
            }
        });
        onWillUnmount(() => {
            document.body.classList.remove('as-sales-mobile-shell', 'as-sales-native-menu-open');
        });
    }
    onToggleNativeMenu() {
        if (!this.state.nativeMenuAvailable) return;
        this.state.openDropdown = '';
        this.state.nativeMenuOpen = !this.state.nativeMenuOpen;
        document.body.classList.toggle('as-sales-native-menu-open', this.state.nativeMenuOpen);
    }
    async loadData() {
        const token = ++this.lastRequest;
        this.state.refreshing = true;
        try {
            // RPC JSON nativo de Odoo 18: conserva la sesión y el contexto de
            // usuario/compañía del ORM. La URL única evita reutilizar respuestas
            // antiguas incluso si existe una caché HTTP intermedia.
            const requestId = `${Date.now()}-${token}-${Math.random().toString(36).slice(2)}`;
            const payload = await rpc(`/web/dataset/call_kw/analytics.sales.dashboard/get_dashboard/${requestId}`, {
                model: 'analytics.sales.dashboard',
                method: 'get_dashboard',
                args: [{...this.state.filters, period:this.state.period, history_days:this.state.historyDays}],
                kwargs: {context: {...user.context}},
            });
            if (token !== this.lastRequest) return;
            this.state.data = payload;
            this.state.filters.scope = payload.scope;
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
        const goal = this.goalProgress;
        const list = [
            {key:'goal_target', label:'Meta', val:goal.available ? this.money(goal.target) : 'Sin meta', detail:goal.available ? 'Metas mensuales definidas en Administración.' : 'Sin meta disponible para esta consulta', accent:'mint'},
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
        // Misma meta guardada en Administración -> Metas; para un local se
        // muestra expresamente el APORTE a la meta de su establecimiento.
        const completion = this.hasData ? this.state.data.goal_compliance_card : null;
        if (completion) {
            list.push({key:'goal_compliance',
                label:completion.label || 'Cumplimiento de meta',
                val:completion.available ? this.pct(completion.value) : 'Sin meta',
                detail:completion.detail || 'Sin meta asignada para este período',
                accent:'mint'});
        }
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
        const days = ev.currentTarget.value;
        if (!['month', 'previous_month', '30', '90', 'year'].includes(days) || this.state.period === days) return;
        this.state.period = days;
        // No congelar la fecha final: al llegar nuevas ventas por el cron,
        // el servidor calcula Mes actual y Mes anterior por calendario o mueve 30/90/Año.
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
            const warehouse = res.warehouse || {};
            const summary = `Movimientos de ventas: ${res.rows}; nuevos: ${res.created}; modificados: ${res.updated}. Bodegas: ${warehouse.rows || 0}; nuevas: ${warehouse.created || 0}; modificadas: ${warehouse.updated || 0}.`;
            if (res.error) {
                this.notification.add(`${summary} ${res.error}`, {title:'Actualización con errores', type:'danger', sticky:true});
            } else {
                this.notification.add(summary, {title:'Información actualizada',type:'success'});
            }
            // The RPC returns after Odoo has committed successful endpoints.
            // Even if one API failed, repaint with the other persisted data.
            await this.loadData();
        } catch (e) {
            this.notification.add((e.data && e.data.message) || e.message || 'No se pudo sincronizar', {title:'Error API',type:'danger',sticky:true});
        } finally { this.state.syncing = false; }
    }
    // El prototipo HTML es sólo una referencia visual. Los datos provienen del
    // backend de Odoo; los perfiles jamás se simulan en el navegador.
    get presentation() {
        return this.state.data?.presentation || {logo:'AS', logo_url:'', title:'Analytics Sales',
            subtitle:'INTELIGENCIA COMERCIAL', scope_name:'Líneas seleccionadas', scope_lines:[]};
    }
    get brandTitle() { return this.presentation.title; }
    get hasCustomScope() { return this.presentation.scope_lines.length > 0; }
    get scopeDescription() {
        return this.hasCustomScope
            ? `${this.presentation.scope_name} incluye: ${this.presentation.scope_lines.join(', ')}. Todas las líneas incluye todas las categorías disponibles.`
            : 'Todas las líneas incluye todas las categorías disponibles según los filtros y permisos del usuario.';
    }
    get dataSourceLabel() {
        if (!this.hasData) return 'Sin datos';
        return this.state.data.source === 'api' ? 'Información actualizada' : 'Histórico Excel';
    }
    get apiFreshnessLabel() {
        if (!this.hasData || this.state.data.source !== 'api') return '';
        const value = this.state.data.api_synced_at;
        if (!value) return 'API: sin sincronización confirmada';
        const utc = new Date(value.replace(' ', 'T') + 'Z');
        if (Number.isNaN(utc.getTime())) return 'Información actualizada';
        const formatter = new Intl.DateTimeFormat('es-EC', {
            timeZone: 'America/Guayaquil', day:'2-digit', month:'2-digit',
            year:'numeric', hour:'2-digit', minute:'2-digit', hour12:false,
        });
        return `Última actualización: ${formatter.format(utc)} (Ecuador)`;
    }
    get warehouseFreshnessLabel() {
        const data = this.hasData && this.state.data.warehouse_dashboard;
        if (!data || !data.updated_at) return '';
        const utc = new Date(data.updated_at.replace(' ', 'T') + 'Z');
        if (Number.isNaN(utc.getTime())) return '';
        const formatter = new Intl.DateTimeFormat('es-EC', {
            timeZone: 'America/Guayaquil', day:'2-digit', month:'2-digit',
            year:'numeric', hour:'2-digit', minute:'2-digit', hour12:false,
        });
        return `Última actualización de bodegas: ${formatter.format(utc)} (Ecuador)`;
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
    get sellerInvoices() { return this.top('sellers', (this.state.data.rankings.sellers || []).length, 'invoices'); }
    get productTable() { return this.top('models', 8, 'units'); }
    get storeTable() { return this.top('stores', 9, this.isAdmin ? 'profit' : 'sales'); }
    get storeOrSellerTable() {
        return this.isStore ? this.top('sellers', 9, 'sales') : this.storeTable;
    }
    get establishmentComparison() {
        if (!this.hasData) return [];
        // Una sola fila por establecimiento; el servidor agrega exclusivamente
        // los locales autorizados. El filtro de local no fragmenta este gráfico.
        const rows = this.state.data.establishment_comparison || [];
        return [...rows].sort((a,b) => b.sales - a.sales || a.name.localeCompare(b.name));
    }
    comparisonCompliance(row) {
        return row.goal_compliance == null ? 'Sin meta' : this.pct(row.goal_compliance);
    }
    get comparisonComplianceLabel() {
        return this.hasData && this.state.data.selected_establishment_id && this.state.data.selected_local_id
            ? 'Aporte a meta' : 'Cumplimiento';
    }
    comparisonGoalWidth(row) {
        // 100% del carril = la meta propia de cada establecimiento.
        // No simular progreso para filas sin una meta positiva.
        return this.width(row.sales, row.goal_target);
    }
    comparisonGoalAmount(row) {
        return row.goal_target > 0 ? this.money(row.goal_target) : 'Sin meta';
    }

    get goalProgress() {
        return this.hasData ? (this.state.data.goal_dashboard || {available:false, sellers:[]}) : {available:false, sellers:[]};
    }
    get goalSellers() {
        return this.goalProgress.available ? (this.goalProgress.sellers || []) : [];
    }
    goalProgressWidth(actual, target) {
        if (!(target > 0) || !(actual > 0)) return '0%';
        return Math.min(100, Math.max(0, 100 * actual / target)).toFixed(2) + '%';
    }
    get dailyHistory() {
        return this.hasData ? (this.state.data.daily_history || null) : null;
    }
    get dailyBars() {
        const info = this.dailyHistory;
        return info ? (info.history || []) : [];
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
    async onHistoryDays(ev) {
        const raw = Number(ev.currentTarget.value);
        if (!Number.isInteger(raw) || raw < 1 || raw > 90) {
            this.notification.add('Seleccione entre 1 y 90 días históricos.', {type:'warning'});
            ev.currentTarget.value = String(this.state.historyDays);
            return;
        }
        if (raw !== this.state.historyDays) {
            this.state.historyDays = raw;
            await this.loadData();
        }
    }
    get profitBrands() { return this.top('brands', (this.state.data.rankings.brands || []).length, 'profit'); }
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
        const rows = this.hasData ? (this.state.data.rankings.models || []) : [];
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
