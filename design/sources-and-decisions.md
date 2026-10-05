# 来源、版本与待定事项

> 设计基线：v0.2.1 · 2026-10-05。状态：草案，尚未通过 JustRead 固件与实机验收；硬性规则约束目标设计，组件与平台接口仍为拟议契约。

## 材料与版本

设计基线来源：《Read Pico 系统界面、Mini App 与小组件设计规范》v0.2.1，日期2026-10-05；辅助入口来源：《Read Pico UI Skill｜SKILL.md 入口草案》v0.2，同日。

- <a href="/design-drafts/read-pico-design-v0.2.1.md" download>下载设计规范原稿</a>
- <a href="/design-drafts/read-pico-ui-skill-v0.2.md" download>下载 Skill 入口原稿</a>

原稿作为可追溯资料保留。本站只拆分、规范Markdown和补充说明；新增方案均标为补充建议或拟议补充，不自动改变硬性基线或声明协议版本。

## 来源

本次于2026-10-05核对S1–S3与S5；S4没有读到可验证正文。以下外部资料只支持各自列出的事实，不证明JustRead已实现某项能力。

| 编号 | 资料 | 支持范围与核对状态 |
| --- | --- | --- |
| S1 | [MindReset官方Read Pico仓库](https://github.com/MindReset/read_pico_firmware) | 已核对：4.7英寸、1216×684、16灰阶、双点触摸与三个电容按键区域 |
| S2 | [官方Demo Firmware](https://dot.mindreset.tech/docs/read_0/demo_firmware) | 已核对：整页功能菜单、partial DU / full GC16、阅读DU / GL16 / GC16示例；不是JustRead刷新策略 |
| S3 | [Apple iPhone SE第三代规格](https://support.apple.com/en-us/111866) | 已核对：4.7英寸、1334×750；仅作为原草案的小屏比较 |
| S4 | [Apple HIG Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) | 本轮未核对正文；44pt引用保留为原草案参考，80px仍是设计估算 |
| S5 | [Read Pico Getting Started](https://dot.mindreset.tech/docs/read_0/start) | 已打开：设备入口；不用于定义JustRead用户教程 |

其他按键语义、亮度隐藏、字号底线与布局规则来自用户提供的草案。原始 `design.css` 未提供，迁移清单中的 CSS 数值沿用草案描述。后续收到的五张截图归为下列设计参考，不作为已实现功能或实机验收证据。

## 留白设计参考图

2026-10-05 提供，原图均为 1368 × 2432（基准画布的 2 倍）。[系统组件留白](/design/spacing-and-regions)记录结构观察与重新计算的推荐值，未宣称逐像素复原截图。

| 编号 | 原图 | 参考用途 |
| --- | --- | --- |
| R1 | [首页](/design-reference/home.png) | 阅读信息分组、标题与宿主内容区 |
| R2 | [书库](/design-reference/library.png) | 排序行、封面宫格与分页留白 |
| R3 | [应用](/design-reference/apps.png) | 图标名称单元与宫格间距 |
| R4 | [设置](/design-reference/settings.png) | 前导图标、主副标签与整行留白 |
| R5 | [阅读设置](/design-reference/reading-settings.png) | 少量条目下方空白与尾部控件 |

## 原稿章节映射

| 原稿 | 本站页面 |
| --- | --- |
| §1、§3 | [范围与原则](/design/principles-and-scope) |
| §2 | [设备与单位](/design/device-and-units) |
| §4 | [视觉Token](/design/visual-and-typography) |
| §5 | [系统几何](/design/system-layout) |
| §6.1–6.4 | [导航与分页](/design/interaction-and-states) |
| §6.5–6.7 | [系统动作](/design/system-actions) |
| §7 | [刷新与功耗](/design/refresh-and-power) |
| §8 | [组件设计](/design/components) |
| §9 | [首页与小组件](/design/home-and-widgets) |
| §10 | [分隔线](/design/separators) |
| §11 | [Mini App契约](/design/mini-app-contract) |
| §12 | [适配与困难内容](/design/adaptation) |
| §13 | [旧稿迁移](/design/migration-notes) |
| §14 | [验收](/design/acceptance) |
| §15及Skill入口 | [AI工作流](/design/agent-workflow) |
| §16 | 本页 |

[系统职责](/design/architecture)与[术语表](/design/glossary)是本次补充整理，用于连接规则，不宣称真实模块或API已存在。

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

## 整理记录

2026-10-05：保持v0.2.1设计草案；拆分主题、修复表格与JSON代码块、加入计算例子、状态表与验收模板。声明示例的`designSpecVersion`由0.2精确为0.2.1，仅说明参考基线；`manifestSchemaVersion`保持0.1-draft。Skill入口版本不变，未安装到Agent工具。

同日追加：依据五张新提供的设计图增加系统组件留白页，补充设置行、宫格、分页区与宿主职责，更新验收和参考资料。新增数值保持补充建议性质，设计基线与 Mini App 声明格式版本不变。

后续变更记录建议包含日期、原规则、新决定、理由、影响页面、是否改变设计或协议版本、验证证据和未完成项。
