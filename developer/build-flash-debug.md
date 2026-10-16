# 构建、烧录与调试

## 宿主 UI 构建

在固件仓库根目录运行：

```sh
uv run --no-project --python <UV Python 3.12> python tools/build.py --width 684 --height 1216
uv run --no-project --python <UV Python 3.12> python tools/build.py --matrix
```

脚本会构建并运行相应布局测试。产物位于 `build/<宽>x<高>/`，包括 UI 库、模拟器和 manifest；它们不是设备刷写镜像。

## 设备固件构建

在 ESP-IDF 6.1 激活环境后，使用同一个 UV Python 环境运行：

```sh
export PATH="<ESP-IDF Python 工具目录>:$PATH"
source <ESP-IDF 6.1 路径>/export.sh
export IDF_PYTHON_ENV_PATH=<UV Python 环境目录>
export RUI_FONT_PYTHON=<UV Python 环境目录>/bin/python
uv run --no-project --python <UV Python 环境目录>/bin/python python tools/firmware.py --version 0.1.0
```

默认构建 684 × 1216、80 MHz Flash/PSRAM 配置并启用云服务。`--memory-clock-profile 120` 可生成 120 MHz 实验配置；`--disable-cloud` 关闭云服务；`--serial-bench` 只用于临时硬件验收，不应作为发布镜像。

成功构建后，目录 `build/firmware-684x1216-80mhz/` 中包含独立工程、`artifacts-ota/firmware.bin` 和 `paper-reader-684x1216-80mhz.zip`。压缩包含 OTA 应用镜像、bootloader、分区表、初始 otadata、`flash_args.txt`、审计结果、资源和许可证。

## 烧录方式

- **OTA 更新**：设备设置页写入备用应用槽位，只适用于已有匹配分区表的设备。
- **首次安装或分区迁移**：在线刷机页从 Cloud 的 `models.json` 和型号 `web-flash.json` 读取镜像与分区地址，并逐个校验、写入和回读清单分区。发布包中的 `flash_args.txt` 也可用于命令行写入对应镜像。不要用单独的 OTA `firmware.bin` 更新分区表。
- **USB SD 读卡**：设备重启进入 USB MSC 后，电脑安全弹出卡片，再从设备退出并重启。

刷写前确认型号与 ESP32-S3 小纸 Pico 实机一致。网页刷机不擦除整片 Flash，会保留 NVS 和 SPIFFS；本文不推断串口名称，按系统实际枚举结果选择设备。

## 日志与问题定位

设备通过 USB Serial/JTAG 输出 ESP-IDF 日志。可按 `JR_OPEN`、`JR_TURN`、`JR_SD`、`JR_FONT`、`JR_OTA`、`JR_CLOUD` 和 `JR_RESOURCE` 标签定位开书、翻页、SD、字体、更新、云服务和资源流程。正式固件不含 `--serial-bench` 测试命令；硬件验收结束后应刷回正式固件。
