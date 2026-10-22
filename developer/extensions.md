# 锁屏与插件开发总览

想使用别人制作的插件，先看安装说明；想自己做，先按教程运行一个最小例子，再查参数表。本组文章按读者无法获取私有固件仓库编写，完整示例和<a href="/tools/justread_pack.py" download>独立打包工具</a>均随文档提供。

## 按你的目标选文章

| 你现在想做什么 | 从哪里开始 | 读完能做什么 |
| --- | --- | --- |
| 安装现成插件或换一个锁屏 | [安装与使用](/user/extensions) | 认清包格式、放进 SD 卡、在设备上启用和退出 |
| 理解 Lua、API、回调和墨水屏刷新 | [运行原理](/developer/extensions-runtime) | 知道谁加载代码、何时调用函数、为什么画图后还要刷新 |
| 第一次写插件，不熟悉 Lua | [插件入门教程](/developer/plugin-tutorial) | 从一句文字做到按钮、计数、保存和退出 |
| 只想改锁屏文字，再做时钟 | [锁屏入门教程](/developer/lockscreen-tutorial) | 从两份 JSON 做到周期时钟，理解 area 和 when |
| 查绘图参数和局刷用法 | [绘图详解](/developer/lua-plugin-ui) | 理解每个参数、返回值、坐标和常见错误 |
| 查电量、阅读状态和存档 | [设备与存档详解](/developer/lua-plugin-services) | 正确读取数据、处理 nil/false、持久化自己的状态 |
| 在锁屏显示字数、诗句、通知 | [锁屏数据接口](/developer/lockscreen-data) | 理解数据来源并制作完整的信息卡模板 |
| 已熟悉开发，只需精确约束 | [插件 API 参考](/developer/lua-plugin-api)、[锁屏配置参考](/developer/lockscreen-development) | 查询完整签名、字段、预算和兼容性 |
| 准备交给其他用户 | [打包规范](/developer/extension-packaging)、[发布说明模板](/developer/extension-release-template) | 选择交付方式，记录安装步骤与验证证据 |

只安装扩展不需要开发工具。普通插件目录中的 main.lua 可以直接交给固件读取；制作锁屏安装包或分发插件包时，才需要运行打包工具。只有修改固件本身或维护宿主接口时，才进入[固件构建流程](/developer/build-flash-debug)。

## 适用范围与验证状态

适用范围：小纸 Pico / ESP32-S3，默认逻辑分辨率 684 × 1216。接口于 2026-10-22 按当前实现核对，不代表每个示例已经完成实机验收，也尚未据此确定最早支持的发布版本。使用者从设备“关于”记录固件版本，并按教程验证目标功能；其他机型不能仅凭分辨率相同就认定兼容。

## 从需求选择扩展方式

| 需求 | 锁屏模板 `.lspack` | 普通 Lua 插件 `.jrpack` / 目录 |
| --- | --- | --- |
| 入口 | `lockscreen.json` + `images.json`，可选 Lua | 根 `main.lua` 返回插件 table |
| 使用场景 | 进入锁屏、锁屏期间、解锁前 | 用户从插件列表主动打开的应用 |
| 画布 | 整屏静态场景；Lua 只操作配置的 `area` | 扣除系统状态栏、顶栏和可选底栏后的画布 |
| 用户输入 | 不向 Lua 分发触摸或按键 | 点击、四向滑动、系统导航事件 |
| 数据 | 只读 `config`、`clock`、`poetry`，可声明 ANCS | `device.status`、`reader.status`、插件私有 `storage` |
| 图像 | 静态 PNG、Lua 小 PNG、字形图集 | 基本图形和文字；目录模式可用系统导航位图 |
| 刷新周期 | `when = "locked"` 时由配置定时 | `on_tick` 约 100 ms；插件自行决定是否刷新 |
| 退出 | 系统解锁流程控制 | 系统返回、实体键、`plugin_exit()` |

两者复用同一个 Lua VM 组件，但权限不同。普通插件不能调用锁屏专用 `clock`、`config`、`ancs`、`poetry`、`ui.image` 或 `ui.glyph`；锁屏也没有普通插件的设备、阅读、存储、蜂鸣器或主动退出接口。两者都没有通用文件系统、网络或任意 BLE/GATT API。

## 开发顺序

1. 按[第一个插件](/developer/plugin-tutorial)或[第一个锁屏](/developer/lockscreen-tutorial)保存页面提供的完整文件。
2. 确定交付途径：目录复制、本地导入包、云市场。三者的插件附属资源支持不同，见[打包与验证](/developer/extension-packaging)。
3. 使用[文档配套打包器](/developer/extension-packaging#packer)生成 `.jrpack` / `.lspack`，检查包根目录、资源引用、大小和编码。
4. 在目标设备验证显示、交互、退出和故障恢复；打包成功、文档构建成功都不能代替这一步。
5. 使用[扩展发布文档模板](/developer/extension-release-template)记录接口依赖、安装方式、兼容性与验证证据。

建议先做只依赖单个 `main.lua` 的普通插件，或 `texts` 加空 `images.json` 的静态锁屏。确认可安装、可退出后再增加资源与定时逻辑。

## 当前兼容性边界

- 普通插件的源码只从 `main.lua` 加载，`require`、`loadfile` 等不可用；多模块工程应在发布前合并为一个入口文件。
- 本地 `.jrpack` 从包内读取入口，导航图标和私有存储仍走同名目录路径；云市场安装只落地入口。跨这三种交付方式的插件应仅依赖入口源码，使用系统默认导航图标。需要附属图标或持久化时，优先采用目录安装并写明限制。
- 历史 `PLUGINS.md` 提到 `key` 事件；当前 Pico `key()` 直接关闭插件，并未把该事件传入 Lua。不要发布依赖硬件键控制的插件，除非在目标固件上确认过适配。
- 固件支持锁屏包内 `.ttf`，当前云端锁屏扫描允许列表不接受 `.ttf`；市场模板使用 `font_file: "system"` 或 PNG 图集。
- 锁屏 JSON 的 `refresh` 与 Lua `ui.refresh()` 是两套枚举；不要互换 `full_gc16` 和 `full_bw`。同名 `full_gray` 在普通插件与锁屏适配层的波形映射也不同。

这些是核对时的实现行为。修复或扩展接口后，应同时更新示例、打包检查、对应页面和发布文档，不要仅修改文字承诺。

## 维护者附录：核对依据

以下是提供给有内部源码权限的维护者的追溯资料，普通扩展作者不需要获取这些文件。本组教程、API 和工具已包含制作扩展所需的公开约定。内部核对基线为固件提交 9aa33da 的工作树，路径相对固件或云端仓库：

| 来源 | 用途 |
| --- | --- |
| `components/reader_plugins/include/reader_plugins.h`、`src/reader_plugins.c` | Lua globals、参数校验、回调、预算 |
| `ports/read_pico/app_reader_ui.c` | 普通插件扫描、输入、画布、存储、图标、本地与市场安装 |
| `components/reader_lockscreen/include/reader_lockscreen.h`、`src/reader_lockscreen.c` | JSON schema、静态场景与缩放 |
| `components/reader_lockscreen/src/reader_lock_png.c`、`reader_lock_vars.c` | PNG 与固定变量校验 |
| `ports/read_pico/reader_lock_esp.c`、`reader_loop.c` | 锁屏时序、Lua area、刷新、计时和退出 |
| `tools/package_jrpack.py`、`tools/package_lspack.py` | 打包器实际检查范围 |
| `backend/app/scanner.py`、`api_market.py`（云端） | 投稿扫描、类别大小与市场元数据 |

维护者负责在接口变化时更新这些公开页面和独立工具，不应要求外部作者自行核对内部实现。文档站的 [Mini App 契约](/design/mini-app-contract)仍是设计草案，不能作为当前 Lua 接口使用。
