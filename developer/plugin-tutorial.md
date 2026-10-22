# 从零制作第一个插件

目标是做一个“点击加一”的计数器，支持重置、退出和目录模式下的保存。先让最小代码运行，再逐步理解交互。本文适用默认小纸 Pico 684 × 1216 逻辑屏幕，接口依据见[开发总览](/developer/extensions)。

## 需要准备什么

你需要一台已能正常使用的 JustRead 设备、可写入的 SD 卡，以及能保存 UTF-8 纯文本的编辑器。使用 VS Code 等代码编辑器可以避免把 `main.lua` 存成富文本或 `main.lua.txt`。

**目录安装这一步不需要 Python、ESP-IDF、C 编译器或刷机。** 只有最后要制作分发包时才需要打包工具。如果还不知道插件为什么能工作，可先读[运行原理](/developer/extensions-runtime)。

## 第一步：让设备显示一句话

在电脑上新建 `hello` 文件夹，里面只放一个 `main.lua`，内容完整复制如下：

```lua
local M = { title = "我的第一个插件" }

function M.on_draw()
    ui.clear(255)
    ui.text(24, 32, "你好，JustRead", 32, 0)
end

return M
```

把文件夹放到 SD 卡：

```text
/.justread/plugins/hello/main.lua
```

退出文件传输，重新进入插件列表并打开 `hello`。预期是：系统顶栏显示“我的第一个插件”，下面白色画布中有“你好，JustRead”。系统状态栏和返回入口由固件提供。

### 这几行分别是什么意思

| 代码 | 用普通话解释 |
| --- | --- |
| `local M = { title = "..." }` | 建一个名叫 M 的表，里面记录插件标题；表可以理解为按名称存放资料的容器 |
| `function M.on_draw()` | 给 M 登记一个画图函数，系统需要绘图时会调用它 |
| `ui.clear(255)` | 把插件画布填成白色，并请求全灰刷新 |
| `ui.text(24, 32, "...", 32, 0)` | 在画布左上角向右 24、向下 32 的位置画字，字号 32、黑色 |
| `end` | 结束刚才定义的函数 |
| `return M` | 把插件资料和函数交给固件；漏掉它，固件就拿不到插件入口表 |

这里的 `M` 只是作者取的变量名，也可以换别的名字，但要前后一致。`title`、`on_draw` 是接口约定的字段名，不能随意改。

`--` 开头的是 Lua 注释，用于解释代码，不会执行；字符串用英文引号包围。全角中文引号 `“ ”` 不能替代 Lua 的 `"`。

## 第二步：做一个能保存的计数器

新建另一个目录 `counter`，把下面**整份代码**保存为它的 `main.lua`。这份代码不依赖图标、图片或其他 Lua 文件。目录安装后会在自己的 `data/count.txt` 保存计数。

```lua
local M = { title = "点击计数" }
local count = 0
local message = ""

-- 三个按钮使用同一种矩形布局。
local function buttons()
    local w, h = ui.size()
    return {
        { x = 24, y = 160, w = w - 48, h = 88, label = "加一" },
        { x = 24, y = 272, w = w - 48, h = 88, label = "重置" },
        { x = 24, y = 384, w = w - 48, h = 88, label = "退出" },
    }
end

local function contains(box, x, y)
    return x >= box.x and x < box.x + box.w
       and y >= box.y and y < box.y + box.h
end

local function save_count()
    if storage.write("count.txt", tostring(count)) then
        message = "已保存"
    else
        message = "保存失败，本次仍可使用"
    end
end

function M.on_open()
    local saved = tonumber(storage.read("count.txt"))
    if saved then
        count = math.floor(math.max(0, math.min(999999, saved)))
        message = "已读取存档"
    else
        count = 0
        message = "从零开始"
    end
end

function M.on_draw()
    ui.clear(255)
    ui.text(24, 32, "当前计数：" .. tostring(count), 36, 0)
    ui.text(24, 96, message, 24, 80)
    for _, box in ipairs(buttons()) do
        ui.rect(box.x, box.y, box.w, box.h, 0, false, 2)
        ui.text(box.x + 24, box.y + 24, box.label, 28, 0)
    end
end

function M.on_event(name, x, y, key)
    if name ~= "tap" then return end
    local items = buttons()
    if contains(items[1], x, y) then
        count = (count + 1) % 1000000
        save_count()
    elseif contains(items[2], x, y) then
        count = 0
        save_count()
    elseif contains(items[3], x, y) then
        plugin_exit()
        return
    end
end

return M
```

正确卡内布局是：

```text
/.justread/plugins/counter/
└── main.lua
```

设备成功写入一次后，还会出现：

```text
/.justread/plugins/counter/data/count.txt
```

作者不用提前创建 `data`，也不用把这个用户存档打进发布包。为了让新手看清按钮，本例只针对默认尺寸安排固定的三行；移植到更小画布时，应调整位置并检查每个按钮是否完整可见。

### 点击按钮时，哪几段代码依次执行

用户点击“加一” → 系统调用 `M.on_event("tap", x, y, 0)` → `contains` 判断点是否位于第一个按钮 → `count` 加一 → `save_count()` 保存 → 事件结束后系统调用 `M.on_draw()` → 显示新数字。

**按钮不会因为画了一个矩形就自动能点击。** `ui.rect` 只画外观，`contains` 和 `on_event` 才决定点到这里发生什么。画图和命中判断使用同一份 `buttons()` 数据，可以避免改了按钮位置却忘记改点击范围。

矩形的宽高不是右下角坐标。例如第一个按钮的 y = 160、高 = 88，它覆盖 `160 <= y < 248`。x 同样使用左闭右开范围。

### 为什么数据要转来转去

`count` 是数字，`storage.write` 保存字符串，所以先用 `tostring(count)`。读取返回的也是字符串，例如 `"12"`，用 `tonumber` 才还原为数字。存档不存在、不能读取或内容不是数字时，结果可能为 `nil`，于是从 0 开始。

代码把读取的值限制为 0–999999，防止坏存档让界面显示异常大的数字。`..` 表示拼接字符串，例如 `"当前计数：" .. tostring(count)` 会得到 `"当前计数：12"`。

### 为什么画图函数不负责加一

系统可能因为状态栏、恢复显示或其他原因再次调用 `on_draw`。如果把 `count = count + 1` 放进去，计数会随绘图次数变化。绘图应只把当前状态表现出来；用户行为放在事件回调，初始化放在 `on_open`。

本例每次都清空画布，容易理解，也能避免旧数字留在背景中；代价是会请求完整灰度刷新。需要优化时，再看[绘图与局刷详解](/developer/lua-plugin-ui)。

## 第三步：自己验证行为

| 操作 | 预期结果 |
| --- | --- |
| 第一次打开 | 显示 0 和“从零开始” |
| 点“加一” | 数字增加，通常显示“已保存” |
| 点两个按钮之间的空白 | 数字不变 |
| 点“重置” | 回到 0，并保存 |
| 点“退出”后重新打开 | 恢复最后成功保存的数字 |
| 系统顶栏返回 | 退出插件；没有拦截系统操作 |

出现“保存失败”时，先确认是**目录安装**，不是直接运行 `counter.jrpack`，再检查卡是否可写。这个提示不阻止当前会话继续计数；它只说明下次启动可能无法恢复。

替换源码后，要退出插件再重新打开。当前运行实例不会因为电脑上的文件修改而自动重新加载。

## 第四步：怎样改成自己的插件

先做这些小修改，每次修改后重新打开确认：

1. 改 `title` 和屏幕上的文字，观察列表名与顶栏标题的区别。
2. 把“加一”改成加二，只改事件中更新 `count` 的语句。
3. 调整 `buttons()` 的 y 值，验证画面与可点击区域一起移动。
4. 修改 `message` 颜色，理解灰度 0 为黑、255 为白。

有了这个基础，再看[设备、阅读和存档 API](/developer/lua-plugin-services)读取电量或阅读状态；需要底部导航和定时逻辑时，看 API 总览中的[生命周期与事件](/developer/lua-plugin-api#lifecycle)及[系统栏、坐标与导航](/developer/lua-plugin-api#canvas)。不要用 `while true do` 自己接管主循环。

## 第五步：制作交给别人的包

目录中只保留源码和需要发布的资源，排除 `data` 用户存档。下载<a href="/tools/justread_pack.py" download>独立工具</a>，与 counter 源目录放在同一工作文件夹，按[准备说明](/developer/extension-packaging#packer)运行：

```sh
uv run --no-project --python 3.12 python justread_pack.py plugin counter dist/counter.jrpack
```

无需固件源码。普通用户收到目录版时可以直接复制；收到包版时走导入入口。修改后重新打包要加 --force 或换输出名。

本计数器依赖存档。当前本地直接运行 `.jrpack` 的存档路径有限制，分发时应推荐目录模式，或明确说明包模式的存档能力；云市场安装入口到目录后可使用私有存储。不能因为打包成功就宣称各安装方式行为完全相同。

## 遇到问题先查这里

| 现象 | 常见原因 |
| --- | --- |
| 列表没有 hello/counter | 多了一层目录、文件实际为 `main.lua.txt`、名字不合规则、扫描上限 |
| 提示必须返回 table | 缺少 `return M`，或错误地返回了字符串/数字 |
| 提示缺少 on_draw | 名字拼错，或函数没有挂在返回的 M 上 |
| drawing is only available in on_draw | 在 `on_open/on_event/on_tick` 里直接调用了画图函数 |
| 点按钮没变化 | 先确认事件名为 tap，再检查按钮坐标与画布是否一致 |
| 新数字叠在旧数字上 | 绘图前没有擦除旧区域；先用本例的 `ui.clear` 验证 |

这篇是完整程序教程；[API 总览](/developer/lua-plugin-api)负责精确签名和限制，[运行原理](/developer/extensions-runtime)负责解释宿主为什么这样调用。
