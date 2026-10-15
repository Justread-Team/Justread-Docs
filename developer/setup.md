# 开发环境搭建

本文介绍固件开发工具，不介绍 VitePress 文档站环境。文档站使用 Node.js 与 pnpm，见仓库根目录 `justread_docs/README.md`。

## 宿主 UI

准备 Git、CMake、Ninja、C11/C++11 编译器，以及由 UV 管理并安装 `ninja`、`fontTools` 的 Python 环境。构建脚本会在首次运行时检出固定的 Read Pico 参考提交，并将宿主 UI 编译产物放入固件仓库 `build/`。

```sh
uv run --no-project --python <Python 3.12 环境中的 python> python tools/build.py --width 684 --height 1216
```

`tools/build.py --matrix` 会构建脚本中列出的宿主 UI 分辨率，并运行各配置的 CTest；`--keys-only` 构建纯按键输入配置。宿主 UI 的 684 × 1216 库不是可刷入设备的固件。

## ESP32-S3 固件

准备 ESP-IDF 6.1、ESP32-S3 工具链、CMake/Ninja，以及 UV 管理的 Python 3.12 环境。该 Python 环境需包含 `ninja` 和 `fontTools`。先按 Espressif 文档安装 ESP-IDF 和目标芯片工具，再激活 IDF 环境。构建时明确让固件脚本、`idf.py` 和 CMake 使用同一个 Python 环境：

```sh
export PATH="<ESP-IDF Python 工具目录>:$PATH"
source <ESP-IDF 6.1 路径>/export.sh
export IDF_PYTHON_ENV_PATH=<UV Python 环境目录>
export RUI_FONT_PYTHON=<UV Python 环境目录>/bin/python
uv run --no-project --python <UV Python 环境目录>/bin/python python tools/firmware.py --version 0.1.0
```

`IDF_PYTHON_ENV_PATH` 应指向 Python 环境目录，而不是 Python 可执行文件。Windows 环境中的可执行文件路径为 `Scripts/python.exe`。构建输出写入固件仓库 `build/firmware-684x1216/` 或带时钟配置后缀的目录。

## 硬件边界

当前 Read Pico BSP 只允许 684 × 1216 逻辑尺寸。`tools/build.py` 可构建其他尺寸的通用 UI 库，但 `tools/firmware.py` 会拒绝将它们包装成设备固件。更换面板还需匹配 BSP、刷新波形、framebuffer 与触摸映射。
