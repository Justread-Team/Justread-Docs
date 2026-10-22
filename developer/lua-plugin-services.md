# 设备、阅读状态和存档 API 详解

这篇面向已经完成[计数器教程](/developer/plugin-tutorial)的作者。以下除 `print` 外的接口用于**普通插件**；锁屏使用[另一组只读接口](/developer/lockscreen-data)。短代码块注明了放置位置，不能把每个片段都独立当成完整入口。

## device.status：向系统取一份设备状态

```lua
local status = device.status()
```

成功得到一个 Lua 表，概念上类似下面这份数据；数值只是解释格式的例子：

```lua
{
    battery = 78,
    temperature_centi_c = 2534,
    temperature_valid = true,
    sd_ready = true,
}
```

| 字段 | 单位/类型 | 正确使用方式 |
| --- | --- | --- |
| `battery` | 电量百分比，未知可为 -1 | 先判断是否 >= 0，再附加百分号 |
| `temperature_centi_c` | 0.01°C | 除以 100 才得到摄氏度，例如 2534 表示 25.34°C |
| `temperature_valid` | boolean | true 才展示温度；否则不能把 0 当作真实 0°C |
| `sd_ready` | boolean | SD 是否已挂载；不代表下一次写文件必定成功 |

这份状态来自系统缓存；调用不会要求设备立刻重新测量电量/温度。整体无法获取时返回 `nil`，所以不要直接写 `device.status().battery` 而不处理缺失情况。

下面的初始化和绘图片段可放入已有插件；变量定义放在回调外：

```lua
local battery_text = "电量未知"
local temperature_text = "温度未知"

function M.on_open()
    local status = device.status()
    if not status then return end
    if status.battery >= 0 then
        battery_text = tostring(status.battery) .. "%"
    end
    if status.temperature_valid then
        temperature_text = string.format("%.2f C", status.temperature_centi_c / 100)
    end
end

function M.on_draw()
    ui.clear(255)
    ui.text(24, 32, battery_text, 32, 0)
    ui.text(24, 88, temperature_text, 28, 0)
end
```

要定期读取，参考[电量观察完整示例](/developer/lua-plugin-ui#invalidate)，不要在每次画一个字时都读取状态。

## device.buzzer：短促声音反馈

```text
 device.buzzer(frequency_hz, duration_ms) → boolean
```

频率 200–5000 Hz，时长 5–250 ms，成功调用间隔至少 150 ms。`Hz` 决定音高，毫秒决定持续时间，例如：

```lua
-- 放在已有的点击事件分支里。
local played = device.buzzer(1200, 40)
if not played then print("buzzer unavailable or rate limited") end
```

太频繁时可返回 false；超出允许参数范围会报 Lua 错误。声音只是操作反馈，不能用它循环播放长音乐或假定蜂鸣器一定可用。正常功能不应依赖“必须成功响一声”。

## reader.status：读取当前书籍的状态

```lua
local book = reader.status()
```

| 字段 | 含义 |
| --- | --- |
| `reading` | 系统当前是否持有打开的书籍 |
| `title` | 书名字符串 |
| `page`、`page_count` | 系统当前排版上下文的页位置与页数 |
| `chapter`、`chapter_count` | 当前章节位置与章节总数 |

有书时位置从 1 开始；没有书时 page/chapter 等为 0。API 不承诺插件打开时一定保留一本书，也不承诺 page_count 是整个 EPUB 的总页数；排版可能按章节进行。不要据此未经核对就显示“整书已经读了 80%”。

```lua
-- 在已有插件的 on_open 或受控 tick 中读取，再在 on_draw 显示。
local book = reader.status()
local label = "没有打开的书籍"
if book and book.reading then
    label = "当前页 " .. tostring(book.page) .. "/" .. tostring(book.page_count)
end
```

这只是只读状态，不能用它翻页、打开任意路径或替用户改变阅读设置。普通插件也没有统一“今日字数”接口；锁屏可通过其专用 config 接口获取系统提供的值。

## storage：保存自己的一小份数据

接口只允许访问当前插件的私有 data 目录。目录名为 counter 时：

```lua
storage.write("count.txt", "12")
```

实际对应 SD 卡 `/.justread/plugins/counter/data/count.txt`。**参数中不用再写 data/，也不能写整条 SD 绝对路径。** `"data/count.txt"` 会变成 data 下再套一层 data，而不是指回标准目录。

### 写入

```text
storage.write(path, data) → boolean
```

path 为安全相对路径，最多 96 字节；data 是最多 4096 字节的字符串。允许安全子目录，如 `"scores/best.txt"`。只能使用支持的名称字符，不能有空段、`.`、`..`、反斜杠或绝对路径。

宿主创建父目录，先写临时文件，成功后替换目标文件。你仍须检查返回值：卡被移除、不可写、空间不足或安装方式不匹配都可能失败。

```lua
local ok = storage.write("best.txt", tostring(best_score))
if not ok then
    -- best_score 和 message 是你自己定义的状态变量。
    message = "本次记录未保存"
end
```

应在事件处理等受控时机保存重要变化。不要在 `on_draw` 里每次重画都写卡，也不要每 100 ms 的 tick 都保存同一份内容。

### 读取

```text
storage.read(path) → string 或 nil
```

文件不存在、读取失败或超过单值上限时可能为 nil。读取成功也只得到字节字符串，系统不会自动帮你转换为数字、JSON 或 Lua 表。

```lua
local raw = storage.read("best.txt")
local best_score = tonumber(raw) or 0
```

Lua 的 `or` 会在左侧是 nil 或 false 时选择右侧，所以没有有效数字时使用 0。数字 0 和空字符串在 Lua 中都是真值，这一点与部分语言不同。

如果写入 `"0"`，读取后 `tonumber` 得到 0，并不会走默认值之外的特殊失败分支。

### 多个字段怎样保存

固件没有提供 JSON 编解码 API，也没有打开 require。只有几个数字时可以用约定的简单文本，读取后验证：

```lua
-- 片段：保存两个由你定义的整数 wins、losses。
storage.write("stats.txt", tostring(wins) .. "," .. tostring(losses))

-- 片段：读回后校验，格式错误就使用默认值。
local raw = storage.read("stats.txt") or ""
local a, b = raw:match("^(%d+),(%d+)$")
local restored_wins = tonumber(a) or 0
local restored_losses = tonumber(b) or 0
```

格式升级时应增加你自己的数据版本并写兼容读取逻辑。单值 4096 字节不是自动管理的整个插件配额；避免无界创建存档，也不要把大图、书籍内容当作小存档存入。

### 哪种安装方式能保存

目录模式和云市场部署到目录的入口，可以按标准私有路径写入。本地直接运行 `.jrpack` 时，宿主仍按包含 `.jrpack` 后缀的名称构造 data 路径，与包文件本身冲突，通常无法保存。见[安装对照](/developer/extension-packaging#installation)。因此返回 false 应当是可处理的正常失败路径。

## plugin_exit：请求结束当前插件

```lua
-- 放在退出按钮的事件分支里。
plugin_exit()
return
```

它返回 true 并登记退出请求，宿主稍后处理。函数本身不会像语言的 return 那样停止你正在执行的回调，所以通常紧跟 `return`，避免还做额外工作。保存应放在请求退出之前，并妥善处理失败。

系统顶栏返回和实体键退出由固件控制，无需额外监听。不要尝试在 Lua 中阻止用户使用系统返回。

## print：记录给开发者看的信息

```lua
print("save result", true)
```

消息进入固件日志，普通插件 tag 为 `lua_plugin`，单条有界为最多 255 字节；它不会画到屏幕上。需要给用户看的提示，要把文本放进自己的状态变量，再在 `on_draw` 调用 `ui.text`。

调试日志只记录必要的阶段和结果，不输出通知正文或用户存档内容。运行失败时，可把错误提示、插件/固件版本和触发步骤提供给维护者。

下一步可回到[API 总览](/developer/lua-plugin-api)查询全部签名与预算，或按[发布文档模板](/developer/extension-release-template)写清自己的数据格式和安装要求。
