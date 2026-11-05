/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { Component, useState, onWillStart, useRef, onMounted } from "@odoo/owl";

export class Zoomable extends Component {
    setup() {
        this.zoomRef = useRef("zoom");
        this.scale = 1;
        this.startDistance = 0;
        this.mounted = false;

        onMounted(() => {
            this.mounted = true;
        });
    }

    getDistance(touches) {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    onTouchStart(ev) {
        if (!this.mounted) return;

        if (ev.touches.length === 2) {
            this.startDistance = this.getDistance(ev.touches);
        }
    }

    onTouchMove(ev) {
        if (!this.mounted || !this.zoomRef.el) return;

        if (ev.touches.length === 2) {
            ev.preventDefault();

            const newDistance = this.getDistance(ev.touches);
            let scaleChange = newDistance / this.startDistance;

            this.scale *= scaleChange;
            this.scale = Math.max(0.5, Math.min(this.scale, 3));

            this.startDistance = newDistance;

            this.zoomRef.el.style.transform = `scale(${this.scale})`;
            this.zoomRef.el.style.transformOrigin = "0 0";
        }
    }

    onTouchEnd() {
        this.startDistance = 0;
    }
}

Zoomable.template = "sale_report.Zoomable";

export class KadoshcellReport extends Component {
    setup() {
        this.orm = useService("orm");

        // Obtener fecha actual
        const today = new Date();

        // Calcular primer día del mes actual
        const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);

        // Formatear a YYYY-MM-DD
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, "0");
            const day = String(date.getDate()).padStart(2, "0");
            return `${year}-${month}-${day}`;
        };

        this.state = useState({
            isLoading: false,
            date_from: formatDate(firstDayOfMonth), 
            date_to: formatDate(today),             
            tipo: "0",
            tipos: [],
            empresas: [],
            totales: {},
            empresasFiltro: [],
            empresasSeleccionadas: [],
        });

        onWillStart(async () => {
            await this.loadFilters();
        });
    }

    cleanName(name) {
        return (name || "")
            .toString()
            .trim()
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/-+/g, "-")
            .replace(/^-|-$/g, "");
    }

    async loadFilters() {
        const result = await this.orm.call(
            "json.sales.report",
            "get_filter_options",
            []
        );

        this.state.tipos = result.tipos || [];
        this.state.empresasFiltro = result.empresas || [];
    }

    onSelectEmpresa = (ev) => {
        const empresa = ev.target.value;

        if (!empresa) return;

        if (!this.state.empresasSeleccionadas.includes(empresa)) {
            this.state.empresasSeleccionadas.push(empresa);
        }

        ev.target.value = "";
    };

    removeEmpresa = (empresa) => {
        this.state.empresasSeleccionadas =
            this.state.empresasSeleccionadas.filter(e => e !== empresa);
    };

    async loadData() {
        this.state.isLoading = true;

        try {
            const result = await this.orm.call(
                "json.sales.report",
                "processed_data",
                [
                    this.state.date_from,
                    this.state.date_to,
                    this.state.tipo
                ]
            );

            let empresas = result.empresas || [];

            this.state.empresas = empresas;
            this.state.totales = result.totales_generales || {};

        } finally {
            this.state.isLoading = false;
        }
    }

    updateRanking = async () => {
        if (!this.state.date_from || !this.state.date_to) {
            alert("Debe seleccionar fechas");
            return;
        }
        await this.loadData();
    };
}

KadoshcellReport.template = "sale_report.SaleRankingReport";
KadoshcellReport.components = { Zoomable };

registry.category("actions").add("kadoshcell_report_client", KadoshcellReport);
