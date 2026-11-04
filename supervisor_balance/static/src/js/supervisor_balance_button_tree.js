/** @odoo-module **/
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SupervisorBalanceButtonTree extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
    }
    async buttonTreeClick() {
        await this.orm.call("balance.portfolio", "buttom_tree_balance_portfolio_all", []);
        await this.actionService.doAction({ type: "ir.actions.client", tag: "reload" });
    }
}

registry.category("views").add("supervisor_balance_tree_button", {
    ...listView,
    Controller: SupervisorBalanceButtonTree,
    buttonTemplate: "supervisor_balance.ListView.Buttons",
});
