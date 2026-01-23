/** @odoo-module **/

import { WebsiteSale } from "@website_sale/js/website_sale";
import { _t } from "@web/core/l10n/translation";

WebsiteSale.include({
    /**
     * @override
     */
    _updateRootProduct($form, productId, productTemplateId) {
        this._super(...arguments);
        if ($form.find('textarea[name="repair_note"]').length) {
            this.rootProduct['repair_note'] = $form.find('textarea[name="repair_note"]').val();
        }
    },

    /**
     * @override
     */
    _submitForm() {
        const params = this.rootProduct;
        if (params.repair_note !== undefined && params.repair_note.trim().length === 0) {
            alert(_t("Enter Repair Note"));
            return Promise.resolve(); // Stop execution
        }
        return this._super(...arguments);
    },
});