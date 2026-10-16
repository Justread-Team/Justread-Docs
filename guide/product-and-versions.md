# 产品与版本

## 产品定位

JustRead 是小纸 Pico 的阅读器固件。设备端读取 SD 卡书籍，提供 TXT/EPUB 阅读、设备设置、联网更新、文件传输和 SD 卡 Lua 插件。当前固件工程以 Read Pico 的 ESP32-S3 BSP 为基础；项目构建脚本固定使用 MindReset/read_pico_firmware 提交 `28cde682a4468a581c278761922724f57d976418` 作为硬件能力参考。

设备端固件 UI 构建脚本只接受 684 × 1216 逻辑坐标。设备实际面板为 1216 × 684，显示方向由固件端口处理。通用 UI 组件可单独构建其他逻辑尺寸，但这不代表设备 BSP 支持其他面板。

## 版本兼容表

| 版本标识 | 硬件目标 | 关键范围 | 文档状态 |
| --- | --- | --- | --- |
| 构建脚本默认 `0.1.0`；发布版本以 CDN `release.json` 为准 | 小纸 Pico，ESP32-S3，16 MiB Flash，1216 × 684 面板 | TXT/EPUB 阅读、SD 卡字体、Wi-Fi、Reader Cloud、SD OTA、热点/局域网/USB 文件访问、Lua 插件与锁屏模板 | 代码已核对；硬件修订号及各版首次支持记录尚未集中维护 |

`0.1.0` 是 `tools/firmware.py` 的默认嵌入版本，不等于当前线上发布版本。小纸 Pico 的设备更新页从 `https://cdn.xmoa.smn.icu/downloads/mindreset-read-pico-s3/release.json` 查询发布版本；其它型号使用其型号目录中的 `release.json`。

## 写作规则

- 区分固件版本与硬件修订版，不要只写“最新版”。
- 行为变化注明从哪个版本开始生效；仍有差异时用表格列出。
- 尚未验证的兼容关系标为“待核实”。
