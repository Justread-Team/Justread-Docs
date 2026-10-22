# Lua 插件 API 完整参考

适用范围与核对版本见[扩展开发总览](/developer/extensions)。本文覆盖普通 SD 卡插件；锁屏脚本的额外接口与时序见[锁屏模板规范](/developer/lockscreen-development)。

第一次接触 Lua 或回调，请先读[运行原理](/developer/extensions-runtime)和[插件入门教程](/developer/plugin-tutorial)。逐个函数的解释、实际调用与错误示例在[绘图详解](/developer/lua-plugin-ui)、[设备与存档详解](/developer/lua-plugin-services)。本页用于集中查询签名和限制。

## 目录、入口与最小示例

```text
/.justread/plugins/counter/
├── main.lua
└── icons/                 # 可选，仅目录安装能直接读取
    └── home.rui48
```

插件名使用 ASCII 字母、数字、`_`、`-`、`.`，不能为 `.` 或 `..`，最多 31 字节。直接运行包时整个文件名（包括 `.jrpack`）也受此限制。最多发现 16 个插件，按名称排序；不要依赖超出扫描上限的插件仍会显示。列表使用目录名或包文件名，`title` 用于启动后的系统顶栏。

入口必须是非空 UTF-8 Lua 文本，最多 64 KiB，返回包含 `on_draw()` 的 table。不支持预编译字节码、多文件动态加载或 `manifest.json` 声明权限/版本。

以下内容可直接保存为 `counter/main.lua`；例子使用目录安装以支持持久化：

```lua
local M = { title = "点击计数" }
local count = 0

function M.on_open()
    count = math.max(0, math.min(999999, tonumber(storage.read("count.txt")) or 0))
end

function M.on_draw()
    local w, h = ui.size()
    ui.clear(255)
    ui.text(24, 32, "点击画布计数", 28, 0)
    ui.text(24, 88, tostring(count), 48, 0)
    ui.rect(24, 160, w - 48, math.min(96, h - 184), 0, false, 2)
end

function M.on_event(name, x, y, key)
    if name == "tap" then
        count = (count + 1) % 1000000
        if not storage.write("count.txt", tostring(count)) then
            print("count save failed")
        end
        -- 宿主会在事件回调后请求重绘；这里只改状态。
    end
end

return M
```

计数变化即保存，避免仅在 `on_close` 保存：故障退出不保证调用清理回调。若发布为本地直接运行的 `.jrpack`，应去掉持久化依赖或清楚说明[安装差异](/developer/extension-packaging#installation)。

## 生命周期与事件 {#lifecycle}

源码顶层执行 → 读取元数据 → 重算画布 → `on_open()` → 根据需要 `on_draw()` / `on_event()` / `on_tick()` → 正常退出 `on_close()` → 销毁 VM。每次启动都是新 VM。标题与导航元数据只在启动时读取，后续修改 Lua table 不会重新配置系统栏。应在 `on_open` 或 `on_draw` 中查询最终 `ui.size()`，避免在源码顶层缓存未扣除底栏的尺寸。

| 回调 | 是否必需 | 语义 |
| --- | --- | --- |
| `on_open()` | 否 | 初始化状态、读取私有存档；不能绘图 |
| `on_draw()` | 是 | 维护应用画布；只有这里能调用绘图函数 |
| `on_event(name, x, y, key)` | 否 | 更新状态；成功执行后宿主请求重绘 |
| `on_tick(now_ms)` | 否 | 约 100 ms 调度一次，非精确周期；状态变化后用 `ui.invalidate()` / `ui.refresh()` 请求重绘 |
| `on_close()` | 否 | 正常退出时清理；出错后不再执行此回调 |

`now_ms` 为单调毫秒值，经 32 位宿主计时传入，不是 Unix 时间。长时间运行应处理回绕；不要用忙等待模拟定时器，也不要在每次 tick 中无条件全刷。

| `name` | `x`, `y` | `key` |
| --- | --- | --- |
| `tap` | 画布内点击位置 | 0 |
| `swipe_left/right/up/down` | 滑动结束位置；起止点都须在画布内 | 0 |
| `navigation` | `x` 为 1 起始导航项序号，`y = 0` | 0 |

当前 Pico 按键回调直接退出插件，未向 Lua 分发历史文档中的 `key` 事件。系统顶栏返回也直接退出；不能拦截。`on_event` 的第四参数保留在签名中，不表示此端口已提供按键输入。

## 系统栏、坐标与导航 {#canvas}

状态栏和顶栏由系统绘制。`ui.size()` 返回应用画布尺寸，绘图、输入和刷新坐标均以画布左上角 `(0, 0)` 为原点。宿主限制绘制区域，插件不得自行覆盖系统栏。画布不会在每次绘制前自动清空；需要擦除旧内容时显式填背景。

顶栏返回热区向画布延伸 16 px；底部导航热区也向画布延伸 16 px。交互内容应避开上下相邻边缘。点击系统状态栏由宿主刷新设备状态，不传给插件。

```lua
local M = {
    title = "示例应用",
    navigation_active = 1,
    navigation = {
        { label = "首页", icon = "icons/home.rui48" },
        { label = "收藏" },
    },
}
-- 还必须实现 M.on_draw() 并 return M。
```

`navigation` 是连续数组，1–5 项，每项须有非空 `label`。1 项为单个底部操作，2–5 项显示选中指示；不提供则无底栏。启用后 `ui.size()` 扣除底部 80 px。无效导航整体忽略。`navigation_active` 从 1 开始，缺省/无效时选第一项；宿主先更新选中状态再发事件。

标题缓冲允许 95 字节，导航 label 47 字节，icon 路径 95 字节；超长元数据按 UTF-8 边界截断。资源路径仍须满足安全路径规则。

`.rui48` 为无文件头、恰好 288 字节的 48 × 48 单色位图。逐行从上到下，每行从左到右，最高位优先；1 黑、0 白。宿主负责槽位和热区。缺失或错误图标回退到系统四圆格子图标。普通插件没有用于正文绘制 PNG 或 `.rui48` 的 API。

### 底部导航完整例子

以下代码可单独保存为 main.lua，不需要图片。底部两项由系统绘制；用户点“收藏”时，系统先改变选中指示，再把序号 2 作为 x 传给 on_event。脚本用这个序号决定正文显示什么，而不是自己再画一套底部按钮。

```lua
local M = {
    title = "双页示例",
    navigation_active = 1,
    navigation = {
        { label = "首页" },
        { label = "收藏" },
    },
}
local page = 1

function M.on_event(name, x, y, key)
    if name == "navigation" then page = x end
end

function M.on_draw()
    local w, h = ui.size()
    ui.clear(255)
    local label = page == 1 and "这是首页" or "这是收藏页"
    ui.text(24, 32, label, 32, 0)
    ui.text(24, 88, "可用高度：" .. tostring(h), 24, 80)
end

return M
```

`page` 是你的正文状态，宿主选中项是系统栏状态，两者通过 navigation 事件同步。不要只在事件中修改 `M.navigation_active` 期待系统重新读取元数据；这个字段仅用于启动初值。若初值改成 2，示例的 `local page` 也应初始化为 2。

## 公共绘图与刷新 API

以下函数也用于锁屏 Lua，但画布、字号和刷新适配不同。坐标与尺寸使用整数；灰度 0 黑、255 白，输入值钳制到该范围；线宽钳制为 1–8。绘图/刷新返回 `boolean` 表示宿主接受请求，不代表面板波形已经完成；参数类型或范围错误可能抛出 Lua 错误并停止实例。

| 调用 | 参数与结果 |
| --- | --- |
| `ui.size()` | 返回 `width, height` |
| `ui.clear(gray = 255)` | 仅 `on_draw`；填整个局部画布，并自动请求 `full_gray` |
| `ui.rect(x, y, w, h, gray = 0, filled = false, stroke = 1)` | 仅 `on_draw`；`w/h > 0`；填充或描边矩形 |
| `ui.line(x0, y0, x1, y1, gray = 0, stroke = 1)` | 仅 `on_draw`；绘制线段 |
| `ui.text(x, y, text, px, gray = 0)` | 仅 `on_draw`；普通插件字号 8–128 px，UTF-8 文本最多 512 字节；左上角定位，单行，不自动换行 |
| `ui.refresh(mode, x = 0, y = 0, w = canvas_w, h = canvas_h)` | `w/h > 0`；刷新区域映射到应用画布；省略 `w/h` 时是整画布尺寸，不是从 `x/y` 到边界的剩余尺寸 |
| `ui.invalidate()` | 请求整画布 `full_gray` 并标记重绘 |

`ui.refresh` 接受 `full_bw`、`full_gray`、`partial_bw`、`partial_gray`。普通插件适配器将 `full_gray` 映射到系统 `RUI_GC16`；这是该端口的实现，不应推断其与锁屏 GL16 相同。系统队列可能合并或升级请求，插件不能直接驱动面板。

全画布绘制可用 `ui.clear`。要保留局刷效果，用 `ui.rect(..., 255, true)` 擦除所需矩形，再请求该矩形；同时调用 `ui.clear` 会额外产生全灰刷新请求。在事件或 tick 中仅改状态和请求刷新，在 `on_draw` 中完成绘制。

## 普通插件专用 API

| 调用 | 返回值与限制 |
| --- | --- |
| `device.status()` | `{battery, temperature_centi_c, temperature_valid, sd_ready}` 或 `nil`；battery 为百分比，未知可为 -1；温度单位 0.01°C，先检查有效标记 |
| `device.buzzer(frequency_hz, duration_ms)` | `boolean`；200–5000 Hz、5–250 ms，成功调用间至少 150 ms；不满足间隔返回 false |
| `reader.status()` | `{reading, title, page, page_count, chapter, chapter_count}` 或 `nil`；有书时页/章节从 1 开始，没有书时位置与总数为 0 |
| `storage.read(path)` | 数据字符串或 `nil`（缺失、无法读取、超过上限等）；单值最多 4096 字节 |
| `storage.write(path, data)` | `boolean`；数据字符串最多 4096 字节；宿主建目录，以临时文件 + rename 写入 |
| `plugin_exit()` | 返回 true，设置退出请求；宿主消费请求后退出，不是立即中断当前函数 |
| `print(...)` | 无返回；输出有界日志，消息最多 255 字节；普通插件日志 tag 为 `lua_plugin` |

`storage` 映射到 `/.justread/plugins/<当前名称>/data/<path>`。路径最多 96 字节，使用字母、数字、`_`、`-`、`.` 及 `/` 分隔；不能为绝对路径，不能有空段、`.` 或 `..` 段。4096 字节是单值限制，不是自动管理的插件总配额。不要把通知、个人配置等敏感内容写入日志。

## Lua 环境与失败处理

开放 base、`table`、`string`、`math`、`utf8`，`print` 替换为宿主日志。没有 `io`、`os`、`package`、`debug`、`coroutine`；`dofile`、`loadfile`、`load`、`collectgarbage`、`require` 不可用。当前解释器依赖为 `espressif/lua` 5.5.0；固件样例按 32 位数值环境编写，避免依赖超大整数或双精度运算结果。

| 资源 | 当前上限 |
| --- | --- |
| 入口源码 | 1–65536 字节 |
| Lua 分配总量 | 256 KiB |
| 每次源码顶层执行/回调 | 100000 条指令预算，hook 粒度 1000 |
| 顶层、事件、tick、生命周期回调 | 80 ms 时间预算 |
| `on_draw` | 500 ms 时间预算 |

预算由 Lua hook 检查，不是可用于实时任务的截止时间保证；宿主 I/O 也会影响耗时。语法、类型、预算、内存等错误会导致启动失败或实例停止；绘制/tick 故障后不应假设 `on_close` 会运行。开发者须验证能返回列表并重新启动。

## 可参考样例

无需读取固件源码即可照着[插件教程](/developer/plugin-tutorial)保存完整 hello 和计数器入口；[绘图详解](/developer/lua-plugin-ui#invalidate)另有电量观察完整插件。它们覆盖基本绘制、事件、存档与 tick。用[文档提供的独立工具](/developer/extension-packaging#packer)制作分发包；运行结果仍应在目标设备验证。
