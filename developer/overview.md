# 开发总览

本部分面向 JustRead 固件开发者。设备代码位于独立仓库 `JustRead/`；文档站位于 `justread_docs/`，两者有各自的工具链和 Git 历史。

## 开发路径

1. 按[环境搭建](/developer/setup)安装项目实际要求的工具链。
2. 阅读[代码结构](/developer/codebase)，找到入口、驱动、业务逻辑和界面实现。
3. 按[构建、烧录与调试](/developer/build-flash-debug)验证修改。
4. 按[贡献与发布](/developer/contributing-and-release)提交变更并记录兼容性。

固件目标为 ESP-IDF 6.1、ESP32-S3、小纸 Pico 684 × 1216 逻辑分辨率。宿主 UI 构建还需要 CMake、Ninja、C/C++ 编译器和 Python 工具环境。

## 插件开发

- [Lua 插件 API](/developer/lua-plugin-api)：设备当前实现的 SD 卡 Lua 插件入口与 API。

设计目录中的 Mini App 和系统 SDK 内容是设计草案；不要将其当作当前设备运行时接口。
