# 来源与待定事项

## 设计原稿

设计规范原稿与 UI Skill 入口草案保留供查阅；本站正文按主题组织。

- <a href="/design-drafts/read-pico-design-v0.2.1.md" download>下载设计规范原稿</a>
- <a href="/design-drafts/read-pico-ui-skill-v0.2.md" download>下载 Skill 入口原稿</a>

## 来源

以下外部资料只支持各自列出的事实，不证明 JustRead 已实现某项能力。

| 编号 | 资料 | 支持范围与说明 |
| --- | --- | --- |
| S1 | [MindReset 官方 Read Pico 仓库](https://github.com/MindReset/read_pico_firmware) | 4.7 英寸、1216 × 684、16 灰阶、双点触摸与三个电容按键区域 |
| S2 | [官方 Demo Firmware](https://dot.mindreset.tech/docs/read_0/demo_firmware) | 整页功能菜单、partial DU / full GC16、阅读 DU / GL16 / GC16 示例；不是 JustRead 刷新策略 |
| S3 | [Apple iPhone SE 第三代规格](https://support.apple.com/en-us/111866) | 4.7 英寸、1334 × 750；仅作为原草案的小屏比较 |
| S4 | [Apple HIG Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) | 原草案引用的 44 pt 参考尚未核对正文；80 px 是设计估算 |

其他按键语义、亮度隐藏、字号底线与布局规则来自设计原稿。原始 `design.css` 未提供，迁移清单中的 CSS 数值沿用原稿描述。下列五张截图仅作设计参考，不作为已实现功能或实机验收证据。

## 留白设计参考图

五张原始 PNG 均为 1368 × 2432 像素，按宽、高各 2 倍对应 684 × 1216 基准画布；坐标换算方法见[系统组件留白](/design/spacing-and-regions#参考图的使用范围)。图中的结构用于参考，本站布局数值按组件约束重新计算。

| 编号 | 原图 | 参考用途 |
| --- | --- | --- |
| R1 | [首页](/design-reference/home.png) | 阅读信息分组、标题与宿主内容区 |
| R2 | [书库](/design-reference/library.png) | 排序行、封面宫格与分页留白 |
| R3 | [应用](/design-reference/apps.png) | 图标名称单元与宫格间距 |
| R4 | [设置](/design-reference/settings.png) | 前导图标、主副标签与整行留白 |
| R5 | [阅读设置](/design-reference/reading-settings.png) | 少量条目下方空白与尾部控件 |

## 待实机与SDK决定

| 待定项 | 所需证据或决定 |
| --- | --- |
| 灰阶Token与刷新模式组合 | 目标面板、驱动与内容清晰度测试 |
| 局刷累计、全刷时机与耗时 | 字体、内容、面积及温度等实测策略 |
| 字体栅格与状态栏24px字形 | 字体度量、混排与裁字检查 |
| 80×80与顶栏72×80热区 | 触摸准确率与误触测试 |
| 底部4–8px可见性、旋转坐标 | 硬件修订与边缘命中测试 |
| 分页淡出 | 能力、耗时、残影与价值评审；无结论保持关闭 |
| 系统组件、声明协议与协商 | SDK字段、API、版本、能力与生命周期设计 |
| 菜单List / 控制中心 | 最终视觉、容量与操作结构 |
| 长按与去抖 | 各状态下的事件验证；不猜测阈值 |
| 截图 | 格式、路径与访问入口 |
| 锁屏 | 自定义范围、唤醒、解锁与按键语义 |
| 根页Back（补充待定） | 明确退路，不能自行等同于Home或退出 |

待定项允许继续评审设计稿和无动画原型，但不能被写成已验证能力。
