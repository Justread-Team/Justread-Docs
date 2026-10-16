# 存储与文件

## SD 卡

SDMMC 以 Read Pico BSP 的 CLK/CMD/D0 引脚和 1-bit 流程挂载，根目录在应用内为 `/sdcard`。书籍位于 `/sdcard/books/`，用户 TTF 位于 `/sdcard/fonts/`，系统资源位于 `/sdcard/.justread/system/`，插件和锁屏包分别位于 `/.justread/plugins/` 与 `/.justread/screen/`。

SD 初始化失败会尝试降低总线频率并后台重试；无卡启动后可在插卡时重试。运行中移除 SD 卡后，端口先关闭书籍和字体句柄，再尝试恢复挂载及重扫书库。此流程不会格式化 SD 卡。

## NVS 与系统字体

阅读进度、书签、字号、行距、首行缩进、刷新偏好、Wi-Fi 配置、账户状态、锁屏时间和当前锁屏包等设备状态保存在 NVS。Cloud 网页刷机按型号清单写入 Bootloader、分区表、OTA 启动数据和应用分区，不执行整片擦除，因此会保留 NVS；SD OTA 只更新备用应用槽位。

系统字体有固定字节数和 SHA-256 身份，资源安装先写临时文件、校验后再替换正式文件。TTF 正文字形和文件块缓存优先使用 PSRAM；DMA 缓冲及驱动需要的内存保留在内部 RAM。

## 电脑访问 SD

热点/局域网文件服务由 `components/reader_transfer` 提供网页浏览、下载和上传；上传通过临时文件及原子提交，不覆盖已存在同名文件。USB 读卡由 `components/reader_usb_msc` 提供，设备重启后将卡交给电脑；电脑安全弹出后，退出流程把卡还给应用并重启。

SD OTA 路径为 `/.justread/ota/firmware/firmware.bin`。SD OTA 不用于更新分区表。系统资源路径、账户和书籍同步边界见[首次使用](/user/getting-started)与[设置和更新](/user/settings-and-updates)。
