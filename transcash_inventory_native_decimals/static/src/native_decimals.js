/**
 * Standalone Transcash iframe locale bridge for Odoo 18.
 *
 * Transcash 18.0.1.51 uses hard-coded Intl.NumberFormat('es-EC') in its own
 * non-module JS. We adapt only that exact locale INSIDE these iframes.
 * The parent Odoo window, all other applications, and the raw data are
 * untouched. The real separators/grouping are supplied from res.lang.
 */
(function () {
    'use strict';

    const meta = document.querySelector('meta[name="transcash-native-decimals"]');
    if (!meta) return;
    let cfg;
    try { cfg = JSON.parse(meta.content); }
    catch (error) { console.warn('TRANSCASH: configuración decimal no válida', error); return; }

    const decimalPoint = typeof cfg.decimal_point === 'string' && cfg.decimal_point
        ? cfg.decimal_point : '.';
    const thousandsSep = typeof cfg.thousands_sep === 'string' ? cfg.thousands_sep : '';
    const grouping = Array.isArray(cfg.grouping) && cfg.grouping.every(
        n => Number.isInteger(n) && n >= -1 && n <= 9
    ) ? cfg.grouping : [3, 0];

    // No grouping for [] or an empty thousands separator. Implement Odoo's
    // grouping semantics: [3,0] -> 1.234.567; [3,2,0] -> 12,34,567;
    // -1 stops grouping remaining digits.
    function splitGroups(integer) {
        if (!thousandsSep || !grouping.length || integer.length < 2) return [integer];
        const result = [];
        let position = integer.length;
        let index = 0;
        let previousWidth = 0;
        let repeat = false;
        while (position > 0) {
            let width;
            if (repeat) {
                width = previousWidth;
            } else if (index < grouping.length) {
                const group = grouping[index++];
                if (group === -1) { result.unshift(integer.slice(0, position)); break; }
                if (group === 0) {
                    if (!previousWidth) { result.unshift(integer.slice(0, position)); break; }
                    width = previousWidth;
                    repeat = true;
                } else {
                    width = previousWidth = group;
                }
            } else {
                result.unshift(integer.slice(0, position));
                break;
            }
            if (!width) { result.unshift(integer.slice(0, position)); break; }
            const start = Math.max(0, position - width);
            result.unshift(integer.slice(start, position));
            position = start;
        }
        return result;
    }

    const NativeNumberFormat = Intl.NumberFormat;
    const nativeNumberToLocaleString = Number.prototype.toLocaleString;

    // Native Intl performs rounding, decimal precision, sign handling,
    // NaN/Infinity, etc. Only the separators/grouping are changed.
    function localizedParts(nativeNoGrouping, value) {
        const parts = nativeNoGrouping.formatToParts(value);
        const output = [];
        for (const part of parts) {
            if (part.type === 'integer') {
                const groups = splitGroups(part.value);
                groups.forEach((digits, idx) => {
                    if (idx) output.push({ type: 'group', value: thousandsSep });
                    output.push({ type: 'integer', value: digits });
                });
            } else if (part.type === 'decimal') {
                output.push({ type: 'decimal', value: decimalPoint });
            } else {
                output.push(part);
            }
        }
        return output;
    }

    function needsOdooLocale(locales) {
        return locales === 'es-EC' || (Array.isArray(locales) && locales.length === 1 && locales[0] === 'es-EC');
    }

    function nativeWrapper(instance, options) {
        // These Transcash screens use decimal formatting, not currency style.
        // Use a neutral locale only as a numeric precision/rounding engine.
        const raw = new NativeNumberFormat('en-US', { ...(options || {}), useGrouping: false });
        const ownFormat = value => localizedParts(raw, value).map(p => p.value).join('');
        const ownParts = value => localizedParts(raw, value);
        return new Proxy(instance, {
            get(target, property) {
                if (property === 'format') return ownFormat;
                if (property === 'formatToParts') return ownParts;
                const value = Reflect.get(target, property, target);
                return typeof value === 'function' ? value.bind(target) : value;
            },
        });
    }

    Intl.NumberFormat = new Proxy(NativeNumberFormat, {
        construct(target, args) {
            const instance = Reflect.construct(target, args);
            return needsOdooLocale(args[0]) ? nativeWrapper(instance, args[1]) : instance;
        },
        apply(target, thisArg, args) {
            const instance = Reflect.apply(target, thisArg, args);
            return needsOdooLocale(args[0]) ? nativeWrapper(instance, args[1]) : instance;
        },
    });

    // upload.js also calls Number.toLocaleString('es-EC') directly.
    Object.defineProperty(Number.prototype, 'toLocaleString', {
        configurable: true,
        writable: true,
        value: function (locales, options) {
            if (needsOdooLocale(locales)) {
                return new Intl.NumberFormat(locales, options).format(Number(this));
            }
            return nativeNumberToLocaleString.apply(this, arguments);
        },
    });

    // Original CSV numeric columns are serialized with toFixed('.') despite
    // the display configuration. Adapt ONLY this known Transcash CSV format,
    // retaining semicolon column delimiters and leaving text fields untouched.
    // No thousands separators in CSV, so Excel can interpret values as numbers.
    const isDashboard = window.location.pathname === '/transcash_inventory/dashboard';
    if (isDashboard && decimalPoint !== '.') {
        const NativeBlob = window.Blob;
        const numericColumns = new Set([6, 7, 8, 9, 16, 17, 18, 19, 20, 22, 23, 24]);
        function localizeCsv(content) {
            const bom = content.startsWith('\ufeff') ? '\ufeff' : '';
            const source = bom ? content.slice(1) : content;
            if (!source.startsWith('"Codigo";"Descripcion";') ||
                    !source.includes('"Ventas_USD_periodo"')) return content;

            const rows = [];
            let row = [], cell = '', inQuotes = false;
            for (let i = 0; i < source.length; i++) {
                const c = source[i];
                if (inQuotes) {
                    if (c === '"') {
                        if (source[i + 1] === '"') { cell += '"'; i++; }
                        else inQuotes = false;
                    } else cell += c;
                } else if (c === '"') inQuotes = true;
                else if (c === ';') { row.push(cell); cell = ''; }
                else if (c === '\n') { row.push(cell); rows.push(row); row = []; cell = ''; }
                else if (c === '\r') { if (source[i + 1] === '\n') i++; row.push(cell); rows.push(row); row = []; cell = ''; }
                else cell += c;
            }
            if (inQuotes) return content;
            if (row.length || cell.length) { row.push(cell); rows.push(row); }
            if (!rows.length || rows[0][6] !== 'Ventas_USD_periodo') return content;
            for (const data of rows.slice(1)) {
                for (const column of numericColumns) {
                    if (typeof data[column] === 'string' && /^-?(?:\d+(?:\.\d+)?|\.\d+)$/.test(data[column])) {
                        data[column] = data[column].replace('.', decimalPoint);
                    }
                }
            }
            return bom + rows.map(fields => fields.map(
                value => '"' + String(value).replace(/"/g, '""') + '"'
            ).join(';')).join('\r\n');
        }
        window.Blob = new Proxy(NativeBlob, {
            construct(target, args) {
                const parts = args[0], options = args[1];
                if (parts && parts.length === 1 && typeof parts[0] === 'string' &&
                    options && /^text\/csv\b/i.test(options.type || '')) {
                    return Reflect.construct(target, [[localizeCsv(parts[0])], options]);
                }
                return Reflect.construct(target, args);
            },
        });
    }

    // upload.js has a fixed `.toFixed(2).replace('.', ',')` size display.
    // Observe only that one label instead of changing the upload workflow.
    if (window.location.pathname === '/transcash_inventory/import') {
        document.addEventListener('DOMContentLoaded', () => {
            const picker = document.getElementById('excelFile');
            const info = document.getElementById('selectedInfo');
            if (!picker || !info || !window.MutationObserver) return;
            const syncFileSize = () => {
                if (!picker.files || !picker.files.length || !info.textContent.includes('Listo para cargar')) return;
                const sizeMB = picker.files[0].size / (1024 * 1024);
                const size = new Intl.NumberFormat('es-EC', {
                    minimumFractionDigits: 2, maximumFractionDigits: 2,
                }).format(sizeMB);
                const desired = size + ' MB · Listo para cargar';
                if (info.textContent !== desired) info.textContent = desired;
            };
            new MutationObserver(syncFileSize).observe(info, { childList: true, characterData: true, subtree: true });
            syncFileSize();
        });
    }

    // For support diagnostics in the iframe console only.
    Object.defineProperty(window, 'transcashNativeDecimalConfig', {
        value: Object.freeze({ ...cfg, grouping: Object.freeze([...grouping]) }),
        configurable: false,
        writable: false,
    });
})();
