/** @odoo-module **/

import { WebsiteSale } from "@website_sale/js/website_sale";
import { _t } from "@web/core/l10n/translation";

WebsiteSale.include({
    /**
     * @override
     */
    _updateRootProduct($form, productId, productTemplateId) {
        this._super(...arguments);
        if ($form.find('textarea[name="product_description"]').length) {
            this.rootProduct['product_description'] = $form.find('textarea[name="product_description"]').val();
        }
    },

    /**
     * @override
     */
    _submitForm() {
        const params = this.rootProduct;
        if (params.product_description !== undefined && params.product_description.trim().length === 0) {
            alert(_t("Enter Product Description"));
            return Promise.resolve(); // Stop execution
        }
        return this._super(...arguments);
    },
});