# Lucide SVG 点阵生成与高清化

## 来源与高清化原则

图形源使用固定版本的 [Lucide 官方 SVG](https://github.com/lucide-icons/lucide)，不从个人 Figma 文件导出图标，也不在固件运行时解析 SVG。当前源版本固定为[Lucide 1.50.0](https://github.com/lucide-icons/lucide/releases/tag/1.50.0)。

SVG 是矢量路径。生成时直接按目标物理槽位栅格化：例如 48 × 48 px 图标输出 48 × 48 点阵，OOBE 插画输出 256 × 256 点阵。路径保持矢量源的曲线和轮廓，在目标分辨率一次性采样；不要先生成低分辨率图片再放大，不要裁边、拉伸、挪动或在采样后插值。描边按目标屏幕上的物理像素配置，256 px 插画槽使用 12 px 描边。

生成器将 SVG 映射到白底，转为灰度后以 50% 阈值量化成纯黑白，再打包成 1 bit/pixel：1 表示黑、0 表示白，字节内最高位优先。1bpp 只改变颜色深度，不降低栅格的目标像素尺寸；目标槽位为 256 × 256 px 时，生成的仍是 256 × 256 点阵。

## 生成步骤

1. 核对 `tools/gen_lucide_bitmap_assets.py` 中固定的 Lucide 版本、图形输入和目标尺寸配置。
2. 在固件仓库根目录运行：

   ```sh
   uv run --no-project python tools/gen_lucide_bitmap_assets.py
   ```

   生成器从固定版本的 Lucide 官方 `icons/` 目录拉取配置的 SVG，临时源文件放在系统临时目录并在运行结束时清理。它需要可用的网络连接和 ImageMagick `magick` 命令；Python 通过 UV 运行，只使用标准库，不需要新增 Python 包。
3. 检查生成区的尺寸与格式：输出槽位应与目标绘制尺寸一致，像素值只有黑白两种，字节按 MSB-first 组织。源 SVG、版本和生成配置是可重复生成来源；生成区由脚本维护，不要手改点阵数据。

维护图标时，先确定 Lucide 图形、目标尺寸和描边，再从固定版本源 SVG 直接生成目标点阵。
