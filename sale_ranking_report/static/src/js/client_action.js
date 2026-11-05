/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useDebounced } from "@web/core/utils/timing";
import { Component, onWillStart, useState, onMounted, useRef } from "@odoo/owl";

export class SaleRankingReportMain extends Component {
    setup() {
        // this.localSearchValue = "";
        this.orm = useService("orm");
        this.user = useService("user");
        this.dialogService = useService("dialog");
        this.state = useState({
            rows: { marcas: [], meses: [], clientes: [], totales: {}, total_general: 0 },
            isLoading: true,
            availableUsers: [], // Lista de usuarios disponibles
            selectedUser: false, // Usuario seleccionado (false para todos)
            showUserSearch: false,
            showUserDropdown: false,
            search: "",
            activeUserIndex: -1
        });

        this.searchInput = useRef("input");

        this.debouncedFilterUsers = useDebounced(() => {
            const value = this.searchInput.el.value;
            this.state.search = value;
            this.filterUsers();
        }, 250);

        onWillStart(async () => {
            await this.loadUsers();
            await this.isNotAdmin();
        });

        onMounted(async () => {
            await this.loadData();
        });

    }

    // debounce(func, wait) {
    //     let timeout;
    //     return function (...args) {
    //         clearTimeout(timeout);
    //         timeout = setTimeout(() => func.apply(this, args), wait);
    //     };
    // }

    async isNotAdmin() {
        try {
            const result = await this.orm.call(
                "sale.ranking.report",
                "is_not_user_admin",
                []
            );
            this.state.showUserSearch = result;
        } catch (error) {
            console.error("Error validated admin:", error);
        }
    }


    async loadUsers() {
        try {
            this.state.isLoadingUsers = true;
            const users = await this.orm.searchRead(
                "res.users",
                [["active", "=", true], ["balance_code", "!=", false]],
                ["id", "name", "balance_code"],
                { limit: 100 } // Limitar inicialmente
            );
            this.state.availableUsers = users.map(user => ({
                id: user.id,
                name: user.name,
                balanceCode: user.balance_code
            }));
        } catch (error) {
            console.error("Error loading users:", error);
        } finally {
            this.state.isLoadingUsers = false;
        }
    }

    async loadData(userCode = false) {
        this.state.isLoading = true;
        try {
            const result = await this.orm.call(
                "sale.ranking.report",
                "processed_data",
                [userCode] // Pasamos el balanceCode del usuario como parámetro
            );
            this.state.rows = result;
        } catch (error) {
            console.error("Error loading data:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    onInputFocus() {
        this.state.isDropdownOpen = true;
        this.filterUsers();
    }

    onInputBlur() {
        setTimeout(() => {
            this.state.isDropdownOpen = false;
            this.state.activeUserIndex = -1;
        }, 200);
    }

    filterUsers() {
        const searchTerm = this.state.search.toLowerCase();
        if (!searchTerm) {
            this.state.filteredUsers = [...this.state.availableUsers];
        } else {
            this.state.filteredUsers = this.state.availableUsers.filter(user =>
                user.name.toLowerCase().includes(searchTerm) ||
                (user.balanceCode && user.balanceCode.toLowerCase().includes(searchTerm))
            );
        }
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value;
        this.state.isDropdownOpen = true;
        this.debouncedFilterUsers();  // Aquí invocas el debounce
    }

    onSelectUser(user) {
        if (user) {
            this.state.selectedUser = user.balanceCode;
            this.state.search = user.name;
        } else {
            this.state.selectedUser = false;
            this.state.search = "";
        }

        this.searchInput.el.value = this.state.search;
        this.state.isDropdownOpen = false;
        this.loadData(this.state.selectedUser);
    }

    onInputKeydown(ev) {
        switch (ev.key) {
            case "ArrowDown":
                ev.preventDefault();
                if (this.state.activeUserIndex < this.state.filteredUsers.length - 1) {
                    this.state.activeUserIndex++;
                }
                break;
            case "ArrowUp":
                ev.preventDefault();
                if (this.state.activeUserIndex > 0) {
                    this.state.activeUserIndex--;
                }
                break;
            case "Enter":
                ev.preventDefault();
                if (this.state.filteredUsers[this.state.activeUserIndex]) {
                    this.onSelectUser(this.state.filteredUsers[this.state.activeUserIndex]);
                }
                break;
            case "Escape":
                this.state.isDropdownOpen = false;
                break;
        }
    }


    onSearchUser() {
        const searchName = this.state.search.trim();
        
        // Si está vacío, mostrar todos
        if (!searchName) {
            this.onSelectUser(null);
            return;
        }

        // Buscar coincidencias (optimizado)
        const searchLower = searchName.toLowerCase();
        const userFound = this.state.availableUsers.find(user => 
            user.name.toLowerCase().includes(searchLower)
        );

        if (userFound) {
            this.onSelectUser(userFound);
        } else if (searchName.length > 2) { // Solo mostrar error si hay suficiente texto
            this.showAlert();
            this.onSelectUser(null);
        }
    }


    showAlert() {
        this.dialogService.add(AlertDialog, {
            title: "¡Error de Validacion!",
            body: "No se encontró ningún vendedor.",
        });
    }

    async updateRanking() {
        const vendorRef = this.searchInput.el?.value || "";
        if (!vendorRef) {
            this.state.selectedUser = false;
        }
        await this.loadData(this.state.selectedUser);
    }

    async clearSearch() {
        this.state.search = "";
        this.searchInput.el.value = "";
        await this.loadData();
    }
}

SaleRankingReportMain.template = "sale_ranking_report.SaleRankingReportMain";

registry.category("actions").add("sale_ranking_report_client", SaleRankingReportMain);
