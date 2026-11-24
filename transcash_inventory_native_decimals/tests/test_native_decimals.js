// Standalone checks: node tests/test_native_decimals.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../static/src/native_decimals.js'), 'utf8');

function page(cfg, pathname = '/transcash_inventory/dashboard') {
    const context = vm.createContext({
        console,
        window: { location: { pathname }, Blob },
        document: {
            querySelector: selector => selector === 'meta[name="transcash-native-decimals"]' ? { content: JSON.stringify(cfg) } : null,
            addEventListener: () => {},
        },
    });
    vm.runInContext(source, context);
    return context;
}

function checkNumber(cfg, expected) {
    const ctx = page(cfg);
    const actual = vm.runInContext('new Intl.NumberFormat("es-EC",{minimumFractionDigits:2,maximumFractionDigits:2}).format(1234567.89)', ctx);
    assert.equal(actual, expected);
    assert.equal(vm.runInContext('(1234567.89).toLocaleString("es-EC",{minimumFractionDigits:2,maximumFractionDigits:2})', ctx), expected);
    assert.equal(vm.runInContext('new Intl.NumberFormat("en-US",{minimumFractionDigits:2,maximumFractionDigits:2}).format(1234567.89)', ctx), '1,234,567.89');
    assert.equal(vm.runInContext('new Intl.NumberFormat("es-EC",{minimumFractionDigits:1,maximumFractionDigits:1}).format(-1234.56)', ctx),
        '-' + expectedNegative(cfg));
    return ctx;
}
function expectedNegative(cfg) {
    if (!cfg.thousands_sep || cfg.grouping.length === 0) return '1234' + cfg.decimal_point + '6';
    return '1' + cfg.thousands_sep + '234' + cfg.decimal_point + '6';
}

checkNumber({ decimal_point: ',', thousands_sep: '.', grouping: [3,0] }, '1.234.567,89');
checkNumber({ decimal_point: '.', thousands_sep: ',', grouping: [3,0] }, '1,234,567.89');
checkNumber({ decimal_point: '.', thousands_sep: '', grouping: [] }, '1234567.89');
const ctxIndian = page({ decimal_point: ',', thousands_sep: ' ', grouping: [3,2,0] });
assert.equal(vm.runInContext('new Intl.NumberFormat("es-EC",{maximumFractionDigits:2}).format(1234567.89)', ctxIndian), '12 34 567,89');
assert.equal(vm.runInContext('new Intl.NumberFormat("es-EC").format(0)', ctxIndian), '0');
assert.equal(vm.runInContext('new Intl.NumberFormat("es-EC").format(1234567)', ctxIndian), '12 34 567');
assert.equal(vm.runInContext('new Intl.NumberFormat("es-EC").format(NaN)', ctxIndian), 'NaN');
assert.equal(vm.runInContext('new Intl.NumberFormat("es-EC").format(Infinity)', ctxIndian), '∞');
assert.equal(vm.runInContext('new Intl.NumberFormat("es-EC", { maximumFractionDigits: 2 }).formatToParts(12345.67).map(x => x.value).join("")', ctxIndian), '12 345,67');
const ctxStop = page({ decimal_point: ',', thousands_sep: '.', grouping: [3,-1] });
assert.equal(vm.runInContext('new Intl.NumberFormat("es-EC").format(12345678)', ctxStop), '12345.678');

// Verify the narrow CSV hook changes numeric fields, never text columns or the delimiter.
(async () => {
    const ctx = page({ decimal_point: ',', thousands_sep: '.', grouping: [3,0] });
    const csv = '\ufeff"Codigo";"Descripcion";"Categoria";"Marca";"Formato";"Proveedor_ficha";"Ventas_USD_periodo";"CostoVentas_USD_periodo";"UtilidadBruta_USD_periodo";"MargenBruto"\r\n' +
        '"SKU.009";"Un valor 1.20; \"\"Especial\"\"";"Telefonia";"M";"U";"A";"1234.50";"300.10";"934.40";"0.75000"';
    ctx.originalCsv = csv;
    const blob = vm.runInContext('new window.Blob([originalCsv],{type:"text/csv;charset=utf-8;"})', ctx);
    const text = await blob.text();
    assert.ok(text.includes('"SKU.009";"Un valor 1.20; ""Especial"""'));
    assert.ok(text.includes('"1234,50";"300,10";"934,40";"0,75000"'));
    assert.ok(text.startsWith('"Codigo";"Descripcion"'));
    assert.deepEqual([...new Uint8Array(await blob.arrayBuffer())].slice(0,3), [239,187,191]);
    const notCsv = vm.runInContext('new window.Blob(["1234.50"],{type:"text/plain"})', ctx);
    assert.equal(await notCsv.text(), '1234.50');
    console.log('OK: separadores nativos, agrupación, precisión, negativos, CSV y tipos ajenos a CSV');
})().catch(error => { console.error(error); process.exitCode = 1; });
