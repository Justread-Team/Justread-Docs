# 扩展打包、安装与验证

本文按**读者无法访问 JustRead 固件仓库**编写。你只需要自己的源文件和本页可下载的独立打包脚本。脚本只用 Python 标准库，无需安装 ESP-IDF、编译器、Pillow 或固件源码。

只安装现成包时，直接看[用户安装说明](/user/extensions)。第一次编写扩展，先完成[插件教程](/developer/plugin-tutorial)或[锁屏教程](/developer/lockscreen-tutorial)，再回这里打包。

## 下载工具并准备工作目录 {#packer}

下载 <a href="/tools/justread_pack.py" download>justread_pack.py 独立打包脚本</a>，另存为同名文件；若浏览器直接显示源码，用“另存为”保存，确认不是 `.py.txt`。本工具随文档站提供，不需要从私有仓库获取任何文件。

准备一个普通工作文件夹，例如 `my-extensions`，将工具和自己的源目录并排放置：

```text
my-extensions/
├── justread_pack.py
├── counter/                 # 你的插件源目录
│   └── main.lua
└── my-lock/                 # 你的锁屏源目录
    ├── lockscreen.json
    ├── images.json
    └── lockscreen.lua        # 静态锁屏不需要
```

只制作一种扩展时，只保留对应源目录即可。终端的“当前目录”应是 `my-extensions`，也就是能同时看见工具和 counter/my-lock 的位置。命令中的 `counter`、`my-lock` 就相对这个位置查找。

工具需要 Python 3.10 或以上；以下统一用 UV 选择 Python 3.12。已有 UV 与可用 Python 时可以直接运行，不用创建项目或虚拟环境，也没有第三方 Python 包要安装。`--no-project` 表示不按 Python 项目创建依赖环境；`--python 3.12` 选择解释器。

```sh
uv run --no-project --python 3.12 python justread_pack.py --help
```

如果你由管理员提供了现有 Python 环境，可将 `3.12` 替换为该环境 Python 的路径。这里不要求 ESP-IDF 环境。UV 找不到 Python 时，按本机软件管理方式准备解释器；不要通过不断另建虚拟环境来解决权限问题。

## 制作插件包

确保 `counter/main.lua` 是你自己的完整插件入口，然后在工作目录运行：

```sh
uv run --no-project --python 3.12 python justread_pack.py plugin counter dist/counter.jrpack
```

参数依次是：制作普通插件、读取 counter 目录、把安装包写成 `dist/counter.jrpack`。工具会自动建立输出目录 dist。成功后打印文件字节数和 SHA-256，并提示哪些验证尚未执行。

想按当前市场的包体上限检查，可以加 `--market`：

```sh
uv run --no-project --python 3.12 python justread_pack.py plugin counter dist/counter.jrpack --market
```

当前市场仅安装入口，包内附属文件不自动部署。需要导航图标的插件仍应提供目录安装说明；使用存档的本地包也有以下安装限制。

## 制作锁屏包

静态模板至少有两份 JSON，动态模板另外有配置指向的 Lua。运行：

```sh
uv run --no-project --python 3.12 python justread_pack.py lockscreen my-lock dist/my-lock.lspack
```

准备投稿云市场时加 `--market`：

```sh
uv run --no-project --python 3.12 python justread_pack.py lockscreen my-lock dist/my-lock.lspack --market
```

这会额外检查当前市场的资源允许列表和 8 MiB 包体硬上限。实际账户/分类限制可能更小，服务端扫描、审核仍需另行完成。

## 修改后重新打包

默认不覆盖现有产物，避免误覆盖。确认要替换时加 `--force`：

```sh
uv run --no-project --python 3.12 python justread_pack.py lockscreen my-lock dist/my-lock.lspack --force
```

产物必须放在源目录之外。正确是 `dist/my-lock.lspack`，不要放成 `my-lock/my-lock.lspack`，否则下次递归打包会把旧包也收进去。测试成功后重新导入/选择新包，并退出旧运行实例后再打开。

## 工具检查什么，不能证明什么

| 检查内容 | 工具行为 |
| --- | --- |
| 包根部、路径、重复成员与链接 | 从安全相对路径生成成员，拒绝符号链接和嵌套包；最多 128 文件 |
| 入口编码和体积 | 检查非空 UTF-8 Lua、无 NUL/bytecode、最多 64 KiB |
| 锁屏 JSON | 检查重复键、已公开字段/类型/范围、引用、canvas/area、运行时机和间隔 |
| PNG | 检查 IHDR、位深、非交错、尺寸/像素上限和头部 CRC；不执行完整像素解码 |
| 图集和字体 | 检查引用、体积、图集字符/格子与图像尺寸；不解析完整 TTF 字形 |
| 市场附加条件 | `--market` 检查当前文件类型允许列表和包体硬上限，不连接市场服务器 |
| 输出 | 标准 ZIP_STORED，不写目录条目；打印最终字节数和 SHA-256 |

**工具不运行 Lua，也不模拟设备。** 它不能证明 on_draw 一定存在、API 调用一定正确、所有 PNG 数据都能解码、字体覆盖中文、脚本不超预算或实际屏幕没有残影。固件 JSON 还有内部 token 上限，复杂配置可能通过工具却被设备拒绝。

工具采用便于分发的 ASCII 资源路径（字母、数字、`_`、`-`、`.`、`/`），比部分静态资源解析条件更严格。模板显示名称和文字内容仍可用中文。插件目录/包名称还受设备扫描的 31 字节上限约束，文件名要简短。

发布资料、README、截图和用户 data 存档不要放进源目录。工具不会按 `.gitignore` 自动排除文件；它收集目录内所有普通文件。锁屏市场尤其不接受任意 Markdown、JPG、额外 JSON 或 `.ttf`。

## 包格式公开约定

| 项目 | `.jrpack` 普通插件 | `.lspack` 锁屏 |
| --- | --- | --- |
| 容器 | 标准 ZIP，所有成员 ZIP_STORED | 同左 |
| 根部必需文件 | `main.lua` | `lockscreen.json`、`images.json` |
| 根部可选文件 | 附属资源，但运行时不保证读包内资源 | 根部 Lua、PNG、图集；本地可用 TTF |
| 成员数 | 最多 128 | 最多 128 |
| 体积 | 本地包文件最多 8 MiB，云扫描成员体积和最多 8 MiB | 锁屏云扫描成员体积和最多 16 MiB；上传另受较小限制 |

根部直接放入口，不加一层 `counter/main.lua`。不允许目录条目、重复路径、符号链接、绝对路径、空段、`.`/`..`、反斜杠、冒号、控制字符或嵌套包。PNG 本身内部的 zlib 数据正常保留，“不压缩”只指 ZIP 成员方法。

不使用本工具时，也须满足这些公开约定。普通压缩软件常默认采用 DEFLATE，因此“生成一个 zip 再改后缀”不能保证正确。

## 安装方式与资源可用性 {#installation}

| 安装方式 | 设备怎么运行 | 资源和存档限制 |
| --- | --- | --- |
| 插件目录复制 | 读 `/.justread/plugins/<name>/main.lua` | 图标从该目录读，存档在其 data 下；适合有资源/存档的插件 |
| 本地 .jrpack 复制/导入 | 包放进插件目录，直接读 ZIP 根 main.lua；导入可能生成 import 名称 | 图标与存档仍按同名目录拼路径，包文件与目录冲突，通常图标回退、存档失败；不能依赖包内附属资源 |
| 插件云市场 | 下载校验后把 main.lua 部署到 slug 目录 | 当前只安装入口，附属资源不落地；私有 data 可写 |
| 锁屏复制/导入/市场 | 原样保存 .lspack，到包内找配置与资源 | 静态资源、Lua、PNG、图集按包内相对路径读取 |

跨渠道普通插件要能够在没有图标和无法存档时运行。需要目录模式就明确要求目录安装。操作入口和 SD 路径详见[普通用户安装说明](/user/extensions)。

## 市场投稿与字体许可

投稿需要名称、唯一 slug、发布版本、描述、分类和包文件。发布版本放在投稿资料中；锁屏 JSON 的 `version: 1` 是配置格式，不跟着发布版本变化，普通插件也不强制 manifest.json。

实际上传限制取服务配置、账户权益、分类限制与当前 **8 MiB 服务硬上限**中的较小值，两类市场都如此。锁屏扫描层“16 MiB 成员体积和”不表示允许上传 16 MiB。

锁屏当前市场资源允许两份配置、`.png`、`.lua`，以及根部 `OFL.txt`、`LICENSE.txt`、`font-license.rtf`（文件名比较不区分大小写）。许可证须为非空 UTF-8，最多 128 KiB，RTF 有相应文件头。固件本地支持的随包 `.ttf` 当前市场不接受；投稿用系统字体或 PNG 字形图集，并保留必要授权文件。

服务端核验大小、摘要、结构和安全扫描后进入审核，审核通过才公开。插件还记录入口摘要。工具检查成功不表示已通过安全扫描、审核或设备验收。

## 不读固件源码，也能做的验证

先检查自己的最终包是否可读；在工作目录运行：

```sh
uv run --no-project --python 3.12 python -m zipfile -l dist/my-lock.lspack
uv run --no-project --python 3.12 python -m zipfile -t dist/my-lock.lspack
```

第一条列出成员，核对根部和资源名；第二条检查 ZIP 可读性与 CRC。Lua 仍需实际导入设备启动。

| 你的扩展 | 在设备上至少验证 |
| --- | --- |
| 普通插件 | 第一次启动、点击/滑动/导航、保存失败提示、退出重开、目录/包/市场中你声明支持的方式 |
| 锁屏 | 静态背景与文字、所选 when、时钟周期/解锁等待、未校时/无诗库/未连接手机时的提示、解锁返回与方向恢复 |
| 两者 | 错误时用户能恢复操作，最终包版本/字节数/SHA-256与发给别人的文件相符 |

如果能获取固件串口日志，普通插件可找 `lua_plugin`，锁屏可找 `JR_LOCK`、`JR_LOCK_LUA`、`JR_LOCK_TIMER`、`JR_LOCK_FONT`。无法获取日志时，也可以记录错误提示、操作步骤、设备固件版本和扩展版本，交给维护者复现。

不要求读者运行私有仓库中的 CTest、生成器或设备取证脚本；这些属于维护者内部回归。你自己的结构检查、设备观察和市场结果应分开写进[发布说明](/developer/extension-release-template)。

## 常见工具错误

| 提示/现象 | 怎么处理 |
| --- | --- |
| source must be a real directory | 核对当前工作目录及源目录名称，不要把安装包当作源目录参数 |
| output exists | 确认替换后加 --force，或换一个输出文件名 |
| missing lockscreen.json / main.lua | 入口多套了一层文件夹，或实际后缀为 .txt |
| duplicate JSON key / unsupported fields | 删除重复字段或不属于公开配置的自定义字段；发布信息放在说明中 |
| lua.area must fit canvas | 核对 x + width、y + height 没超出 canvas |
| PNG must be 8-bit and noninterlaced | 重新导出为支持的 8-bit、非交错 PNG |
| current market does not accept | 移出 README/JPG/TTF 等不允许成员，或只制作符合本地要求的版本 |
| 命令找不到 uv / Python | 先准备可用命令和解释器；扩展制作不需要安装整套固件开发工具 |
