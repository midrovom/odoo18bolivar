/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import DynamicSnippet from "@website/snippets/s_dynamic_snippet/000";
import { utils as uiUtils } from "@web/core/ui/ui_service";

const DynamicSnippetCustom = DynamicSnippet.extend({
    selector: ".s_dynamic_snippet",  

    /**
     * @override
     * @private
     */
    _getQWebRenderOptions: function () {
        const dataset = this.el.dataset;
        const numberOfRecords = parseInt(dataset.numberOfRecords);

        let numberOfElements;
        if (uiUtils.isSmall()) {
            numberOfElements = parseInt(dataset.numberOfElementsSmallDevices) || 4;
        } else {
            numberOfElements = parseInt(dataset.numberOfElements) || 4;
        }

        const chunkSize = numberOfRecords < numberOfElements ? numberOfRecords : numberOfElements;

        return {
            chunkSize: chunkSize,
            data: this.data,
            unique_id: this.unique_id,
            extraClasses: dataset.extraClasses || '',
            columnClasses: dataset.columnClasses || '',
        };
    },
});

publicWidget.registry.dynamic_snippet = DynamicSnippetCustom;

export default DynamicSnippetCustom;
