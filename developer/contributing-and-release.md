# 贡献与发布

## 修改与验证

固件仓库与文档站是两个独立 Git 仓库。固件改动应在 `JustRead/` 中完成；文档站页面和 VitePress 配置在 `justread_docs/` 中维护。改动 UI 行为时对照 `include/reader_ui.h`、平台端口和组件实现；仅在设计稿中出现的能力应明确标为提案。

宿主 UI 可用 `tools/build.py --matrix` 构建矩阵并执行随构建配置的 CTest。设备固件用 ESP-IDF 6.1 和 `tools/firmware.py` 构建；发布前审阅生成的能力审计、分区表、应用摘要和目标硬件验证记录。刷机、云市场和屏幕光学响应的实机验证不能由编译成功替代。

## 版本与产物

`tools/firmware.py` 默认嵌入版本 `0.1.0`，可用 `--version` 指定语义版本。线上 OTA 版本来自型号目录中的 Reader Cloud `release.json`，发布时应与嵌入版本保持一致，并提供更新说明、字节数和 SHA-256。设备 OTA 发布独立应用 `firmware.bin`；网页刷机另外发布型号目录的 `web-flash.json` 和其列出的 Bootloader、分区表、OTA 启动数据、应用镜像，以支持首次安装和分区表迁移。

发布前更新用户指南中与变化相关的页面，并记录适用硬件、固件版本、代码审查状态和实机验证状态。不要把 `--serial-bench` 镜像作为正式包发布。
