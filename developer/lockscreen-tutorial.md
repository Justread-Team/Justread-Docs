# 从零制作第一个锁屏

本篇做两件事：先显示一句自己写的静态文字，再让同一个模板每分钟显示一次当前时间。前半篇只编辑 JSON，不需要会 Lua。适用默认小纸 Pico 684 × 1216 逻辑屏幕；完整字段限制见[锁屏编写规范](/developer/lockscreen-development)。

## 先认清四类文件

| 文件 | 作用 | 这一课是否需要 |
| --- | --- | --- |
| `lockscreen.json` | 告诉系统画布大小、静态文字、字体、脚本时机 | 必须 |
| `images.json` | 告诉系统有哪些静态图片、放在哪里 | 必须；没有图片就写 `[]` |
| `lockscreen.lua` | 每次运行时读取时间等数据，再画动态内容 | 时钟步骤才需要 |
| `.lspack` | 把上述文件按规定装在一起，供设备安装 | 交给设备时需要 |

JSON 是一种文字配置格式：`{}` 表示按名称存放字段的对象，`[]` 表示列表。字段名和字符串用英文双引号；相邻字段用逗号分隔，最后一项后面不加逗号。JSON 不能写 `--` 或 `//` 注释。

在电脑任意合适位置建一个工作文件夹，把源目录命名为 `my-lock`。不需要下载固件仓库。源目录是你编辑的材料，`.lspack` 是做好的安装包，两者不要混淆。

## 第一步：写一个纯文字锁屏

建立 `my-lock` 目录，内含以下两个文件。

`lockscreen.json` 完整内容：

```json
{
  "version": 1,
  "模板名称": "我的阅读暂停页",
  "canvas": {
    "width": 684,
    "height": 1216,
    "background": 255
  },
  "font_file": "system",
  "texts": [
    {
      "text": "阅读暂停",
      "x": 48,
      "y": 560,
      "width": 588,
      "height": 80,
      "font_size": 44,
      "gray": 0,
      "align": "center"
    }
  ]
}
```

`images.json` 完整内容：

```json
[]
```

现在目录应为：

```text
my-lock/
├── lockscreen.json
└── images.json
```

### 这些数字会变成什么画面

整个设计画布是宽 684、高 1216，背景 255 为白色。文字所在框左上角是 `(48, 560)`，宽 588、高 80，距离左右边缘都是 48 像素。`align: "center"` 让文字在这个框内水平居中，不是把文字在整屏垂直居中。

`font_size: 44` 是设计字号，`gray: 0` 是黑色。`font_file: "system"` 让固件使用设备当前选择的字体；不需要随模板另外放字体文件。

`模板名称` 是菜单里的名字，`version: 1` 是配置格式版本。修改模板内容后发布 1.1.0，并不意味着要把这里的 version 改成 1.1 或 2。

## 第二步：打包、导入和观察

下载<a href="/tools/justread_pack.py" download>独立打包脚本</a>，按[工具准备说明](/developer/extension-packaging#packer)将它放在 my-lock 文件夹旁边。准备 UV 和可用 Python 后，在能同时看到工具与源目录的位置运行：

```sh
uv run --no-project --python 3.12 python justread_pack.py lockscreen my-lock dist/my-lock.lspack
```

成功后会生成 dist/my-lock.lspack 并打印大小和摘要。这里的 Python 只负责制作包，阅读器上运行的是 Lua；不需要 ESP-IDF 或 C 编译器。工具无需第三方 Python 依赖。

把 `my-lock.lspack` 传到卡内，再在阅读设置的锁屏模板页导入。导入后列表应显示“我的阅读暂停页”；实际锁定时应显示白底黑字“阅读暂停”。短按电源键解锁，确认返回原界面。

至此已经做出一个完整可用的静态模板。没有时钟、没有自动动画，是因为还没有添加动态脚本。

## 第三步：给模板加一个时钟

将 `lockscreen.json` **整体替换**为以下内容；原来的 `images.json` 保持 `[]`。不是把这段 JSON 粘在旧文件后面。

```json
{
  "version": 1,
  "模板名称": "我的每分钟时钟",
  "canvas": {"width": 684, "height": 1216, "background": 255},
  "font_file": "system",
  "texts": [
    {"text": "阅读暂停", "x": 48, "y": 560, "width": 588, "height": 80,
     "font_size": 44, "gray": 0, "align": "center"}
  ],
  "lua": {
    "file": "lockscreen.lua",
    "when": "locked",
    "interval_ms": 60000,
    "area": {"x": 48, "y": 800, "width": 588, "height": 160},
    "refresh": "partial_gray"
  }
}
```

在同一个目录新增 `lockscreen.lua`，完整内容：

```lua
local M = {}

function M.on_draw()
    local w, h = ui.size()
    local now = clock.now()
    local value = "--:--"
    if now then
        value = string.format("%02d:%02d", now.hour, now.minute)
    end

    ui.rect(0, 0, w, h, 255, true)
    ui.text(24, 32, value, 64, 0)
    ui.refresh("partial_gray", 0, 0, w, h)
end

return M
```

最终源目录为：

```text
my-lock/
├── lockscreen.json
├── images.json
└── lockscreen.lua
```

重新打包时显式允许覆盖输出：

```sh
uv run --no-project --python 3.12 python justread_pack.py lockscreen my-lock dist/my-lock.lspack --force
```

导入新包，并确认选中的是“我的每分钟时钟”。已经加载的旧锁屏不会自动变为新脚本；先解锁，再重新锁定观察。

### 新字段各管什么

| 字段 | 本例意思 | 修改时注意 |
| --- | --- | --- |
| `file` | 到包根部找 lockscreen.lua | 要与真实文件名一致，当前脚本路径不使用子目录 |
| `when` | 已锁定期间周期运行 | 不写成 before_open，否则是解锁前才显示 |
| `interval_ms` | 每次刷新完成后等待 60000 毫秒再检查 | 60000 毫秒 = 60 秒；不是每秒更新 |
| `area` | 把屏幕 `(48, 800)` 起的 588 × 160 区域交给脚本 | 必须完整在 canvas 内，不能覆盖整个静态布局后又误以为坐标从屏幕算 |
| `refresh` | 没有脚本显式请求时采用灰度局刷策略 | 本例 Lua 也显式请求相同区域，便于看清调用 |

### 代码怎样得到“09:05”

`clock.now()` 向系统取本地时间，成功时返回一个表，包含 `hour`、`minute` 等字段。没有有效时间时是 `nil`，于是保留 `--:--`；这不是脚本崩溃。

`string.format("%02d:%02d", 9, 5)` 把两个数字写成至少两位、前面补零的文字，结果是 `09:05`。它负责显示格式，不负责校时。

`ui.rect(0, 0, w, h, 255, true)` 先把整个动态区域填白，避免新时间与旧时间叠在一起。这里不用 `ui.clear`，因为后者还会隐含请求完整灰度刷新。

`ui.text(24, 32, ...)` 相对 **area 左上角**定位；本例设计尺寸与设备一致，所以文字实际约在屏幕 `(72, 832)`。脚本拿到的 w/h 为 588/160，不是 684/1216。

最后一行请求把动态区域送到面板。灰度局刷可以呈现文字边缘的灰阶；不需要让静态“阅读暂停”每分钟也重新刷新。

## 第四步：理解系统在什么时候执行它

进入锁屏 → 系统读 JSON 和资源 → 画静态标题 → 调用 Lua 的 `on_draw` 画时间 → 显示第一帧 → 等待周期 → 再次执行脚本并局部刷新 → 解锁时停止并释放实例。

本例没有 `on_tick`，因为每次 `on_draw` 直接读当前时间就够了。若以后要维护轮播索引，可在 `on_tick` 更新索引，在 `on_draw` 表现它。`locked` 模式中每次周期是先 tick、再 draw；不必也不应该自己写一个无限循环。

只要选择了 `locked` 和合法间隔，系统负责唤起脚本。`ui.refresh` 负责这一次显示哪些区域，不负责创建下一次定时任务。

## 第五步：如何加一张背景图

在源目录新增符合规范的 `images/art.png`，把 `images.json` 整体改为：

```json
[
  {
    "file": "images/art.png",
    "x": 48,
    "y": 96,
    "width": 588,
    "height": 360,
    "fit": "contain"
  }
]
```

重新打包。`file` 相对包根目录，所以不是电脑绝对路径，也不是 `/.justread/...`。`contain` 保持图片比例并居中，`stretch` 会拉伸铺满矩形。图片先画、静态文字后画、Lua 最后画。

本例矩形选在上半屏，不与标题和时钟重叠。PNG 要导出为 8-bit、非交错；单张最多 2 MiB、单边最多 4096、总像素最多 1048576。图像导出工具若提供“交错”选项，不勾选；黑白素材也不要误导出为 1-bit PNG。

## 三种运行时机该怎么选

| 你想做的事 | 选择 | 额外设置 |
| --- | --- | --- |
| 锁上时显示一次固定随机内容 | `before_lock` | 没有周期更新 |
| 锁住后仍需检查时间、通知或轮播 | `locked` | `interval_ms` |
| 用户准备解锁时先显示一句提示，再回原界面 | `before_open` | `hold_ms`，单位毫秒 |

`hold_ms: 2000` 表示解锁前内容展示约 2 秒，不是锁屏后 2 秒自动解锁。一个模板只有一个 lua 配置，三种模式不能同时声明。

## 遇到问题先查这里

| 现象 | 先检查 |
| --- | --- |
| 打包时 JSON 解析失败 | 是否用了中文引号、漏逗号、多尾逗号或在 JSON 写注释 |
| 提示缺少资源 | 包根部是否有两份 JSON；file 是否拼写一致 |
| 锁屏显示标题但没有时间 | when 是否正确；area 是否够大；Lua 是否返回 M 并实现 on_draw |
| 时间为 --:-- | 系统尚未校时，先确认设备时间，而非不断缩短刷新间隔 |
| 字或线没画出来 | 局部坐标、字号和整行文字是否超出 area；绘图返回值可能为 false |
| 局刷变成全刷 | 是否调用 ui.clear/ui.invalidate，或系统合并/升级了刷新请求 |
| 仍是旧模板 | 是否重新打包、导入、选中并重新进入锁屏 |
| 提示模板无效/回退默认页 | 先恢复本篇无图片静态版本，再逐项加回图片和 Lua |

需要显示今日阅读字数、诗句或手机通知时，继续看[锁屏数据接口](/developer/lockscreen-data)。发布前按[打包与验证](/developer/extension-packaging)检查目标设备，不能把“制作出 ZIP”当成全部验收完成。
