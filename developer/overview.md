# 开发总览

本部分面向 JustRead 固件开发者。先记录经过验证的开发流程，再把复杂主题拆成独立页面。

## 开发路径

1. 按[环境搭建](/developer/setup)安装项目实际要求的工具链。
2. 阅读[代码结构](/developer/codebase)，找到入口、驱动、业务逻辑和界面实现。
3. 按[构建、烧录与调试](/developer/build-flash-debug)验证修改。
4. 按[贡献与发布](/developer/contributing-and-release)提交变更并记录兼容性。

工具链版本、构建命令和目标板信息均待从仓库与项目维护者处核实。

## 插件开发

- [Lua 插件 API](/developer/lua-plugin-api)：插件入口、系统状态栏与顶栏、可选底栏和自定义图标格式。
