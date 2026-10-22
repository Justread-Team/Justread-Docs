# 锁屏怎样显示时间、诗句和通知

先完成[时钟锁屏教程](/developer/lockscreen-tutorial)，再读本篇。这里说明每种数据从哪里来、拿到的值是什么，以及数据缺失时怎样继续显示。它们是锁屏 Lua 接口；不能直接复制到普通插件中使用。

## clock.now：读取系统时间

```lua
local now = clock.now()
```

成功时返回本地时间表：year（年）、month（月）、day（日）、hour（时）、minute（分）、second（秒）。系统没有有效时间时返回 nil。格式化由作者自己决定：

```lua
-- 放在锁屏 on_draw 中。
local now = clock.now()
local text = "时间尚未校准"
if now then
    text = string.format("%04d-%02d-%02d %02d:%02d",
        now.year, now.month, now.day, now.hour, now.minute)
end
ui.text(16, 16, text, 28, 0)
```

`clock.now` 只读时间，不联网校时，也不会创建定时器。JSON 的 interval_ms 决定多久检查一次；时间表提供真实当前时间。不要把 `on_tick` 的 now_ms 当作年月日，它是运行计时值。

## config.get：系统提供的固定名称数据

```lua
local words = tonumber(config.get("today_words")) or 0
local current_time = config.get("current_time") or "--:--"
```

`config.get` 返回**字符串或 nil**。上例里今日字数需要 `tonumber` 转成数字，时间字符串则直接使用。

当前两个名称由系统专门提供：`today_words` 为今日阅读字数；`current_time` 为本地 `HH:MM`，未校时为 `--:--`。其他 key 从固件管理的 SPIFFS 固定变量文件读取，不是任意 JSON/SD 文件查询。成功值最多 511 字节，未知 key 得到 nil。

例如固件已配置 `lock_label` 时，可读 `config.get("lock_label")`；模板作者仅在自己的包里加一个同名 JSON 字段，并不能创建这个系统变量。没有变量时必须有默认文案。

## poetry：读取设备已有的每周诗库

```lua
local count = poetry.count("zh-Hans")
local line = count > 0 and poetry.get("zh-Hans", 1) or nil
```

语言必须显式选 `zh-Hans`（简体）或 `zh-Hant`（繁体）。索引从 **1** 开始；0 不是第一条。成功的 line 是 `{text, title, author, dynasty}`，分别为诗句、作品名、作者、朝代。

诗库由系统下载并保存在卡内；调用接口不会替模板发起联网。可用数量为 0–350，无诗库、语言错误或内容不可用时，count 可能为 0、get 可能为 nil。

```lua
-- 放在锁屏初始化阶段，确保没有诗库也有内容。
local poem_text = "读书不觉已春深，一寸光阴一寸金。"
local count = poetry.count("zh-Hans")
if count > 0 then
    local item = poetry.get("zh-Hans", math.random(1, count))
    if item then poem_text = item.text end
end
```

这会在每次新建 Lua 实例时选一条诗，而不是每次刷新都更换。如果想周期轮换，应把索引更新放在 on_tick，并处理索引超出当次可用数量的情况。长诗句需要自行分行/截短；`ui.text` 不负责自动换行。

## ancs：读取 iPhone 通知快照

ANCS 是 iPhone 向已配对设备提供通知信息的一项蓝牙服务。JustRead 的系统 BLE 服务负责配对、连接、订阅和缓存，模板只读取已经收到的数据。

在 `lockscreen.json` 的 lua 对象中加 `"ancs": true`，固件才为这个锁屏提供 `ancs`。它的位置必须在 lua 内，不是配置顶层。手机侧还需要允许配对与通知共享。

```lua
local connected = ancs.connected()
local items = ancs.notifications()
```

connected 表示当前系统 ANCS 链路状态，不代表必定有通知。items 是最多 8 条、由新到旧的数组。Lua 中 `#items` 是数量，`items[1]` 是第一条；空数组不能直接取第一条的 title。

| 每条通知字段 | 含义 |
| --- | --- |
| `id` | 系统通知标识 |
| `app` | 应用标识字符串，例如某个应用的 bundle 标识；不是图标 |
| `title` | 通知标题，可能为空或被截断 |
| `message` | 正文，可能为空或被截断 |

```lua
-- 片段：先区分接口未启用、未连接、没有通知三种状态。
local label = "本模板未启用通知接口"
if ancs then
    if not ancs.connected() then
        label = "手机未连接"
    else
        local items = ancs.notifications()
        label = #items > 0 and (items[1].title or "新通知") or "暂无通知"
    end
end
```

修改这份 Lua 数组不会删除手机通知；接口没有发送消息、清除通知或控制任意蓝牙设备的功能。app/title/message 的字节缓冲上限见[规范](/developer/lockscreen-development#ancs-与诗句)，显示时还应根据画布宽度截短。

## 把几种数据放进一个完整模板

下面是一个可独立制作的新模板，源目录内保存三份文件。它每约 5 秒检查一次，显示时间、字数、一条诗和最新通知状态。为了便于理解，每次更新整个动态区域；按内容变化分区局刷的优化留给后续版本。

`lockscreen.json`：

```json
{
  "version": 1,
  "模板名称": "阅读信息卡",
  "canvas": {"width": 684, "height": 1216, "background": 255},
  "font_file": "system",
  "texts": [
    {"text": "阅读信息", "x": 48, "y": 560, "width": 588, "height": 80,
     "font_size": 44, "gray": 0, "align": "center"}
  ],
  "lua": {
    "file": "lockscreen.lua",
    "when": "locked",
    "interval_ms": 5000,
    "area": {"x": 48, "y": 800, "width": 588, "height": 400},
    "refresh": "partial_gray",
    "ancs": true
  }
}
```

`images.json`：

```json
[]
```

`lockscreen.lua`：

```lua
local M = {}

local function first_chars(value, count)
    local text = tostring(value or "")
    local stop = utf8.offset(text, count + 1)
    return stop and string.sub(text, 1, stop - 1) or text
end

function M.on_draw()
    local w, h = ui.size()
    local now = clock.now()
    local time_text = "时间尚未校准"
    if now then
        time_text = string.format("%04d-%02d-%02d %02d:%02d",
            now.year, now.month, now.day, now.hour, now.minute)
    end

    local words = tonumber(config.get("today_words")) or 0
    local poem = "暂无诗库，先读几页书吧"
    if poetry.count("zh-Hans") > 0 then
        local item = poetry.get("zh-Hans", 1)
        if item then poem = item.text end
    end

    local notice = "通知接口未启用"
    if ancs then
        if ancs.connected() then
            local items = ancs.notifications()
            notice = #items > 0 and ("通知：" .. items[1].title) or "暂无通知"
        else
            notice = "手机未连接"
        end
    end

    ui.rect(0, 0, w, h, 255, true)
    ui.text(16, 32, time_text, 28, 0)
    ui.text(16, 104, "今日阅读：" .. tostring(words) .. " 字", 28, 0)
    ui.text(16, 176, first_chars("诗句：" .. poem, 18), 28, 0)
    ui.text(16, 248, first_chars(notice, 18), 28, 0)
    ui.refresh("partial_gray", 0, 0, w, h)
end

return M
```

按[独立打包步骤](/developer/extension-packaging#packer)生成 `.lspack`，无需固件源码。本例没有包内图片和字体，适合先验证数据路径。字符截短假设输入为有效 UTF-8；18 字符是在本例区域和字号下给中文留余量，不是通用像素测量方案。

默认可能出现“时间尚未校准”“暂无诗库”“手机未连接”，这些都是有效兜底画面。应先确认它们能显示，再逐项接通时间、诗库和手机；不要一开始同时排查三条数据链路。

## 图标与大字号怎样处理

`ui.image("icons/app.png", x, y, width, height)` 可在 on_draw 绘制当前锁屏包内的小 PNG。输出宽高各为 1–96 px；文件名用安全相对路径，后缀为小写 `.png`。资源需要真实打进包，但不需要为了动态绘图再列入静态 images.json。返回 false 时可不画图标，文字仍能显示。

手机通知不传图标，作者需要用 app 标识选择自己准备的 PNG，并给未知应用一个通用图标。用某个应用的通知标题去猜图标不可靠。

`ui.glyph("8", x, y)` 用于预先制作的大数字字形图集：JSON 的 glyphs 说明图集文件、字符顺序和每格尺寸，Lua 选择单个字符贴到画布。它不是任意中文字库；只支持声明过的唯一可打印 ASCII 字符。大时钟可以避免实时栅格化 TTF，但需要作者生成匹配的 PNG，并保留字体许可证。

初学阶段先用系统字体和文字。准备好再按[字体与图集规范](/developer/lockscreen-development#glyphs)制作自己的图集，将时钟和通知分别比较前后内容，只请求变化区域刷新。需要记住：锁屏每次 draw 前会先重绘静态场景到内存，只刷新某一面板区域并不意味着其他动态区域在内存中仍保留。
