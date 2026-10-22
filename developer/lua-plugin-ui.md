# 绘图、坐标和刷新 API 详解

这篇回答“每个绘图参数怎么填”和“为什么代码改了，画面还没变”。建议先完成[第一个插件](/developer/plugin-tutorial)。下面的短代码块是用法片段，除非写明完整程序，否则需要放进自己的插件 table 和回调；不是每一块都可以单独保存成 `main.lua`。

## 先会读函数说明

例如：

```text
ui.rect(x, y, w, h, gray = 0, filled = false, stroke = 1) → boolean
```

这是文档中的签名，不是要原样执行的 Lua。x/y/w/h 是必填参数；`gray = 0` 表示省略这个参数时默认黑色；箭头后的 boolean 表示返回 `true` 或 `false`。

实际调用写成：

```lua
ui.rect(24, 160, 200, 80, 0, false, 2)
```

含义是：左上角 `(24, 160)`、宽 200、高 80、黑色、只描边、线宽 2 px。参数按位置对应，不能写成 Lua 不支持的 `ui.rect(x=24, y=160, ...)`。

要使用后面的可选参数，同时保留前面参数的默认值，可以在支持默认值的位置传 `nil`。初学时建议按示例显式填出需要的参数，更容易核对。

## ui.size：先知道自己能画多大

```lua
local width, height = ui.size()
```

Lua 可以一次返回多个值，这里依次赋给 width 和 height。普通插件拿到的是应用画布，已扣除系统栏；锁屏 Lua 拿到的是 area 大小。不要为这两种脚本都写死 684 × 1216。

默认小纸 Pico 上，普通插件没有底栏时画布为 684 × 1112，有底栏时为 684 × 1032；其他尺寸下应查询接口。标题和底栏元数据在入口返回后才读取，所以在 `on_open` 或 `on_draw` 查询最终大小。

```lua
-- 放在 on_draw 内：画布左右各留 24 像素。
local w, h = ui.size()
ui.rect(24, 32, w - 48, 80, 0, false, 2)
```

x/y 是左上角，w/h 是宽高。要放一个右边距为 24、宽为 100 的按钮，其 x 应为 `w - 24 - 100`，不能直接把 x 写成 `w - 24`。

普通插件绘制由宿主映射并限制在应用区域；锁屏很多绘图操作会直接拒绝超出 area 的内容。内容应留在合法范围内，不把裁切当作布局算法。

## ui.clear：清空整个画布

```text
ui.clear(gray = 255) → boolean
```

只允许在 `on_draw` 调用。`255` 为白、`0` 为黑。它既填背景，也自动请求 `full_gray`，适合第一次学习、整体页面变化或需要重画完整画布的场景。

```lua
function M.on_draw()
    ui.clear(255)
    ui.text(24, 32, "本页内容", 32, 0)
end
```

“清空”不会删除 Lua 变量或存档，只改变画布背景。想清空计数器，要在事件中把 count 设为 0，再让绘图函数显示新值。

## ui.rect：画矩形、边框和擦除区域

```text
ui.rect(x, y, w, h, gray = 0, filled = false, stroke = 1) → boolean
```

宽高必须大于 0；线宽会限制到 1–8。`filled` 用真正的 `true/false`：Lua 中数字 0 也被当作真，不能用 0 表示“不填充”。颜色值限制到 0–255。

```lua
-- 以下片段放在 on_draw 内。
ui.rect(24, 32, 200, 80, 0, false, 2)    -- 黑色边框
ui.rect(24, 144, 200, 80, 160, true)     -- 灰色实心矩形
ui.rect(24, 256, 200, 80, 255, true)     -- 白色实心，擦掉旧内容
```

局部擦除时不用 `ui.clear`，可以避免它附带的全灰请求。擦除矩形要覆盖旧内容的完整范围；旧值“1000”变成“9”时，不能只擦新数字的宽度，否则旧的几个 0 可能留下。

## ui.line：端点连线

```text
ui.line(x0, y0, x1, y1, gray = 0, stroke = 1) → boolean
```

它的后两项是**终点坐标**，与 rect 的宽高不同：

```lua
ui.line(24, 128, 300, 128, 0, 2)  -- 从 (24,128) 到 (300,128)
```

可用于分隔线和简单图形。锁屏要求端点在 area 内；普通插件由适配层做裁切。线宽 1–8，灰度 0–255。

## ui.text：画一行字

```text
ui.text(x, y, text, px, gray = 0) → boolean
```

text 是 UTF-8 字符串，最多 512 **字节**；px 是像素字号，普通插件为 8–128，锁屏为 8–240。x/y 指文本绘制起点的左上位置，宿主处理字体基线。函数不会自动换行，也不会自动水平居中。

```lua
ui.text(24, 32, "阅读时间", 28, 0)
ui.text(24, 88, tostring(12) .. " 分钟", 40, 0)
```

中文常用字通常占多个 UTF-8 字节，512 字节不等于 512 个汉字。当前公共 API 没有 `ui.measure_text`，不能照搬网页的自动排版方式。界面里应为文字留足空间、限制内容长度，必要时由作者拆成多行分别绘制。

锁屏会检查整行文本是否放得下，太宽可能返回 false。字号很大但区域高度很小也会失败。先用短文字和较小字号确认路径，再加长内容。

### 怎样截短中文而不截坏字节

不要对任意中文直接 `string.sub(value, 1, 20)`，那是按字节截取，可能切到一个字的中间。下面是一个处理有效 UTF-8 字符串的辅助函数：

```lua
local function first_chars(value, count)
    local text = tostring(value or "")
    local stop = utf8.offset(text, count + 1)
    return stop and string.sub(text, 1, stop - 1) or text
end
```

`first_chars("阅读暂停", 2)` 得到“阅读”。它限制字符数量，不保证某个字体下的实际像素宽度；对未知外部内容仍需留出宽度余量，或按行拆分。

## ui.refresh：请求把像素更新到屏幕

```text
ui.refresh(mode, x = 0, y = 0, w = canvas_w, h = canvas_h) → boolean
```

坐标相对当前画布，宽高大于 0。省略宽高时会使用**整个画布宽高**，不是从 x/y 到右下角的剩余尺寸。写局部区域时最好把四个坐标参数全写出。

| mode | 初学者可怎样理解 |
| --- | --- |
| `partial_bw` | 请求局部黑白更新，适合没有灰阶的简单内容 |
| `partial_gray` | 请求局部灰度更新，适合含灰阶的文字/图像区域 |
| `full_bw` | 请求全黑白模式；最终刷新范围和波形由宿主处理 |
| `full_gray` | 请求完整灰度模式；普通插件与锁屏的适配映射不同 |

锁屏 JSON 的 `refresh` 还有 `full_gc16`，但 Lua 函数不接受它；这两套配置不能混着用。物理刷新由系统队列安排，可能合并或升级，返回 true 不是“面板已经完成更新”。

```lua
-- 放在 on_draw 中：先擦，再画，再请求这一块。
ui.rect(24, 80, 260, 80, 255, true)
ui.text(24, 88, "9", 48, 0)
ui.refresh("partial_gray", 24, 80, 260, 80)
```

单独绘图一般不会自动告诉系统应该更新哪一块。普通输入事件后宿主会安排重绘和默认刷新，因此上面的局部请求也不保证能把宿主已提出的整屏请求缩小。需要优化真实刷新范围，必须在目标设备观察；不要只看 Lua 参数就声称已经实现纯局刷。

## ui.invalidate：数据变了，请重画 {#invalidate}

```text
ui.invalidate() → boolean
```

它请求整画布 `full_gray` 并标记重绘，常用于 `on_tick` 中发现状态变化时。它自己不生成文字、不清背景；随后由 `on_draw` 使用新数据绘图。

下面是一个**完整插件**，每约 5 秒重新读取一次设备状态。没有状态变化时不请求重画：

```lua
local M = { title = "电量观察" }
local last_check = nil
local battery = -1

local function read_battery()
    local status = device.status()
    return status and status.battery or -1
end

function M.on_open()
    battery = read_battery()
end

function M.on_tick(now_ms)
    if last_check and now_ms >= last_check and now_ms - last_check < 5000 then
        return
    end
    last_check = now_ms
    local next_value = read_battery()
    if next_value ~= battery then
        battery = next_value
        ui.invalidate()
    end
end

function M.on_draw()
    ui.clear(255)
    local label = battery >= 0 and (tostring(battery) .. "%") or "未知"
    ui.text(24, 32, "电量：" .. label, 36, 0)
end

return M
```

`on_tick` 大约每 100 ms 被调度，不代表设备状态每 100 ms 会重新测量；`device.status` 返回的是系统缓存。上例自己节流到约 5 秒，且只在值改变时要求重画，也处理了传入计时值倒退/回绕的情况。

## 两种失败要分别理解

**返回 false**：函数存在、参数类型可读，但宿主没能接受这次操作，例如区域放不下、设备能力失败。可以显示替代内容或记录简短日志。

**Lua 错误**：例如把字号写成字符串、在 on_event 中画图、调用不存在的 API。错误会让实例进入故障状态，而不只是这一行返回 false。应修改源码并重新启动，不靠每次 tick 无限重试。

```lua
-- 放在 on_draw 中观察绘制失败，日志不直接显示在画布上。
local ok = ui.text(24, 32, "你好", 32, 0)
if not ok then print("text draw failed") end
```

精确的预算和支持范围见[API 总览](/developer/lua-plugin-api)。锁屏的小图和字形接口见[锁屏数据与图像](/developer/lockscreen-data)。
