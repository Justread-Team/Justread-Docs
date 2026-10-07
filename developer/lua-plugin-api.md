# Lua 插件 API

本文记录当前固件中的 Lua 插件宿主接口。对应实现说明位于固件仓库 `components/reader_plugins/API.md`；这里按文档站的开发导航提供可浏览、可搜索的说明。

## 插件入口

每个插件放在 SD 卡的 `/.justread/plugins/<插件目录>/` 下，由 `main.lua` 返回一个 Lua table。`on_draw` 是基本绘制入口，`title` 用作系统顶栏标题；未提供标题时使用插件目录名。

```text
/.justread/plugins/example/
├── main.lua
└── icons/
    └── home.rui48
```

```lua
local M = { title = "五子棋" }

function M.on_draw()
    local width, height = ui.size()
    -- 在应用画布内绘制内容。
end

return M
```

## 系统状态栏与顶栏

当前插件宿主使用系统状态栏和系统顶栏，插件无需自行绘制这两部分。状态栏显示设备状态；顶栏显示插件标题和系统返回入口，点击返回入口会关闭插件。长按中间硬件按键仍可作为退出方式。

`ui.size()` 返回顶栏以下应用画布的尺寸。绘制、输入和局部刷新坐标都相对该画布，宿主会把绘制和刷新裁剪在画布范围内，插件不能覆盖系统栏或系统热区。点击状态栏会刷新设备状态。

顶栏返回热区会向画布内延伸 16 px；启用底部导航时，底部热区也会向画布内延伸 16 px。应用内容应避开这些区域，避免与系统操作重叠。

## 可选底部导航

插件可以在返回的 table 中声明 1 至 5 个导航项。声明 2 至 5 项时显示系统底栏；声明 1 项时显示单独的底部操作；省略 `navigation` 则不显示底栏。`navigation_active` 是从 1 开始的当前项序号，省略时默认选中第一项。

```lua
local M = {
    title = "示例应用",
    navigation_active = 1,
    navigation = {
        { label = "首页", icon = "icons/home.rui48" },
        { label = "收藏" }, -- 不指定 icon 时使用系统的四圆格子图标
    },
}

function M.on_event(name, x, y, key)
    if name == "navigation" then
        local selected = x -- 从 1 开始的导航项序号
    end
end

return M
```

用户点击导航项时，宿主先更新选中指示，再向 `on_event` 发送 `("navigation", index, 0, 0)`。单个底部操作没有选中指示。启用导航时，`ui.size()` 不包含底部 80 px 系统区域。

### 自定义图标

图标文件放在插件目录内，可与 `main.lua` 同级，也可放在子目录中。当前格式为无文件头的 288 字节单色位图：48 × 48 像素，每行从上到下、每行像素从左到右打包，最高位优先；位值 1 表示黑色，0 表示白色。系统会将图标绘制在 48 × 48 px 图标槽中，并负责热区和刷新。

省略 `icon`，或图标文件缺失、格式无效时，系统回退到默认的四圆格子图标。
