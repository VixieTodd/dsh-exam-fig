# dsh-exam-fig

出题配图 — 数学、物理、化学 — **由图中的数值直接生成**，并配一个校验器，证明图与题干一致。

DSH host 插件：四个工具，无 UI，无客户端部分。

```
exam_figure          按参数画一张图
exam_figure_catalog  能画什么，以及各自的参数
exam_figure_check    图是否画出了题干声称的全部内容？
exam_figure_doctor   当前安装是否可用？
```

---

## 为什么需要它

让模型"画一个 30° 斜面、上面放 2 kg 物块"，出来的图**看着对**，但经常是错的：分量箭头按全长画而不是 `G sin θ`、直角标在了错误的顶点、`R₂` 标到了 `R₁` 的位置、凹面镜像画在镜后。这些都是**静默错误**——页面照样渲染成功。

解法不是更好的提示词，而是不再把图当作"插图"，而当作**题干数值的派生品**：

1. **参数进，数值出。** `incline(theta_deg=30, G=1.55)` 自己算出 `G∥ = G sin 30°`。箭头之所以画那么长，是因为它就是那么长；不存在"画一根大概这么长的箭头"这个可以和答案打架的中间步骤。
2. **绘图函数返回它画了什么。** 每个函数返回 `marks`——实际落上去的标签。`figcheck` 拿它和题干要求比对。顶点标错了会失败，哪怕图看着没问题。
3. **会骗人的几何靠算术抓，不靠眼睛。** `figcheck` 写完就抓到一个 `Rt△ABC`：题干说 `∠C = 90°`，图上直角却画在顶点 A。

---

## 快速开始

### 1. 安装插件

```bash
dsh plugin install /absolute/path/to/dsh-exam-fig
```

或在会话内：

```
plugin_manager  action=install_bundle  target=/absolute/path/to/dsh-exam-fig
```

bundle 是 host-only 的：`index.js` + `cordis.patch.yml` + `package.json`。它调用 Python，所以下一步不能跳过。

### 2. 准备 Python 依赖

插件**不打包** wheel——它们约 200 MB 且与版本绑定。一次性抓到一个 vendor 目录：

```bash
cd /path/to/dsh-exam-fig
python -m examfig.figdeps
```

它读 PyPI 镜像、手工解析 `Requires-Dist`、把 wheel 解压进 `python/vendor/`。**刻意不用 `pip`**——原因见[为什么不用 pip](#为什么不用-pip)。

验证：

```bash
python -m examfig.cli doctor
```

```json
{"ok": true, "python": "3.12.14", "font": "Microsoft YaHei",
 "omml": true, "missing": [],
 "packages": {"matplotlib": "3.11.2", "numpy": "2.5.4", "rdkit": "2026.9.1", ...}}
```

在 agent 侧，`exam_figure_doctor` 报告同样内容。

### 3. 画图

```
exam_figure(kind="incline", params={"theta_deg": 30, "G": 1.55})
```

```json
{"ok": true, "kind": "incline", "path": ".../examfig/incline.png",
 "marks": ["30", "G", "Gperp", "Gpar"],
 "detail": {"G_par": 0.775, "G_perp": 1.342, "ratio": 0.5773502691896257}}
```

### 4. 证明它与题干一致

```
exam_figure_check(
  specs=[{no: 1, need: ["G", "G_par", "G_perp", "30"], text: "如图1，物块重 G"}],
  figures={1: {marks: ["G", "Gpar", "Gperp", "30"]}})
```

```
ALL PASS
PASS [图 1] 4 项标注一致
```

指向一张缺标注的图，它会失败，并点名缺的是哪个。

---

## 环境

| 要求 | 说明 |
| --- | --- |
| **DSH** | `^0.2.2-rc.1`。host-only bundle，需要 `tools` 与 `subprocess` 服务。 |
| **Node** | ≥ 20（插件本身只用 `node:` 内置模块）。 |
| **Python** | 3.10+。默认用 DSH 自带的解释器（`$DSH_HOME/dsh-runtimes/.../python`），可用 `DSH_EXAMFIG_PYTHON` 覆盖。 |
| **中文字体** | Microsoft YaHei、SimHei、Noto Sans CJK SC、PingFang SC、WenQuanYi Zen Hei 任一。没有中文标签会变成方框，`exam_figure_doctor` 会报告选中的字体。 |
| **Microsoft Office**（可选） | 提供 `MML2OMML.XSL`，仅 Word 原生公式需要。没有时公式降级为纯文本。可用 `DSH_EXAMFIG_MML2OMML` 指定路径。 |

平台：开发与测试在 Windows 上完成。除默认字体列表和 Office 路径探测外没有 Windows 特有的东西，macOS/Linux 装有中文字体即可用。

### 环境变量

| 变量 | 作用 |
| --- | --- |
| `DSH_EXAMFIG_PYTHON` | 要调用的解释器 |
| `DSH_EXAMFIG_VENDOR` | 解压后的 wheel 所在目录 |
| `DSH_EXAMFIG_CACHE` | matplotlib 的 `MPLCONFIGDIR` |
| `DSH_EXAMFIG_MML2OMML` | `MML2OMML.XSL` 路径 |

---

## 架构

```
dsh-exam-fig/
├── index.js              插件本体：四个工具，调用 Python
├── cordis.patch.yml      bundle patch（一条 insert）
├── package.json
├── python/examfig/
│   ├── cli.py            每个子命令输出一个 JSON —— 这是接缝
│   ├── env.py            sys.path 引导、matplotlib 缓存、中文字体探测
│   ├── registry.py       kind -> (module, function, params)  [惰性]
│   ├── figcheck.py       声明标注 vs 实际标注
│   ├── figures/
│   │   ├── _helpers.py   共享原语：坐标轴框、点、箭头、测距括号
│   │   ├── plane.py      quadratic, triangle
│   │   ├── power.py      y = x^a 五个幂同图
│   │   ├── solid.py      cube, pyramid（正交投影 + 背面剔除）
│   │   ├── incline.py    斜面与力的分解
│   │   ├── numberline.py 数轴：区间、射线、标点
│   │   ├── venn.py       二/三集合韦恩图，按区域着色
│   │   ├── algebra.py    explog（a^x 与 log_a x）、piecewise / |ax+b|+c
│   │   ├── trig.py       y = A sin(ωx + φ) + k
│   │   ├── unitcircle.py 单位圆与正弦线、余弦线、正切线
│   │   ├── geometry.py   solve_triangle, circleline, vectors
│   │   ├── conic.py      椭圆、双曲线、抛物线（焦点、准线）
│   │   ├── stats.py      直方图+频率多边形、散点图+回归线
│   │   ├── kinematics.py motion（同一组方程出 x-t 与 v-t）
│   │   ├── mechanics.py  forces, projectile, circular
│   │   ├── waves.py      wave, vibration, standingwave
│   │   ├── optics2.py    refraction（含临界角）、doubleslit、energylevel
│   │   ├── thermo.py     由过程列表生成 p-V 图
│   │   ├── em.py         fieldlines, magnetic, induction
│   │   ├── circuit.py    串联电路（schemdraw）
│   │   ├── circuit2.py   并联支路、电表、滑动变阻器（schemdraw）
│   │   ├── optical.py    凸透镜、凹面镜
│   │   ├── chemistry.py  滴定曲线、速率-时间与平衡移动
│   │   └── molecule.py   键线式（RDKit）
│   ├── docxkit.py        python-docx 辅助：字体、图宽、混合 run
│   ├── omml.py           LaTeX -> Word 原生公式
│   ├── chem.py           带真下标化学式；按规范用 = 或 ->
│   └── figdeps.py        wheel 抓取器（不用 pip）
└── tests/
    ├── smoke.mjs         工具定义、render、output schema
    └── test_engine.py    绘图数学、校验器、化学
```

### 接缝：每次调用一个 JSON

Node 从不 import Python，Python 也不知道 Node 存在。`index.js` 启动 `python -m examfig.cli <子命令>`，把 stdout 的**最后一行**当单个 JSON 解析；其余全进 stderr。所以失败的子进程也返回机器可读的 `{ok: false, error: ...}`，而不是让调用方去刮 traceback。

输出以 `{ maxBytes }` 模式收集，这意味着 **`handle.stdout` 是 `undefined`**，必须在 `done` 之后从 `handle.collected.stdout.readFrom(0)` 取字节。在那里挂 `data` 监听器会抛错。

### 惰性导入是结构性的，不是风格

`python/vendor/` 只有在 `env.bootstrap()` 跑过之后才进 `sys.path`。所以 `figures/__init__.py` 用 PEP 562 的 `__getattr__` 暴露子模块，`registry.REGISTRY` 存的是 `(模块名, 函数名)` 字符串而不是 callable。在包导入期 import 绘图模块，在这个项目要服务的环境里必然 `ModuleNotFoundError: numpy`。

### 标签定位的两套办法

`labelplace.py` 把"这个点标注放哪"当一个小优化问题解：8 个方向 × 2 个距离，代价 = 出框 + 与其他标签重叠 + 压线 + 离锚点距离。它需要真实渲染器测量（`text.get_window_extent`）才知道标签多大——按字符数估，一旦掺了中文和 mathtext 下标就差一倍以上。

但它不适用于**属于整个元件**的标签。电路图里标签属于回路外侧、元件中点旁边；用优化器会把 `R₂` 塞进回路内部，在电路图上就是错的。所以 `circuit.py` 用确定性做法：元件中点 + 外法向 × 实测偏移。**先问标签锚的是什么，再选定位策略。**

### 碰撞检查：保存前最后跑的那一步

`labelplace.py` 决定标签**放哪**；`layout.py` 事后问一个不同的问题：**画完的图到底能不能读？** 逐个放置时，前一个标签不可能知道后一个会压到它身上，也不知道最后一个标签会跑到曲线上面或者半个身子出画框。

现在每张图都以 `layout.finish(fig, ax, path)` 收尾，而不是 `fig.savefig(...)`。它实测每个文字盒子、报告三类碰撞、尝试把出问题的标签挪开、保存，然后返回：

```json
{"collisions": 0, "fixed": 2, "remaining": []}
```

这份报告一路传回工具层，`exam_figure` 会打印出来：

```
layout: clean (2 label(s) nudged apart)
```

修不好时：

```
layout: 1 UNRESOLVED COLLISION(S)
  - overlap: "G" vs "G_{\perp}"
```

**修不好就报出来，绝不掩盖。** 修不好的图照样落盘（调用方需要看到它），但报告会说明——一张悄悄标错的图正是这个项目要防的事。

三类严重度，因为严重程度本来就不一样：

| 严重度 | 含义 | 权重 |
| --- | --- | --- |
| `overlap` | 两个标签叠在一起，两个都读不了 | 10 |
| `frame` | 标签跑出坐标轴范围（`bbox_inches="tight"` 还会把整页撑开去装它） | 6 |
| `line` | 标签压在画出来的笔划上，或压在物块轮廓上 | 1 |

修复尝试 17 个候选位移（按标签自身宽高的倍数），只有在**严格降低该标签得分**时才接受。否则原位不动。

#### `skip` 列表，以及它为什么必须存在

有些标签**本来就该贴着它描述的东西**：角度标记坐在两条射线之间的楔形里，`O` 坐在两轴之间的夹角里，`x`/`y` 坐在它们命名的那根轴的末端。把这些当碰撞审计、再"修好"，直接把斜面图的 `30°` 推出了图外——这是真实发生的回归，靠看输出而不是看报告才发现的。

所以 `finish(..., skip=(...))` 让指定标签豁免压线与出框检查。**它们仍然参与重叠检查**，因为两段文字叠在一起在任何约定下都是错的。

```python
report = layout.finish(fig, ax, out_path, skip=("$O$", "$x$", "$y$"))
```

#### 审计绝不能误判为障碍的两样东西

* **空标注是箭头。** `ax.annotate("", ...)` 造出的 `Text` 没有字符串；把它当标签会把每个箭头尖都报成碰撞。
* **只有标记的图线是点，不是笔划。** `ax.plot(x, y, "k.", ms=3.5)` 画的是顶点圆点；把它当线会把每个顶点标签推离自己的顶点。

### 布局检查**不**做什么

它不替代对图本身的思考。三根箭头同起点、只差 30°，任何自动 pass 都排不开——标签总得有地方去，而"什么地方"由几何决定。那里的解法是改**画法**：箭头画短、斜面画矮宽，让标签有地方去。见 `figures/incline.py`。

它也不碰 `molecule`、`circuit`、`circuit2`：RDKit 与 schemdraw 自己排元素和自己的标签，没有 matplotlib 文字对象可量。这三类返回 `{"applicable": false}`，让遍历三十九种的调用方不必特判。


---

## 四个工具

### `exam_figure`

| 参数 | 类型 | 含义 |
| --- | --- | --- |
| `kind` | string | 三十九种之一 |
| `params` | object | 该 kind 的参数；未知键会被拒绝 |
| `out` | string | 输出 PNG，默认 `<cwd>/examfig/<kind>.png` |

返回 `{ok, kind, path, bytes, marks, detail}`。`marks` 是绘图函数画的时候登记的标签列表，**绝不从图片反推**。

### `exam_figure_catalog`

三十九种 kind 及每个参数的类型与默认值。**先调它，别猜参数名**——`coerce()` 会拒绝未知键并列出可接受的。

**平面几何与立体**

| kind | 参数 |
| --- | --- |
| `quadratic` | `a`（默认 `1.0`）、`b`（默认 `-2.0`）、`c`（默认 `-3.0`）|
| `power` | `exponents`（默认 `[1.0, 2.0, 3.0, -1.0, 0.5]`）|
| `triangle` | `ac`（默认 `3.0`）、`bc`（默认 `4.0`），直角在 C |
| `cube` | `a`（默认 `1.0`）、`show_diagonal`（默认 `true`）|
| `pyramid` | `a`（默认 `1.0`）、`h`（默认 `1.05`）|

**集合、区间与函数**

| kind | 参数 |
| --- | --- |
| `numberline` | `lo`（默认 `-4.0`）、`hi`（默认 `6.0`）、`intervals`（默认 `[[-1.0, 2.0, 'closed']]`）、`points` |
| `venn` | `sets`（默认 `['A', 'B']`）、`regions`（默认 `{}`）、`shade` |
| `explog` | `base`（默认 `2.0`）、`show_log`（默认 `true`）、`show_reciprocal`（默认 `true`）、`span`（默认 `3.4`）|
| `piecewise` | `mode`（默认 `absolute`）、`abs_a`（默认 `1.0`）、`abs_b`（默认 `0.0`）、`abs_c`（默认 `0.0`）、`knots`（默认 `[[-3.0, -1.0], [-1.0, 1.0], [1.0, -2.0]]`）|
| `trig` | `A`（默认 `1.0`）、`omega`（默认 `1.0`）、`phi`（默认 `0.0`）、`shift`（默认 `0.0`）、`periods`（默认 `1.0`）|

**三角与平面几何**

| kind | 参数 |
| --- | --- |
| `unitcircle` | `theta_deg`（默认 `50.0`）、`show_tan`（默认 `true`）、`show_angles`（默认 `true`）|
| `solve_triangle` | `a`（默认 `5.0`）、`b`（默认 `6.0`）、`c`（默认 `7.0`）、`show_circle`（默认 `true`）、`show_angles`（默认 `true`）|
| `circleline` | `r`（默认 `3.0`）、`dist`（默认 `1.8`）、`angle_deg`（默认 `0.0`）、`tangent`（默认 `false`）|
| `vectors` | `u`（默认 `[3.0, 1.0]`）、`v`（默认 `[1.0, 2.5]`）、`mode`（默认 `both`）|

**圆锥曲线与统计**

| kind | 参数 |
| --- | --- |
| `conic` | `kind`（默认 `ellipse`）、`a`（默认 `3.0`）、`b`（默认 `2.0`）、`p`（默认 `2.0`）、`show_directrix`（默认 `true`）、`show_asymptotes`（默认 `true`）|
| `histogram` | `samples`、`bins`（默认 `6`）、`show_polygon`（默认 `true`）、`show_normal`（默认 `true`）、`xlabel`（默认 `数据`）、`ylabel`（默认 `频率/组距`）|
| `scatter` | `points`、`slope`（默认 `0.0`）、`intercept`（默认 `0.0`）、`show_fit`（默认 `true`）、`xlabel`（默认 `$x$`）、`ylabel`（默认 `$y$`）|

**力学**

| kind | 参数 |
| --- | --- |
| `incline` | `theta_deg`（默认 `30.0`）、`G`（默认 `1.55`）、`L`（默认 `7.2`）|
| `forces` | `magnitudes`、`angles`、`weight`（默认 `0.0`）、`incline_deg`（默认 `0.0`）、`show_decomposition`（默认 `true`）|
| `projectile` | `speed`（默认 `10.0`）、`angle_deg`（默认 `45.0`）、`launch_height`（默认 `0.0`）、`gravity`（默认 `9.8`）、`show_components`（默认 `true`）、`show_range`（默认 `true`）|
| `circular` | `radius`（默认 `2.0`）、`speed`（默认 `4.0`）、`mass`（默认 `0.5`）、`angle_deg`（默认 `35.0`）、`show_critical`（默认 `true`）、`show_forces`（默认 `true`）|
| `motion` | `x0`（默认 `0.0`）、`v0`（默认 `6.0`）、`a`（默认 `-2.0`）、`t_end`（默认 `0.0`）、`show_area`（默认 `true`）|

**波与光学**

| kind | 参数 |
| --- | --- |
| `wave` | `amplitude`（默认 `2.0`）、`wavelength`（默认 `4.0`）、`cycles`（默认 `2.0`）、`speed`（默认 `0.0`）|
| `vibration` | `amplitude`（默认 `2.0`）、`period`（默认 `0.8`）、`cycles`（默认 `2.5`）|
| `standingwave` | `amplitude`（默认 `2.0`）、`length`（默认 `6.0`）、`antinodes`（默认 `3`）、`show_envelope`（默认 `true`）|
| `refraction` | `n1`（默认 `1.0`）、`n2`（默认 `1.5`）、`incidence_deg`（默认 `45.0`）、`show_critical`（默认 `true`）|
| `doubleslit` | `wavelength`（默认 `600.0`）、`slit_separation`（默认 `0.2`）、`distance`（默认 `1.0`）、`window_mm`（默认 `20.0`）、`n_fringes`（默认 `9`）|
| `lens` | `f`（默认 `10.0`）、`u`（默认 `30.0`）、`height`（默认 `6.0`）|
| `mirror` | `f`（默认 `10.0`）、`u`（默认 `30.0`）、`height`（默认 `6.0`）|

**热学、近代物理与电磁学**

| kind | 参数 |
| --- | --- |
| `pv` | `states`（默认 `[3.0, 1.0]`）、`processes`（默认 `[['isobar', 3.0], ['isochore', 1.0], ['isobar', 1.0], ['isochore', 3.0]]`）、`show_area`（默认 `true`）|
| `energylevel` | `z`（默认 `1.0`）、`n_max`（默认 `4`）、`transitions`（默认 `[[3, 1], [2, 1]]`）|
| `fieldlines` | `charges`、`n_lines`（默认 `12`）、`n_equi`（默认 `6`）、`extent`（默认 `3.2`）、`show_labels`（默认 `true`）|
| `magnetic` | `charge`（默认 `1.0`）、`speed`（默认 `1.0`）、`mass`（默认 `1.0`）、`field`（默认 `1.0`）、`sign`（默认 `1`）、`field_mode`（默认 `in`）、`angle_deg`（默认 `90.0`）|
| `induction` | `rod_length`（默认 `1.0`）、`speed`（默认 `2.0`）、`field`（默认 `0.5`）、`resistance`（默认 `2.0`）、`rail_length`（默认 `3.0`）、`field_mode`（默认 `in`）|
| `circuit` | `emf`（默认 `6.0`）、`r1`（默认 `2.0`）、`r2`（默认 `4.0`）|
| `circuit2` | `emf`（默认 `6.0`）、`r1`（默认 `2.0`）、`r2`（默认 `3.0`）、`rheostat`（默认 `4.0`）、`show_ammeter`（默认 `true`）、`show_voltmeter`（默认 `true`）|

**化学**

| kind | 参数 |
| --- | --- |
| `titration` | `analyte_conc`（默认 `0.1`）、`analyte_volume`（默认 `20.0`）、`titrant_conc`（默认 `0.1`）、`ka`（默认 `1.8e-05`）、`mode`（默认 `acid`）、`show_half`（默认 `true`）|
| `equilibrium` | `v_f0`（默认 `1.0`）、`v_r0`（默认 `0.2`）、`v_eq`（默认 `0.0`）、`t_change`（默认 `3.0`）、`jump_f`（默认 `0.6`）、`jump_r`（默认 `0.0`）、`tau`（默认 `0.55`）、`t_end`（默认 `8.0`）、`show_shift`（默认 `true`）|
| `molecule` | `smiles_list`（默认 `['CCO']`）|

列表参数（`intervals`、`points`、`knots`、`magnitudes`、`angles`、`charges`、`samples`、`transitions`、`processes`）接受 JSON 数组，默认值就是上面那组样例，所以空参数直接调也能画出一张像样的图。

### `exam_figure_check`

```
specs:   [{no, need: [标签], text: 题干}]
figures: {no: {marks: [...]}}
```

必需标注缺失时失败；题干写 `如图 7` 但没有图 7 也失败。多余标注只警告。

归一化会把 `G_∥`、`G_{\parallel}`、`G∥` 折到同一个 key。双向子串匹配，因为图上写 `R_1=2 Ω` 而题干只要求 `R_1`。**但单字符符号必须精确匹配**——`G` 是 `Gperp` 的子串，把它判为匹配曾经造成一次真实的假通过。

### `exam_figure_doctor`

解释器、解析到的 vendor 目录、选中的中文字体、各包版本、OMML 是否可用。`ok: false` 时带 `hint` 说明该跑哪条命令。

---

## 组卷

插件负责画图；组装 `.docx` 也在 Python 侧。`docxkit.py` 收了几个花掉若干渲染轮次才学会的排版规则：

* **中文段落左对齐。** Word 默认两端对齐会逐字撑开短行：一行四字答案曾渲染成 `顶 点 纵 坐 标`。
* **按长宽比定图宽。** 固定宽度会让宽扁的电路图只有 2.7 cm 高、竖长的三角形图却有 6.9 cm 高。应当定目标高度、算宽度、再夹紧。
* **图与图注用 `keep_with_next` 绑定**，避免 Word 把图和说明拆到两页。

公式走 **Word 原生 OMML**，不做成图片：`latex2mathml` → `MML2OMML.XSL` → 元素挂到段落上。公式里的中文（反应箭头上的条件）要给那些 run 打 `w:rFonts` 补丁，否则 Cambria Math 渲染成方框。

化学式走**普通 run + `font.subscript`**，不走 OMML。LibreOffice 导入 OMML 时忽略 `m:sty m:val="p"`，会把 `H₂O` 排成斜体；下标 run 到处都被识别。无机用 `=`、有机用 `→`，条件写在两个符号之间（`=点燃=`、`→点燃→`），即人教版教材写法。

---

## 验证

```bash
# 工具层：定义、render、output schema（不需要 Python）
node tests/smoke.mjs

# 引擎：绘图数学、校验器、化学
python tests/test_engine.py
```

两者都不依赖测试框架，故意不装 pytest——这个项目要服务的环境往往装不上，而跑不起来的测试等于没有测试。断言的是**绘图函数返回的数值**，不是像素。像素比对在一张画得漂亮但错误的图上会通过，而那正是本项目要防的失效模式。

### 参数网格

默认参数是最容易的那一档，也是「只测默认参数」唯一能看到的一档。所以每个数值参数都被单独扫到低值和高值（其余保持默认），每张图都必须同时满足：

- `layout.remaining` 为空——没有标签压线、压标签、出框
- 没有空白标签（图上声称标了的，必须真的画出来了）
- 没有 `curve_failures`——每条线的采样点附近都有墨
- 没有墨迹贴边

这一轮扫出来的问题，全是默认参数藏住的：0.2 m 的棒放在 3 m 导轨上，标签全被推出画面；竖直平移 2 会让原点跑到正弦图外面；棱长 0.3 的立方体，顶点名贴着自己的棱。它逼出来的规则只有一条，也是这个仓库反复重新学到的那条：**数据单位写的偏移和点单位写的字号不会一起缩放**，所以凡是靠常数定位的东西，要么对着最终视口定位，要么就不要定位。

图合理拒绝的输入——三边合不拢、窗口比弛豫时间还短、能级低于所请求的跃迁——会抛 `ValueError` 并说明原因，那是坏输入而不是布局缺陷。这些区间是从扫描范围里排除掉的，不是被静音掉的。

---

## 为什么不用 pip

在沙箱化的 DSH 安装里 `pip` 用不了，原因既不是网络也不是目标目录权限：

* `pip` 下载进 `tempfile.mkdtemp()`，然后往那个目录里写 wheel。文件沙箱允许创建目录、**拒绝往目录里写文件**——`PermissionError: [Errno 13]`，与网络无关。
* `site-packages` 同样不可写，所以 `.pth` 方案也不行。

`figdeps.py` 绕开全部：读镜像的 simple 索引、手工解析 `Requires-Dist`、`zipfile.extractall` 进一个普通目录，由 `env.bootstrap()` 挂到 `sys.path` 前面。

镜像按序尝试，PyPI CDN 放最后——从中国大陆访问，它常以 `SSL: UNEXPECTED_EOF_WHILE_READING` 掐断长传输，9 MB 的 wheel 一次都下不完。

还要注意镜像索引页把文件名放在**链接文本**里而不是 href 里：`<a href="../../packages/ab/cd/hash.whl#sha256=…">name-1.0.whl</a>`。用正则抓 href 什么也匹配不到。

另外两条沙箱约束值得记住：

* `MPLCONFIGDIR` 必须指向可写目录，否则 matplotlib 退出时每次都往 stderr 抛 `PermissionError`。
* PNG 写不进刚 `mkdtemp()` 出来的目录，所以测试写到自身旁边的 scratch 目录。

---

## 许可

MIT —— 见 [LICENSE](LICENSE)。依赖许可均为宽松型（BSD / MIT / Apache-2.0），逐项列在 [THIRD-PARTY.md](THIRD-PARTY.md)。本仓库不内嵌任何第三方代码。
