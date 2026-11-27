/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { DispatchDashboard } from "@transcash_dispatch_analysis/dashboard";

patch(DispatchDashboard.prototype, {
    setup() {
        this.preferenceSaveQueue = Promise.resolve();
        super.setup();
    },
    async initialize() {
        try {
            const [defaults, previous] = await Promise.all([
                this.orm.call("dispatch.dashboard", "get_default_filters", []),
                this.orm.call("dispatch.dashboard", "get_custom_active_filter_state", []),
            ]);
            this.state.filters = {...defaults, ...(previous?.filters || {})};
            // Opening a particular board from "Mis tableros" takes precedence.
            this.state.boardId = this.props.action?.params?.board_id || previous?.board_id || false;
            this.state.selectedFavorite = previous?.favorite_id ? String(previous.favorite_id) : "";
            await this.loadSavedFilters();
            const favorite = this.state.savedFilters.find(f => f.id === Number(this.state.selectedFavorite));
            this.state.selectedFavorite = favorite ? String(favorite.id) : "";
            this.state.favoriteName = favorite ? favorite.name : "";
            this.state.defaultsLoaded = true;
            await this.load();
        } catch (error) {
            this.state.loading = false;
            this.state.error = error.data?.message || error.message || "No fue posible cargar las fechas iniciales.";
        }
    },
    async saveFavorite() {
        try {
            if (!this.state.favoriteName.trim()) {
                this.notification.add("Escribe un nombre para guardar la vista.", {type: "warning"});
                return;
            }
            await this.load();
            if (!this.state.data) return;
            const saved = await this.orm.call("dispatch.dashboard", "save_dashboard_filter", [this.state.favoriteName, this.state.filters, this.state.boardId]);
            await this.loadSavedFilters();
            this.state.selectedFavorite = String(saved.id);
            await this.rememberActiveFilters();
            this.notification.add("Vista guardada en Favoritos de Odoo.", {type: "success"});
        } catch (error) {
            this.notification.add(error.data?.message || error.message, {type: "danger"});
        }
    },
    async loadFavorite() {
        const favorite = this.state.savedFilters.find(f => f.id === Number(this.state.selectedFavorite));
        if (!favorite) {
            // Removing the Favorite selection must also survive navigating away.
            this.state.favoriteName = "";
            await this.rememberActiveFilters();
            return;
        }
        // Dates belong to the current analysis, including open-ended ranges.
        // A saved view changes its other filters without replacing the period.
        const {date_from, date_to} = this.state.filters;
        this.state.filters = {...{source_id:"",snapshot_id:"",city:"",delivery:"",planning_scope:"transcash",planning_grouping:"warehouse",warehouse_ids:[]},
            ...JSON.parse(JSON.stringify(favorite.filters)), date_from, date_to};
        this.state.boardId = favorite.board_id || false;
        this.state.favoriteName = favorite.name;
        await this.load();
    },
    async rememberActiveFilters() {
        // Persist only the selection actually displayed, never unapplied edits.
        if (!this.state.appliedFilters) return;
        const filters = JSON.parse(JSON.stringify(this.state.appliedFilters));
        const boardId = this.state.boardId;
        const favoriteId = this.state.selectedFavorite || false;
        // Serialize writes so a slow earlier request cannot overwrite a newer view.
        this.preferenceSaveQueue = this.preferenceSaveQueue.catch(() => {}).then(() =>
            this.orm.call("dispatch.dashboard", "save_custom_active_filter_state", [filters, boardId, favoriteId]));
        try {
            await this.preferenceSaveQueue;
        } catch (error) {
            this.notification.add("No se pudieron conservar los filtros activos: " +
                (error.data?.message || error.message || "Error desconocido"), {type: "warning"});
        }
    },
    async load() {
        const request = ++this.requestNumber;
        this.state.loading = true;
        this.state.error = "";
        try {
            const filters = JSON.parse(JSON.stringify(this.state.filters));
            const data = await this.orm.call("dispatch.dashboard", "get_data", [filters, this.state.boardId]);
            if (request === this.requestNumber) {
                this.state.data = data;
                this.state.appliedFilters = filters;
                this.state.boardId = data.board_id;
                await this.rememberActiveFilters();
            }
        } catch (error) {
            if (request === this.requestNumber) {
                this.state.error = error.data?.message || error.message || "No fue posible cargar el tablero.";
                this.state.data = null;
            }
        } finally {
            if (request === this.requestNumber) this.state.loading = false;
        }
    },
    monthlyAxis(key) {
        const max = Math.max(1, ...this.state.data.monthly.months.map(m => m[key]));
        const raw = max / 4;
        const magnitude = 10 ** Math.floor(Math.log10(Math.max(1, raw)));
        const step = Math.max(1, [1, 2, 5, 10].find(n => n * magnitude >= raw) * magnitude);
        return {max: step * 4, ticks: Array.from({length: 5}, (_, i) => ({value: step * i, y: 228 - i * 48}))};
    },
    monthlyPoints(pending = false) {
        const axis = this.monthlyAxis(pending ? "pending_accumulated" : "completed");
        return this.state.data.monthly.months.map((month, i) => {
            const x = 82 + i * 69;
            const height = 192 * (pending ? month.pending_accumulated : month.completed) / axis.max;
            const newHeight = 192 * month.pending / axis.max;
            const y = 228 - height;
            const lateY = month.late_pct === null ? null : 228 - 192 * month.late_pct / 100;
            const lateLabelY = lateY === null ? null : Math.abs(y - 6 - (lateY - 12)) < 15
                ? Math.max(12, y - 24) : lateY - 12;
            return {...month, x, height, y, newHeight, lateY, lateLabelY};
        });
    },
    monthlyDelaySegments() {
        const segments = [];
        let points = [];
        for (const point of this.monthlyPoints()) {
            if (point.lateY === null) {
                if (points.length) segments.push(points.join(" "));
                points = [];
            } else points.push(`${point.x},${point.lateY}`);
        }
        if (points.length) segments.push(points.join(" "));
        return segments;
    },
    monthlyTooltip(point, pending = false) {
        if (pending) return `${point.label}: ${this.format(point.pending)} del mes + ${this.format(point.pending_accumulated - point.pending)} anteriores = ${this.format(point.pending_accumulated)} pendientes`;
        return `${point.label}: ${this.format(point.completed)} despachos completos · ${this.format(point.late)} demorados de ${this.format(point.measured)} evaluables · ${point.late_pct === null ? "Sin medición" : this.format(point.late_pct, 1) + "% de retraso"}`;
    },});
