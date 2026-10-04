const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const { test } = require('node:test');
const ts = require('typescript');

const sourcePath = path.resolve(__dirname, '../src/components/DateToolbar.tsx');
const source = readFileSync(sourcePath, 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS },
});
const loaded = new Module(sourcePath, module);
loaded.filename = sourcePath;
loaded.paths = Module._nodeModulePaths(path.dirname(sourcePath));
loaded._compile(compiled.outputText, sourcePath);

function findElement(node, type) {
  if (Array.isArray(node)) {
    return node.map((child) => findElement(child, type)).find(Boolean);
  }
  if (!node || typeof node !== 'object') return null;
  if (node.type === type) return node;
  return findElement(node.props?.children, type);
}

test('clearing the date input keeps the last valid selection', () => {
  const selected = [];
  const toolbar = loaded.exports.DateToolbar({
    selectedDate: '2026-04-01',
    today: '2026-04-03',
    onDateChange: (value) => selected.push(value),
  });
  const input = findElement(toolbar, 'input');

  input.props.onChange({ target: { value: '' } });
  assert.deepEqual(selected, []);
  input.props.onChange({ target: { value: '2026-04-02' } });
  assert.deepEqual(selected, ['2026-04-02']);
});
