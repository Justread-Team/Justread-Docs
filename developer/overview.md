# 开发总览

本部分面向 JustRead 固件开发者。设备代码位于独立仓库 `JustRead/`；文档站位于 `justread_docs/`，两者有各自的工具链和 Git 历史。

## 开发路径

如果只是安装扩展，前往[插件和锁屏使用说明](/user/extensions)。如果想写 Lua 插件或锁屏模板，先读[扩展入门路线](/developer/extensions)，无需先完成固件编译。下列步骤面向修改固件本身的开发者。

1. 按[环境搭建](/developer/setup)安装项目实际要求的工具链。
2. 阅读[代码结构](/developer/codebase)，找到入口、驱动、业务逻辑和界面实现。
3. 按[构建、烧录与调试](/developer/build-flash-debug)验证修改。
4. 按[贡献与发布](/developer/contributing-and-release)提交变更并记录兼容性。

固件目标为 ESP-IDF 6.1、ESP32-S3、小纸 Pico 684 × 1216 逻辑分辨率。宿主 UI 构建还需要 CMake、Ninja、C/C++ 编译器和 Python 工具环境。

## 锁屏与插件开发

- [开发总览](/developer/extensions)：选用锁屏或普通插件，了解权限与兼容性边界。
- [运行原理](/developer/extensions-runtime)：理解解释器、宿主、回调、画布与显示刷新。
- [第一个插件](/developer/plugin-tutorial)、[第一个锁屏](/developer/lockscreen-tutorial)：从复制最小例子开始，逐步加入按钮、存档或时钟。
- [绘图详解](/developer/lua-plugin-ui)、[设备与存档详解](/developer/lua-plugin-services)、[锁屏数据接口](/developer/lockscreen-data)：按函数讲解参数、数据来源、失败值和用法。
- [Lua 插件 API](/developer/lua-plugin-api)：入口、生命周期、事件、绘图、存储与资源预算。
- [锁屏模板规范](/developer/lockscreen-development)：JSON 字段、PNG/字体、Lua 时序、时钟与 ANCS 接口。
- [打包、安装与验证](/developer/extension-packaging)：`.jrpack` / `.lspack` 制作、三种安装渠道差异和验收步骤。
- [扩展发布文档模板](/developer/extension-release-template)：按已实现接口编写开发与使用说明，记录发布产物与验证证据。

设计目录中的 Mini App 和系统 SDK 内容是设计草案；不要将其当作当前设备运行时接口。
