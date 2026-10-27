---
title: 在线刷写 JustRead
description: 从 Cloud 型号清单加载 ESP32-S3 小纸 Pico 分区镜像的浏览器刷机界面。
outline: false
aside: false
footer: false
pageClass: flash-layout
---

<script setup>
import FlashPanel from './FlashPanel.vue'
</script>

<FlashPanel />

刷机页会分别读取所选 Stable 或 Canary 通道的 OTA 发布清单，并且只提供与该版本应用镜像大小及 SHA-256 一致的全量刷机包。所选通道没有匹配的全量包时，刷写按钮会保持不可用，不会自动切换到另一个通道。
