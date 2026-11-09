/**
 * Offline test for the tool layer, part one: definitions and rendering.
 *
 * This runs without spawning anything.  Inside a confined DSH sandbox a Node
 * child cannot start *any* process -- not even `python -c 1+1` -- so an
 * end-to-end test here would only prove the sandbox works.  What it *can*
 * prove, and what actually breaks a bundle, is:
 *
 *   - a definition the host would reject (missing `output.schema`,
 *     `render` not a function),
 *   - a `render` that throws on a value the tool really returns,
 *   - a registration that never happens because `apply` failed early.
 *
 * Behaviour of the Python engine is covered by `tests/test_engine.py`.
 *
 *   node tests/smoke.mjs
 */
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(HERE);

const registered = new Map();

/** A stand-in for the harness context: only what the tools touch. */
const ctx = {
  tools: {
    register(definition) {
      registered.set(definition.name, definition);
      return () => registered.delete(definition.name);
    },
  },
  subprocess: {
    // Never called by this test; present so `inject` is satisfied and a
    // future end-to-end path fails loudly rather than silently.
    spawn() {
      throw new Error('spawn is not available under the sandbox');
    },
  },
  effect(fn) {
    return fn();
  },
};

let failures = 0;
function check(label, condition, detail) {
  if (condition) {
    console.log(`  PASS  ${label}`);
  } else {
    failures += 1;
    console.log(`  FAIL  ${label}${detail ? ` -- ${detail}` : ''}`);
  }
}

/** The checks the host performs; a failure here takes the whole bundle down. */
function validateTool(definition) {
  if (typeof definition.name !== 'string' || !definition.name) {
    throw new Error('tool name must be a non-empty string');
  }
  if (typeof definition.execute !== 'function') {
    throw new Error(`${definition.name}: execute must be a function`);
  }
  if (!definition.output || typeof definition.output.render !== 'function') {
    throw new Error(`${definition.name}: output.render must be a function`);
  }
  if (typeof definition.output.schema !== 'object' || definition.output.schema === null) {
    throw new Error(`${definition.name}: output.schema must be an object`);
  }
  if (definition.parameters && definition.parameters.type !== 'object') {
    throw new Error(`${definition.name}: parameters must be an object schema`);
  }
}

/** A tiny validator for the JSON Schema subset the harness accepts. */
function schemaErrors(schema, value, path = '$') {
  const errors = [];
  if (!schema || typeof schema !== 'object') return errors;

  const types = schema.type ? [schema.type] : [];
  const matches = (t) => {
    if (t === 'object') return value !== null && typeof value === 'object' && !Array.isArray(value);
    if (t === 'array') return Array.isArray(value);
    if (t === 'number') return typeof value === 'number';
    if (t === 'string') return typeof value === 'string';
    if (t === 'boolean') return typeof value === 'boolean';
    if (t === 'null') return value === null;
    return true;
  };
  if (types.length && !types.some(matches)) {
    errors.push(`${path}: expected ${types.join('|')}, got ${Array.isArray(value) ? 'array' : typeof value}`);
    return errors;
  }

  for (const key of schema.required || []) {
    if (value === null || value === undefined || !(key in value)) {
      errors.push(`${path}: missing required ${key}`);
    }
  }
  if (schema.properties && value && typeof value === 'object') {
    for (const [key, sub] of Object.entries(schema.properties)) {
      if (key in value && value[key] !== undefined) {
        errors.push(...schemaErrors(sub, value[key], `${path}.${key}`));
      }
    }
  }
  if (schema.items && Array.isArray(value)) {
    value.forEach((item, i) => errors.push(...schemaErrors(schema.items, item, `${path}[${i}]`)));
  }
  return errors;
}

/**
 * The host validates every tool result as *lossless JSON*.  An `undefined`
 * property, a function, a `Set`, a `Date` or a `NaN` all fail it -- with an
 * error that names no field, which makes it very hard to find.  Catching it
 * here costs four lines.
 */
function losslessErrors(value, path = '$') {
  const bad = [];
  if (value === undefined) {
    bad.push(`${path}: undefined`);
  } else if (typeof value === 'function' || typeof value === 'symbol') {
    bad.push(`${path}: ${typeof value}`);
  } else if (typeof value === 'number' && !Number.isFinite(value)) {
    bad.push(`${path}: non-finite number`);
  } else if (Array.isArray(value)) {
    value.forEach((item, i) => bad.push(...losslessErrors(item, `${path}[${i}]`)));
  } else if (value instanceof Set || value instanceof Map || value instanceof Date) {
    bad.push(`${path}: ${value.constructor.name}`);
  } else if (value && typeof value === 'object') {
    for (const [key, sub] of Object.entries(value)) {
      if (sub === undefined) bad.push(`${path}.${key}: undefined`);
      else bad.push(...losslessErrors(sub, `${path}.${key}`));
    }
  }
  return bad;
}

async function main() {
  console.log('loading plugin...');
  const plugin = await import(pathToFileURL(join(ROOT, 'index.js')).href);
  check('exports apply', typeof plugin.apply === 'function');
  check('exports name', plugin.name === 'dsh-exam-fig', plugin.name);
  check('injects tools + subprocess',
    Array.isArray(plugin.inject)
    && plugin.inject.includes('tools')
    && plugin.inject.includes('subprocess'),
    JSON.stringify(plugin.inject));

  console.log('applying...');
  plugin.apply(ctx, {});
  check('registered 4 tools', registered.size === 4, [...registered.keys()].join(', '));

  for (const [toolName, definition] of registered) {
    let ok = true;
    let detail;
    try {
      validateTool(definition);
    } catch (err) {
      ok = false;
      detail = err.message;
    }
    check(`definition valid: ${toolName}`, ok, detail);
  }

  // Every rendered value must also satisfy the declared schema -- the host
  // validates `execute`'s return against it on each call.
  const renderCases = [
    ['exam_figure', { kind: 'incline' }, {
      ok: true, kind: 'incline', path: 'x.png', bytes: 1024,
      marks: ['G', 'Gpar', 'Gperp', '30'], detail: { ratio: 0.577 },
    }],
    ['exam_figure', { kind: 'incline' }, { ok: false, kind: 'incline', error: 'boom' }],
    ['exam_figure_catalog', {}, {
      ok: true,
      kinds: [{ kind: 'incline', parameters: [{ name: 'theta_deg', type: 'number', default: 30 }] }],
    }],
    ['exam_figure_check', {}, { ok: true, lines: ['PASS [图 1] 4 项标注一致'] }],
    ['exam_figure_check', {}, { ok: false, lines: ['FAIL [图 1] ...'], error: 'x' }],
    ['exam_figure_doctor', {}, {
      ok: true, python: '3.12.14', font: 'Microsoft YaHei', omml: true,
      missing: [], packages: { matplotlib: '3.11.2' },
    }],
  ];

  console.log('\nrender + schema');
  for (const [toolName, args, value] of renderCases) {
    const definition = registered.get(toolName);
    let rendered = null;
    let renderErr = null;
    try {
      rendered = definition.output.render(args, value);
    } catch (err) {
      renderErr = err.message;
    }
    check(`${toolName}: render does not throw`, renderErr === null, renderErr);
    check(`${toolName}: render returns text blocks`,
      Array.isArray(rendered) && typeof rendered[0]?.text === 'string' && rendered[0].text.length > 0);

    const errs = schemaErrors(definition.output.schema, value);
    check(`${toolName}: value matches output.schema`, errs.length === 0, errs.join('; '));

    const lossy = losslessErrors(value);
    check(`${toolName}: value is lossless JSON`, lossy.length === 0, lossy.join('; '));
  }

  // Argument schemas must accept the shapes the examples use, and their
  // `required` lists must not be satisfiable by an empty call.
  console.log('\nparameter schemas');
  const drawParams = registered.get('exam_figure').parameters;
  check('exam_figure requires kind', (drawParams.required || []).includes('kind'));
  check('exam_figure.params is open', drawParams.properties.params.additionalProperties === true);

  for (const [toolName, definition] of registered) {
    const schema = definition.parameters;
    // The harness rejects a top-level type other than "object".
    check(`${toolName}: parameters.type is object`, schema.type === 'object');
  }

  const e2e = process.env.DSH_EXAMFIG_E2E === '1';
  const vendor = process.env.DSH_EXAMFIG_VENDOR || join(ROOT, 'python', 'vendor');
  console.log(`\nvendor: ${vendor}${existsSync(vendor) ? '' : ' (absent -- engine untested here)'}`);
  if (!e2e) {
    console.log('engine behaviour: see tests/test_engine.py');
  }

  console.log(`\n${failures === 0 ? 'ALL PASS' : `${failures} FAILURE(S)`}`);
  process.exit(failures === 0 ? 0 : 1);
}

main().catch((err) => {
  console.error('smoke test crashed:', err);
  process.exit(1);
});
