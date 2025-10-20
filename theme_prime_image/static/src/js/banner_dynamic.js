odoo.define('theme_prime.banner_dynamic', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var qweb = require('web.core').qweb;

    publicWidget.registry.BannerDynamic = publicWidget.Widget.extend({
        selector: '.s_banner_dynamic',
        start: function () {
            var self = this;
            this._rpc({
                route: '/banner/products',
                params: { limit: 3 }
            }).then(function (data) {
                self.$el.html(qweb.render('s_banner_dynamic', { data: data }));
            });
        },
    });
});
