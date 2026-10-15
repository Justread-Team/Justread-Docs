# 代码结构

设备固件代码位于 `JustRead/`。按下表定位常见改动：

| 任务 | 入口或模块 | 说明 |
| --- | --- | --- |
| UI 页面、文案、交互和分页 | `src/reader_ui.c`、`include/reader_ui.h` | 通用 C UI 状态机与渲染；尺寸由生成的 `rui_config.h` 决定 |
| 阅读器和板级服务集成 | `ports/read_pico/app_reader_ui.c` | 打开 TXT/EPUB、NVS 进度、字体、Wi-Fi、云服务、OTA、资源和插件的设备端调度 |
| 启动与设备初始化 | `ports/read_pico/reader_main.c` | SD、Wi-Fi、传输、云端、OTA、字体和应用循环初始化 |
| 显示和刷新 | `ports/read_pico/reader_display.c`、`components/reader_support/reader_refresh.*` | 小纸 Pico 显示 HAL、区域和刷新模式 |
| 触摸输入 | `ports/read_pico/reader_input_esp.*`、`components/reader_support/reader_input_queue.*` | 独立采样任务和有界事件队列 |
| 设置持久化 | `ports/read_pico/reader_preferences.c` | 阅读偏好、锁屏时间和模板选择的 NVS 读写 |
| SD 卡书库 | `ports/read_pico/reader_sd.c`、上游 `book_*` 模块 | 挂载、扫描、书籍读取、进度与文件媒体恢复 |
| 通用组件 | `components/adaptive_ui`、`reader_support`、`reader_lockscreen` | 布局自适应、阅读支持和锁屏配置解析 |
| 网络服务 | `components/reader_wifi`、`reader_cloud`、`reader_ota`、`reader_resources`、`reader_transfer`、`reader_usb_msc` | Wi-Fi、账户/同步、更新、系统资源、网页传输和 USB SD 读卡 |
| 插件系统 | `components/reader_plugins` | 从 SD 卡加载受限 Lua 插件 |
| 工程生成与裁剪 | `tools/build.py`、`tools/firmware.py`、`tools/pico_profile.py` | 固定上游参考、生成 UI、裁剪固件依赖并打包 |
| 能力审计 | `tools/audit_firmware.py` | 检查分区、镜像体积、ELF 能力和内嵌字体 |

文档站本身位于兄弟目录 `justread_docs/`，通过 pnpm 和 VitePress 构建。`design/` 中系统组件、Mini App 和首页小组件接口是设计材料，不是当前固件目录结构或 API。
