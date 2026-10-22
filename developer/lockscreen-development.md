# 锁屏配置完整参考

适用范围与源码基线见[扩展开发总览](/developer/extensions)。锁屏由静态 JSON/PNG 场景和可选局部 Lua 组成；使用标准、无压缩的 `.lspack` 发布。锁屏是系统显示和输入状态，不等于整机深睡眠。

初学者先按[锁屏入门教程](/developer/lockscreen-tutorial)制作完整静态模板和时钟；想知道系统如何锁定、调度和解锁，看[运行原理](/developer/extensions-runtime#锁屏从锁定到解锁)。时间、字数、诗句和通知的用法见[锁屏数据接口](/developer/lockscreen-data)。本页保留精确字段和边界，供写完第一个模板后查询。

## 最小静态模板

在自己的工作文件夹建立 my-lock 源目录，无需固件仓库：

```text
my-lock/
├── lockscreen.json
└── images.json
```

`lockscreen.json`：

```json
{
  "version": 1,
  "模板名称": "我的锁屏",
  "canvas": {"width": 684, "height": 1216, "background": 255},
  "font_file": "system",
  "texts": [
    {"text": "阅读暂停", "x": 48, "y": 560, "width": 588, "height": 80,
     "font_size": 44, "gray": 0, "align": "center"}
  ]
}
```

`images.json` 即使没有图片也必须存在，内容为 `[]`。按[打包与验证](/developer/extension-packaging)生成包后，复制到 SD 卡 `/.justread/screen/`，或从阅读设置中的锁屏模板页导入 `.lspack`。模板名用于菜单展示。安装成功后仍需在设备进入/退出锁屏验证实际画面。

## JSON schema

JSON 使用 UTF-8。固件拒绝重复键、未列入对应对象允许列表的字段、错误类型与越界整数；不能在配置中自行增加 `description`、`author`、包版本或权限字段。包的发布版本写在发布说明/市场元数据中，`version: 1` 仅表示 schema 版本。

| 资源 | 固件解析/加载上限 |
| --- | --- |
| `lockscreen.json`、`images.json` | 每份非空且最多 64 KiB；每份最多 1536 个 parser token，结构过于复杂也可能被拒绝 |
| 静态图片、静态文字 | 各最多 32 项 |
| 静态资源相对路径 | 最多 159 字节；禁止绝对路径、空段、`.`/`..` 段、反斜杠、冒号和控制字符 |
| PNG、随包 TTF | 每文件最多 2 MiB；PNG 另有尺寸、像素和编码限制 |
| Lua 源码 | 非空且最多 64 KiB；执行预算与普通插件共用 |

这些上限是分别校验的，不表示把每项都用满仍能成功加载；设备仍可能因内存不足回退。ZIP/市场的体积和类型限制另见[打包规范](/developer/extension-packaging)。

### 顶层字段

| 字段 | 必需 | 类型与约束 |
| --- | --- | --- |
| `version` | 是 | 整数，必须为 1 |
| `模板名称` | 发布时必需 | 非空字符串，UTF-8 最多 95 字节；旧 `name` 是兼容别名，新包用中文字段 |
| `canvas` | 是 | `{width, height, background?}`；宽高整数 1–4096，background 0–255，默认 255 |
| `texts` | 是 | 0–32 项数组；纯 Lua 模板也填 `[]` |
| `font_file` | 否 | `"system"` 或包内安全相对 `.ttf` 路径；字体最多 2 MiB |
| `glyphs` | 否 | PNG ASCII 等宽图集，见下文 |
| `lua` | 否 | 单个脚本配置，见下文 |

新 `.lspack` 不写 `template`。固件保留的旧外置 JSON + ZIP 加载逻辑不作为新包格式；所有资源都直接位于同一个 `.lspack` 中。

### 坐标与静态文字

静态矩形统一含 `x`、`y`、`width`、`height`：`x/y` 为 -4096–4096，宽高 1–4096。允许静态元素部分越界，最后裁切。`canvas.width > canvas.height` 选择横屏，否则竖屏。静态坐标按设计 canvas 分别缩放到目标逻辑宽高；字号取两个方向缩放结果的较小值。

`texts` 每项可用字段：

| 字段 | 必需 | 含义 |
| --- | --- | --- |
| `text` | 是 | UTF-8 字符串，最多 1023 字节 |
| `x/y/width/height` | 是 | 文本排版框，单位是 canvas 像素 |
| `font_size` | 是 | 整数 1–256；设备字号还会随 canvas 缩放 |
| `gray` | 否 | 0–255，默认 0 |
| `align` | 否 | `left`、`center`、`right`，默认 left |

静态文字支持 UTF-8 换行排版；行高为字号的约 125%，超出文本框高度的行不绘制。绘制顺序为背景色 → `images.json` 数组顺序 → `texts` 数组顺序 → Lua 绘制。Lua 位于最上层。

### images.json

```json
[
  {"file": "images/book.png", "x": 48, "y": 100, "width": 588, "height": 400, "fit": "contain"}
]
```

顶层必须是数组，最多 32 项。每项仅可包含 `file`、`x`、`y`、`width`、`height`、`fit`。`file` 为包根目录相对 PNG 路径，矩形必填，`fit` 默认 `contain`（保持比例居中），也可为 `stretch`（拉伸）。静态图片无需出现在 Lua 代码中；Lua 动态小图也无需列入静态图片数组。

PNG 必须为 **8-bit、非交错**，支持灰度、RGB、索引色、灰度 Alpha、RGBA；彩色转换为灰度，Alpha 合成到背景。每文件最多 2 MiB，每边最多 4096 px，总像素最多 1048576。常见导出工具生成的 1-bit 单色 PNG、16-bit PNG、交错 PNG 均不适用，即使肉眼看起来相同。

### 字体与 glyphs 图集 {#glyphs}

`font_file: "system"` 使用当前用户字体，没有自选字体时使用设备系统字体。锁屏前重新打开字体，解锁后恢复阅读字体。省略字体字段时使用当前可用 UI 字体，不应据此保证特定字形覆盖。包内 TTF 适用于本地模板；当前云市场拒绝 `.ttf` 成员。

```json
{
  "file": "clock-glyphs.png",
  "characters": "0123456789:-",
  "cell_width": 96,
  "cell_height": 180
}
```

上例是 `glyphs` 对象，放在 `lockscreen.json` 顶层。字符按声明顺序横向排列；PNG 宽度必须恰好为 `cell_width × 字符数`，高度为 `cell_height`。字符共 1–31 个，唯一，ASCII 33–126（不含空格）；单元格宽高 1–512，并同时满足 PNG 尺寸、像素和体积限制。脚本用 `ui.glyph("0", x, y)` 绘制单字符。图集用于大字号/固定字体效果，须附字体授权允许的许可证。

## Lua 配置与生命周期

在最小模板顶层加入以下字段，并在源目录根部增加 `lockscreen.lua`：

```json
"lua": {
  "file": "lockscreen.lua",
  "when": "locked",
  "interval_ms": 60000,
  "area": {"x": 48, "y": 800, "width": 588, "height": 160},
  "refresh": "partial_gray",
  "ancs": false
}
```

这是 JSON 字段片段，不是独立 JSON 文件。脚本入口仍返回含 `on_draw()` 的 table，源码最多 64 KiB；VM 预算与公共绘图签名见 [Lua 插件 API](/developer/lua-plugin-api)。

| `lua` 字段 | 规则 |
| --- | --- |
| `file` | 必填；安全的**根目录文件名**，以 `.lua` 结尾；当前 parser 不接受子目录，建议固定 `lockscreen.lua` |
| `when` | 必填；`before_lock`、`before_open` 或 `locked` |
| `area` | 必填；设计 canvas 坐标矩形，`x/y >= 0` 且完整位于 canvas 内 |
| `interval_ms` | `locked` 必填；整数 1000–86400000；其他模式若提供也须满足该范围 |
| `hold_ms` | `before_open` 必填；整数 250–600000；其他模式若提供也须满足该范围 |
| `refresh` | 默认 `partial_bw`；还接受 `partial_gray`、`full_gray`、`full_gc16` |
| `ancs` | 默认 false；布尔值；true 时提供系统 ANCS 快照；旧 `ble` 字段兼容，新包用 ancs |

一个模板只有一个 `lua` 配置，不能同时声明三种 `when`。

| 模式 | 实际调用 |
| --- | --- |
| `before_lock` | 进入锁屏时启动 VM、`on_open`，执行一次 `on_tick(now_ms)`（若有）再 `on_draw`；无周期调度 |
| `locked` | 进入时同上；之后定时到期或 ANCS 内容变化时执行 `on_tick` + `on_draw` |
| `before_open` | 进入时仅静态锁屏；请求解锁时启动 VM、`on_open` + `on_draw`，显示并等待 `hold_ms` 后恢复原界面；这一分支不调用 `on_tick` |

正常销毁 VM 时可执行 `on_close`，故障后不保证调用。锁屏不投递 `on_event`，也不提供 `plugin_exit`。不能通过脚本控制系统解锁、休眠或 BLE 连接。

`locked` 的 timer 在上一次显示刷新完成后重新计时，所以可见周期还包含 Lua 绘制和波形耗时。它不是固定频率动画或准确闹钟；时间内容应读 `clock.now()`，不能靠累计 tick 推算。

## Lua 局部画布与时钟示例

`ui.size()` 返回**已缩放后的 area 宽高**，没有普通插件系统栏。Lua 的整数坐标、字号、glyph 单元格和 `ui.image` 输出尺寸是实际局部像素，不能假设与设计 canvas 同尺寸；面积改变时应按 `ui.size()` 适配。锁屏 host 对矩形/线段/文字进行边界检查，越界可能返回 false；尤其文字不会自动裁短或换行，整行宽度必须放得下。

```lua
local M = {}

function M.on_draw()
    local w, h = ui.size()
    local now = clock.now()
    local value = now and string.format("%02d:%02d", now.hour, now.minute) or "--:--"
    local px = math.min(64, math.floor(w / 4), h - 32)
    -- 擦掉旧时间；不用 ui.clear，避免它自动申请全灰刷新。
    ui.rect(0, 0, w, h, 255, true)
    if px >= 8 then ui.text(16, 16, value, px, 0) end
    ui.refresh("partial_gray", 0, 0, w, h)
end

return M
```

每次锁屏绘制前，宿主会先把静态场景重绘到内存 framebuffer，再执行 Lua。只请求局部刷新时，面板未刷部分仍保留上一帧；不要因“只刷新脏区”就假设内存中的其他动态内容仍在。若将多个动态区分开刷新，后续全屏刷新前应确保所有动态内容都重新画好。

### 刷新模式要分清配置与函数

| 接口 | 接受值 | 语义 |
| --- | --- | --- |
| `lua.refresh`（JSON） | `partial_bw` / `partial_gray` / `full_gray` / `full_gc16` | 没有显式请求时的默认刷新策略；`full_gray` 走 GL16，`full_gc16` 走 GC16 清屏 |
| `ui.refresh()`（Lua） | `partial_bw` / `partial_gray` / `full_gray` / `full_bw` | 显式请求；不接受 `full_gc16`；局刷在 area 内，全刷模式由 adapter 扩成整屏 |

`ui.clear()` 和 `ui.invalidate()` 隐含请求 `full_gray`。需要仅局刷时，使用 `ui.rect` 擦背景并显式请求局部刷新。当前 host 每次 draw 最多接收 4 个刷新请求，包含 `ui.clear` 隐含请求；多出的请求返回 false。

首次进入锁屏由系统整屏显示，不保证逐项执行脚本当次提交的局刷请求。周期阶段优先使用脚本显式请求；没有请求时按 JSON 刷新。例外：`ancs: true` 且配置 `full_gray` 时，周期没有显式请求就不刷屏，用于通知/时钟分别判脏后局刷。内容变化筛选需由模板实现，并非所有 ANCS 模板自动隔离刷新区域。

## 锁屏专用只读接口

| 调用 | 返回值与失败行为 |
| --- | --- |
| `clock.now()` | `{year, month, day, hour, minute, second}` 本地时间；系统时间无效时 `nil` |
| `config.get(key)` | 字符串或 `nil`；成功值最多 511 字节；转换数值须用 `tonumber` 并提供兜底 |
| `poetry.count(language)` | 可用条数 0–350；语言为 `zh-Hans` 或 `zh-Hant`，未知语言返回 0 |
| `poetry.get(language, index)` | `{text, title, author, dynasty}` 或 `nil`；index 从 1 开始，1–350 |
| `ancs.connected()` | 是否连接系统 ANCS 对端，boolean；仅 `ancs: true` 时注册 |
| `ancs.notifications()` | 最多 8 条倒序通知快照数组；每项 `{id, app, title, message}`；仅 `ancs: true` 时注册 |
| `ui.glyph(character, x, y)` | 仅 `on_draw`；一个 ASCII 字符，需存在于 glyphs；返回 boolean |
| `ui.image(file, x, y, width, height)` | 仅 `on_draw`；绘制当前包内 PNG，返回 boolean；输出每边 1–96 px |

锁屏 `ui.text` 字号为 8–240 px，文本仍最多 512 字节。所有只读内容都可能缺失，脚本必须可离线显示静态兜底。

`ui.image` 路径最多 159 字节，只接受 ASCII 字母、数字、`_`、`-`、`/`、`.`，不能绝对寻址，不能出现 `..`，后缀须为小写 `.png`。图片解码后按目标尺寸缓存，解锁释放；仍受 PNG 源图限制。此接口适合小图标，大图用静态 `images.json`。

### config 的来源

- `today_words`：系统当前今日阅读字数，以十进制字符串返回。
- `current_time`：系统本地 `HH:MM`，未校时为 `--:--`。
- 其余 key：从 SPIFFS `/spiffs/lockscreen-vars.json` 的 `variables` 对象读取字符串。文件最多 4096 字节，结构是 `{"version":1,"variables":{"lock_label":"藏书一隅"}}`。key 最多 63 字节，字母、数字、`_`、`-`、`.`。

上述两个系统 key 优先于 SPIFFS 同名值。这个文件由固件管理，不是包内配置，也不是允许模板任意读 SD 的接口；新自定义 key 必须写清所需固件配置，不能假设安装模板即可写入变量。

### ANCS 与诗句

ANCS 服务统一管理配对、重连、通知缓存；未声明 ANCS 的锁屏不会得到 `ancs` 表。iPhone 侧需确认配对并允许通知共享，通知也可能为空。`app` 是应用标识，不是图标；需在模板中映射到包内 PNG，未知应用提供通用图标。通知字段缓冲最多为 app 47、title 127、message 255 字节，须处理截断及空内容。旧 `ble.connected/notifications` 是只读兼容别名，不能用来操作连接。

诗句由系统维护 `/.justread/poetry/weekly.json`，包含简繁两组各 350 条；下载依赖系统联网策略，Lua 不负责联网。诗句字段缓冲最多为 text 255、title 159、author 95、dynasty 63 字节。接口返回 0/nil 时使用内置短句，不要假设首次安装一定有诗库。

不需要读取内部样例：文档提供了[完整时钟模板](/developer/lockscreen-tutorial)和[时间、字数、诗句、通知组合模板](/developer/lockscreen-data)。把页面列出的文件按名称保存即可，再用[独立工具](/developer/extension-packaging#packer)打包。

## 故障回退与发布验收

模板加载失败时系统使用默认静态场景；Lua 启动或绘制失败后停止实例并回退可用静态锁屏。应提供有意义的背景/文字，避免 Lua 失败后只剩空白。实机检查横竖方向、字体缺字、脚本越界返回、时钟未校准、SD 资源缺失、ANCS 未配对、解锁恢复和反复锁定后的资源释放。周期 Lua 活跃会影响系统软休眠策略，发布说明须记录周期和功耗验证情况。

具体打包、结构检查和固件回归入口见[打包与验证](/developer/extension-packaging)，对外说明使用[发布文档模板](/developer/extension-release-template)。
