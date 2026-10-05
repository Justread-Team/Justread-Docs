# Mini App 声明与平台契约草案

> 设计基线：v0.2.1 · 2026-10-05。状态：草案，尚未通过 JustRead 固件与实机验收；硬性规则约束目标设计，组件与平台接口仍为拟议契约。

以下 JSON 仅说明未来协议应该包含哪些信息，**不是可直接调用的固件配置**。字段名称可在 SDK 实现时调整。文档版本、设计规范版本与未来 Mini App 声明格式版本应分别管理：修改文案或视觉建议不应自动迫使声明协议升级。下面的 `designSpecVersion` 表示应用所遵循的设计规范版本；`manifestSchemaVersion` 仅表示此声明草案自身的结构版本。

```json
{
  "designSpecVersion": "0.2.1",
  "manifestSchemaVersion": "0.1-draft",
  "orientation": "portrait",
  "fullscreen": false,
  "appBar": {
    "enabled": true,
    "title": "书库",
    "back": true,
    "actions": [
      { "id": "search", "icon": "search", "label": "搜索" }
    ]
  },
  "bottomNavigation": {
    "enabled": false,
    "items": []
  },
  "systemSeparators": {
    "top": false,
    "bottom": false
  },
  "pagination": {
    "axis": "vertical",
    "transition": "none"
  },
  "widget": {
    "supported": true,
    "title": "最近阅读",
    "icon": "library",
    "preferredSize": { "width": 612, "height": 600 }
  }
}
```

拟议运行时应提供：应用画布、系统交互保留区域、有效可见范围、语义输入事件、刷新能力与请求入口。应用不能直接假定系统组件存在，也不能自行控制全局刷新节奏。

## 字段语义与约束（补充建议）

下表用于设计评审，不是已发布的 JSON Schema。

| 字段 | 含义与约束 |
| --- | --- |
| `designSpecVersion` | 示例精确引用 0.2.1；原草案为 0.2，此处只修正文档引用 |
| `manifestSchemaVersion` | 声明结构版本，与文档及固件版本独立 |
| `orientation` | 本版默认 portrait；横屏需单独评审 |
| `fullscreen` | 隐藏默认系统栏；显式请求 App Bar / 底栏仍占空间 |
| `appBar` | 系统标题、返回与工具；工具需有语义名称 |
| `bottomNavigation` | 启用时建议 2–5 项，不得超过 5 项 |
| `systemSeparators` | 默认关闭；不改变分配几何 |
| `pagination` | 分页方向与切换方式；默认无动画，不启用自然滚动 |
| `widget` | 声明首页小组件；preferredSize 不保证其他设备分配相同尺寸 |

`appBar.back` 只声明可见返回入口，不取代系统 Back。应用自定义菜单声明不在原 JSON 中；菜单来源、动作标识和生命周期需未来 SDK 定义，不能提前宣称已有 `menu` 字段。

运行时以返回的应用画布、保留区和可见范围为准。能力不支持时建议给出明确拒绝或降级说明，不能静默裁切热区、缩小字号或伪造刷新能力。字段类型、能力协商、错误码及生命周期回调仍待实现评审。
