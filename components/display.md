# 显示与刷新

## 设备与坐标

设备端口面向小纸 Pico 的 ESP32-S3 和 1216 × 684 物理面板。阅读 UI 使用 684 × 1216 竖屏逻辑坐标；`tools/firmware.py` 会拒绝其它设备固件分辨率。通用宿主 UI 支持更多布局尺寸，但不会改变面板能力。

显示端口位于 `JustRead/ports/read_pico/reader_display.c`，面板绘制和波形来自固定版本 Read Pico BSP。通用 UI 通过 `rui_refresh_t` 表达刷新意图，端口把它映射到驱动波形；新面板需要匹配的 BSP、坐标映射、framebuffer 和刷新策略。

## 刷新模式

设备 UI 提供四种意图：全屏黑白、全屏 16 灰度、局部黑白和局部灰度。局部灰度请求在当前安全策略下转为黑白局部刷新。阅读设置选择黑白或 16 灰度的全屏翻页模式；显示清理使用单独操作，不等同于普通 UI 刷新。

黑白阅读使用上游 FOLLOW DU 波形。非阅读界面沿用标准波形；过渡期间可延后全屏清理。波形名字描述驱动模式，不承诺固定视觉稳定时间。阅读耗时日志止于同步显示驱动返回，未测量墨水屏光学稳定时间。

## 接口

`reader_display_present(state, mode, region, input_binary)` 接收逻辑区域并提交刷新；`reader_display_cleaned(binary)` 通知清理完成。读写屏幕时应由端口的显示锁协调，OTA 写 Flash 期间 UI 渲染与屏幕刷新互斥。后台 SD/网络批量 I/O 会请求更安全的显示时钟和扫描队列。
