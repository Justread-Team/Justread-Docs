# 组件目录

组件页用于快速查阅固件的职责、接口和硬件限制。当前设备端实现以 `JustRead/components/` 与 `JustRead/ports/read_pico/` 为准；设计草案中的 Mini App 系统接口尚未实现。

| 组件 | 当前实现 | 页面 |
| --- | --- | --- |
| [显示与刷新](/components/display) | Read Pico 面板绘制、全屏/局部刷新及清屏 | 已按端口代码整理 |
| [输入与按键](/components/input) | CST836U 触摸、左右滑动和三个按键区域 | 已按端口代码整理 |
| [存储与文件](/components/storage) | SD 卡书库、NVS 偏好与 USB/网络传输 | 已按端口代码整理 |
| [界面组件](/components/ui) | C UI 状态机、布局和系统页面 | 已按头文件及实现整理 |
| [Lua 插件宿主 API](/developer/lua-plugin-api) | SD 卡 Lua 插件、回调和受限设备 API | 当前扩展接口 |

这些页面反映设备端当前实现；Mini App、系统栏 SDK 和第三方应用声明仍属于设计稿范围。
