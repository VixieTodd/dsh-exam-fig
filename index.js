/**
 * dsh-exam-fig -- figure generation for exam papers, as a DSH host plugin.
 *
 * The actual drawing lives in the Python package under `python/examfig/`.  This
 * file is the harness-facing shell: it registers three tools, resolves which
 * interpreter to use, and turns the child process's single-line JSON output
 * into a tool result.
 *
 * Design notes that cost real debugging time:
 *
 * - **Tools are registered as plain `ToolDefinition` objects.**  The
 *   `@deepseek-ai/dsh-tools` helper `defineTool` is not exposed to profile
 *   plugins on the desktop host, so importing it fails at activation.
 *
 * - **`output.schema` is validated on every call.**  Omitting it (or letting
 *   `execute` return a shape that does not match) makes `apply()` throw
 *   synchronously and takes the whole bundle down with it.
 *
 * - **The Python process is spawned, not imported.**  This plugin must control
 *   `sys.path` before numpy/matplotlib are imported, and the interpreter that
 *   the harness ships is not necessarily the one on `PATH`.
 */
import { existsSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const name = 'dsh-exam-fig';
const inject = ['tools', 'subprocess'];

const HERE = dirname(fileURLToPath(import.meta.url));

/**
 * Locate the Python interpreter that has this plugin's dependencies.
 *
 * Order: explicit env var, then whatever the harness itself ships.  A bare
 * `python` from PATH is the last resort because on Windows it is often the
 * Microsoft Store shim, which resolves to a *different* minor version with a
 * different site-packages -- the plugin then reports "matplotlib missing" on a
 * machine where it is installed.
 *
 * `DSH_HOME` is not guaranteed to be visible in the host process, so the
 * home-directory guess is tried as well, and `dsh-runtimes/` is scanned for
 * whichever runtimes are actually present.
 */
function resolvePython() {
  const candidates = [];
  if (process.env.DSH_EXAMFIG_PYTHON) candidates.push(process.env.DSH_EXAMFIG_PYTHON);
  if (process.env.DSH_PYTHON) candidates.push(process.env.DSH_PYTHON);

  const homes = [process.env.DSH_HOME, join(homedir(), '.dsh')].filter(Boolean);
  const suffixes = [
    ['python.exe'],
    ['bin', 'python3'],
  ];
  for (const home of homes) {
    const runtimes = join(home, 'dsh-runtimes');
    for (const name of ['dsh-primary-runtime', 'dsh-runtime', 'primary-runtime']) {
      for (const suffix of suffixes) {
        candidates.push(join(runtimes, name, 'dependencies', 'python', ...suffix));
      }
    }
    // Whatever runtimes exist, in case the naming differs.
    try {
      for (const entry of readdirSync(runtimes)) {
        for (const suffix of suffixes) {
          candidates.push(join(runtimes, entry, 'dependencies', 'python', ...suffix));
        }
      }
    } catch { /* no runtimes directory: fine */ }
    for (const suffix of suffixes) candidates.push(join(home, 'python', ...suffix));
  }

  for (const c of candidates) {
    if (c && existsSync(c)) return c;
  }
  return process.platform === 'win32' ? 'python.exe' : 'python3';
}

/** Where the vendored wheels live: env override, then `<plugin>/python/vendor`. */
function resolveVendor() {
  if (process.env.DSH_EXAMFIG_VENDOR) return process.env.DSH_EXAMFIG_VENDOR;
  const local = join(HERE, 'python', 'vendor');
  if (existsSync(local)) return local;
  const homes = [process.env.DSH_HOME, join(homedir(), '.dsh')].filter(Boolean);
  for (const home of homes) {
    const inHome = join(home, 'exam-fig', 'vendor');
    if (existsSync(inHome)) return inHome;
  }
  return '';
}

/**
 * Run `python -m examfig.cli <args>` and parse its one-line JSON reply.
 *
 * The child writes exactly one JSON object to stdout and everything else to
 * stderr, so a non-zero exit still yields a machine-readable error instead of
 * a traceback we would have to scrape.
 *
 * Output is collected through the `{ maxBytes }` mode, which means
 * `handle.stdout` is *undefined* -- the bytes live behind
 * `handle.collected.stdout.readFrom(0)` and are read only after `done`
 * resolves.  Attaching a `data` listener to `handle.stdout` here would throw
 * or silently never fire.
 */
async function runCli(ctx, args, signal) {
  const python = resolvePython();
  const env = { ...process.env };
  const vendor = resolveVendor();
  if (vendor) env.DSH_EXAMFIG_VENDOR = vendor;
  const sep = process.platform === 'win32' ? ';' : ':';
  env.PYTHONPATH = join(HERE, 'python') + (env.PYTHONPATH ? sep + env.PYTHONPATH : '');
  env.PYTHONIOENCODING = 'utf-8';
  // matplotlib insists on a writable config dir; without this it writes into
  // %TEMP% and throws PermissionError on teardown under the DSH sandbox.
  if (!env.MPLCONFIGDIR) env.MPLCONFIGDIR = join(HERE, '.mplcfg');

  const spec = {
    argv: [python, '-m', 'examfig.cli', ...args],
    cwd: HERE,
    env,
    stdio: {
      stdin: 'ignore',
      stdout: { maxBytes: 8 * 1024 * 1024 },
      stderr: { maxBytes: 256 * 1024 },
    },
    graceMs: 3000,
  };
  if (signal) spec.signal = signal;

  const handle = ctx.subprocess.spawn(spec);
  const { exitCode, signal: sig } = await handle.done;

  const readOut = handle.collected.stdout?.readFrom(0);
  const readErr = handle.collected.stderr?.readFrom(0);
  const text = (readOut?.text || '').trim();
  const errText = (readErr?.text || '').trim();

  // The CLI always ends with a single JSON line; earlier lines, if any, are
  // stray prints from third-party libraries.
  const lastLine = text.split(/\r?\n/).filter(Boolean).pop() || '';
  let parsed = null;
  try {
    parsed = JSON.parse(lastLine);
  } catch {
    parsed = null;
  }
  if (parsed === null) {
    throw new Error(
      `examfig produced no JSON (exit ${exitCode}${sig ? `, signal ${sig}` : ''}): ` +
      ((errText || text).slice(-900) || '(empty output)'));
  }
  return parsed;
}

function textBlock(text) {
  return [{ type: 'text', text }];
}

/** The figure tool: draw one figure and return where it landed. */
function registerDrawTool(ctx) {
  return ctx.tools.register({
    name: 'exam_figure',
    description: [
      'Draw one exam figure (math / physics / chemistry) from parameters.',
      'Kinds: quadratic, power, triangle, cube, pyramid, incline, circuit, lens,',
      'mirror, molecule.',
      'Every parameter the question states must be passed in, so the picture and the',
      'numbers in the prose come from the same source. The result reports `marks`:',
      'the labels actually painted, for use with `exam_figure_check`.',
    ].join(' '),
    parameters: {
      type: 'object',
      properties: {
        kind: { type: 'string', description: 'figure kind, e.g. incline, circuit, quadratic' },
        params: {
          type: 'object',
          description: 'parameters for that kind; call exam_figure_catalog for the list',
          additionalProperties: true,
        },
        out: { type: 'string', description: 'output PNG path (default: <workspace>/examfig/<kind>.png)' },
      },
      required: ['kind'],
      additionalProperties: false,
    },
    output: {
      schema: {
        type: 'object',
        properties: {
          ok: { type: 'boolean' },
          kind: { type: 'string' },
          path: { type: 'string' },
          bytes: { type: 'number' },
          marks: { type: 'array', items: { type: 'string' } },
          detail: { type: 'object', additionalProperties: true },
          layout: { type: 'object', additionalProperties: true },
          error: { type: 'string' },
        },
        required: ['ok'],
        additionalProperties: true,
      },
      render(_args, value) {
        if (!value.ok) return textBlock(`figure failed: ${value.error}`);
        const lines = [
          `drew ${value.kind} -> ${value.path} (${value.bytes} bytes)`,
          `marks: ${(value.marks || []).join(', ')}`,
        ];
        const lay = value.layout;
        if (lay) {
          if (lay.applicable === false) {
            lines.push('layout: not applicable (labels drawn by the renderer)');
          } else if (lay.collisions === 0) {
            lines.push(`layout: clean${lay.fixed ? ` (${lay.fixed} label(s) nudged apart)` : ''}`);
          } else {
            // Say it plainly.  A caller who does not know the figure is
            // compromised will ship it.
            lines.push(`layout: ${lay.collisions} UNRESOLVED COLLISION(S)`);
            for (const item of lay.remaining || []) {
              lines.push(`  - ${item.kind}: "${item.label}"${item.with ? ` vs "${item.with}"` : ''}`);
            }
          }
        }
        return textBlock(lines.join('\n'));
      },
    },
    async execute(args, exec) {
      const out = args.out || join(process.cwd(), 'examfig', `${args.kind}.png`);
      const payload = await runCli(ctx, [
        'draw', '--kind', String(args.kind),
        '--params', JSON.stringify(args.params || {}),
        '--out', out,
      ], exec.signal);

      if (!payload.ok) {
        return { ok: false, kind: String(args.kind), error: payload.error || 'unknown error' };
      }
      // `detail` takes the rest of the reply, but only fields the schema does
      // not name: `ok`/`kind`/`path`/`bytes`/`marks`/`layout` are promoted,
      // everything else is diagnostic noise the caller may find useful.
      const { marks, path, bytes, layout, ok: _ok, kind: _kind, error: _err, ...rest } = payload;
      // Drop undefined values: the host validates the result as lossless JSON
      // and an `undefined` property fails the whole call.
      const detail = {};
      for (const [key, value] of Object.entries(rest)) {
        if (value !== undefined && value !== null) detail[key] = value;
      }
      const result = {
        ok: true,
        kind: String(args.kind),
        path: String(path || out),
        bytes: typeof bytes === 'number' ? bytes : 0,
        marks: Array.isArray(marks) ? marks.map(String) : [],
        detail,
      };
      // Promoted so `render` can warn about it without digging into `detail`:
      // an unresolved collision is the one thing a caller must not miss.
      if (layout && typeof layout === 'object') result.layout = layout;
      return result;
    },
    isConcurrencySafe(args) {
      // No shared state between calls: each spawns its own interpreter and
      // writes its own file, as long as the paths differ.
      return typeof args.out === 'string';
    },
    presentCall(args) {
      return { card: 'generic', title: `draw ${args.kind}`, kind: 'read', locations: [] };
    },
  });
}

/** The catalog tool: what can be drawn, and with which parameters. */
function registerCatalogTool(ctx) {
  return ctx.tools.register({
    name: 'exam_figure_catalog',
    description: 'List every figure kind this plugin can draw, with each parameter\'s type and default.',
    parameters: { type: 'object', properties: {}, additionalProperties: false },
    output: {
      schema: {
        type: 'object',
        properties: {
          ok: { type: 'boolean' },
          kinds: {
            type: 'array',
            items: {
              type: 'object',
              properties: { kind: { type: 'string' } },
              required: ['kind'],
              additionalProperties: true,
            },
          },
          error: { type: 'string' },
        },
        required: ['ok'],
        additionalProperties: false,
      },
      render(_args, value) {
        if (!value.ok && value.error) return textBlock(`catalog failed: ${value.error}`);
        const lines = (value.kinds || []).map((k) => {
          const ps = (k.parameters || [])
            .map((p) => `${p.name}=${JSON.stringify(p.default)}`)
            .join(', ');
          return `- ${k.kind}(${ps})`;
        });
        return textBlock(`figure kinds (${lines.length}):\n${lines.join('\n')}`);
      },
    },
    async execute(_args, exec) {
      const payload = await runCli(ctx, ['catalog'], exec.signal);
      // Project explicitly: the reply carries diagnostics the schema does not
      // declare, and an undeclared field fails the whole call as
      // "invalid output".
      if (!payload.ok) {
        return { ok: false, kinds: [], error: String(payload.error || 'unknown error') };
      }
      return { ok: true, kinds: Array.isArray(payload.kinds) ? payload.kinds : [] };
    },
  });
}

/** The consistency checker: does the figure show everything the stem claims? */
function registerCheckTool(ctx) {
  return ctx.tools.register({
    name: 'exam_figure_check',
    description: [
      'Verify that each figure shows every label the question stem relies on.',
      'Pass `specs` (what each question requires) and `figures` (the `marks` returned by',
      'exam_figure). A vertex labelled on the wrong point, or a component arrow drawn at',
      'the wrong length, fails here even though the image looks fine.',
    ].join(' '),
    parameters: {
      type: 'object',
      properties: {
        specs: {
          type: 'array',
          description: 'per question: {no, need: [labels], text: stem text}',
          items: {
            type: 'object',
            properties: {
              no: { type: 'number' },
              need: { type: 'array', items: { type: 'string' } },
              text: { type: 'string' },
            },
            required: ['no'],
            additionalProperties: true,
          },
        },
        figures: {
          type: 'object',
          description: 'question number -> {marks: [...]}, as returned by exam_figure',
          additionalProperties: true,
        },
      },
      required: ['specs', 'figures'],
      additionalProperties: false,
    },
    output: {
      schema: {
        type: 'object',
        properties: {
          ok: { type: 'boolean' },
          lines: { type: 'array', items: { type: 'string' } },
          error: { type: 'string' },
        },
        required: ['ok'],
        additionalProperties: false,
      },
      render(_args, value) {
        const head = value.ok ? 'ALL PASS' : 'FAILURES';
        return textBlock(`${head}\n${(value.lines || []).join('\n')}`);
      },
    },
    async execute(args, exec) {
      // figcheck reads a JSON file rather than stdin.  Write it to a private
      // temp directory: the plugin directory itself may be read-only once
      // installed, and a fixed filename there would race between sessions.
      const dir = mkdtempSync(join(tmpdir(), 'dsh-examfig-'));
      const specPath = join(dir, 'spec.json');
      writeFileSync(specPath, JSON.stringify({ specs: args.specs, figures: args.figures }), 'utf8');
      try {
        const payload = await runCli(ctx, ['check', '--spec', specPath], exec.signal);
        // Omit `error` when there is none.  A `false` result with `lines` is
        // the normal failure report (the figure disagrees with the stem), not
        // an execution error, and the two must stay distinguishable.
        const result = { ok: Boolean(payload.ok), lines: payload.lines || [] };
        if (!payload.ok && payload.error) result.error = payload.error;
        return result;
      } finally {
        try { rmSync(dir, { recursive: true, force: true }); } catch { /* best effort */ }
      }
    },
  });
}

/** The environment tool: is this install usable, and what is missing? */
function registerDoctorTool(ctx) {
  return ctx.tools.register({
    name: 'exam_figure_doctor',
    description: 'Report the figure engine environment: interpreter, vendored packages, CJK font, OMML support.',
    parameters: { type: 'object', properties: {}, additionalProperties: false },
    output: {
      schema: {
        type: 'object',
        properties: {
          ok: { type: 'boolean' },
          python: { type: 'string' },
          font: { type: 'string' },
          omml: { type: 'boolean' },
          missing: { type: 'array', items: { type: 'string' } },
          hint: { type: 'string' },
          warning: { type: 'string' },
          packages: { type: 'object', additionalProperties: true },
          error: { type: 'string' },
        },
        required: ['ok'],
        additionalProperties: false,
      },
      render(_args, value) {
        if (!value.ok && value.error && !value.python) {
          return textBlock(`doctor failed: ${value.error}`);
        }
        const pkgs = Object.entries(value.packages || {})
          .map(([k, v]) => `${k}${v ? '@' + v : ' (missing)'}`).join(', ');
        const lines = [
          `ok: ${value.ok}`,
          `python: ${value.python}`,
          `font: ${value.font || '(none)'}`,
          `omml: ${value.omml}`,
          `packages: ${pkgs}`,
        ];
        if (value.missing && value.missing.length) lines.push(`missing: ${value.missing.join(', ')}`);
        if (value.hint) lines.push(`hint: ${value.hint}`);
        if (value.warning) lines.push(`warning: ${value.warning}`);
        return textBlock(lines.join('\n'));
      },
    },
    async execute(_args, exec) {
      const payload = await runCli(ctx, ['doctor'], exec.signal);
      // Project onto the declared schema.  `doctor` reports a dozen extra
      // diagnostics (executable, vendor, mplCacheDir, mirrors) that are useful
      // in the CLI and *not* declared here; returning them verbatim made the
      // host reject the result as "invalid output".
      //
      // Every field must also be *present and defined*: an `undefined` value
      // fails the host's lossless-JSON check, so optional strings are added
      // conditionally instead of being passed through as undefined.
      const result = {
        ok: Boolean(payload.ok),
        python: String(payload.python || ''),
        font: String(payload.font || ''),
        omml: Boolean(payload.omml),
        missing: Array.isArray(payload.missing) ? payload.missing.map(String) : [],
        packages: payload.packages && typeof payload.packages === 'object'
          ? payload.packages : {},
      };
      if (payload.hint) result.hint = String(payload.hint);
      if (payload.warning) result.warning = String(payload.warning);
      if (payload.error) result.error = String(payload.error);
      return result;
    },
  });
}

function apply(ctx, config) {
  const pluginDir = config?.pluginDir || HERE;
  if (config?.python) process.env.DSH_EXAMFIG_PYTHON = config.python;
  if (config?.vendor) process.env.DSH_EXAMFIG_VENDOR = config.vendor;
  void pluginDir;

  ctx.effect(() => {
    const disposers = [
      registerDrawTool(ctx),
      registerCatalogTool(ctx),
      registerCheckTool(ctx),
      registerDoctorTool(ctx),
    ];
    return () => disposers.forEach((dispose) => dispose());
  });
}

// No `Config` export: cordis treats an exported `Config` as a callable schema
// and calls it with the composed config.  Exporting null risks a mount-time
// TypeError.
export { name, inject, apply };
