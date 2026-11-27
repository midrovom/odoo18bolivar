{
    "name": "Transcash · Análisis de despachos personalizado",
    "summary": "Filtros persistentes, estadísticas mensuales y referencia externa en mayores retrasos",
    "version": "18.0.1.0.3",
    "category": "Inventory/Reporting",
    "author": "Transcash",
    "license": "LGPL-3",
    "depends": ["transcash_dispatch_analysis"],
    "data": ["views/menu_icon.xml"],
    "assets": {
        "web.assets_backend": [
            "transcash_dispatch_analysis_custom/static/src/dashboard_patch.js",
            "transcash_dispatch_analysis_custom/static/src/dashboard_extension.xml",
            "transcash_dispatch_analysis_custom/static/src/dashboard_extension.scss",
        ],
    },
    "application": False,
    "installable": True,
}
