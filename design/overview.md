# 设计规范总览

> 设计基线：v0.2.1 · 2026-10-05。状态：草案，尚未通过 JustRead 固件与实机验收；硬性规则约束目标设计，组件与平台接口仍为拟议契约。

本组文档定义JustRead在Read Pico上的系统界面、Mini App与首页小组件目标设计。内容来自v0.2.1设计草案和v0.2 Skill入口草案，按查询主题拆分，保留必须、建议与待验证的区别。

先读[范围与原则](/design/principles-and-scope)和[设备与单位](/design/device-and-units)，再按任务查阅。设计已写成规则，不代表系统组件、SDK或固件行为已经实现。

## 视觉与系统布局

- [视觉Token、排版与留白](/design/visual-and-typography)：四类语义色、字号、行高、图标与内容线。
- [系统栏、应用画布与热区](/design/system-layout)：系统区域、几何分配、点击范围与计算例子。
- [系统组件留白与区域分配](/design/spacing-and-regions)：设置行、宫格、分页控件与宿主留白，附五张设计参考图。
- [分隔线的有限例外](/design/separators)：留白优先与必要边界。

## 交互与刷新

- [导航、分页与状态](/design/interaction-and-states)：整页切换、返回、指示器和异常状态。
- [按键、菜单、截图与电源](/design/system-actions)：全局动作、临时覆盖层与待定锁屏。
- [刷新调度与功耗](/design/refresh-and-power)：变化区域、完整清除、合并与实测策略。

## 组件与平台设计

- [系统职责](/design/architecture)：设计层与所有权边界。
- [组件设计目录](/design/components)：PagedList、IconGrid、CoverGrid与基础控件。
- [首页与小组件](/design/home-and-widgets)：基准布局、612×600内容区与宿主契约。
- [Mini App契约草案](/design/mini-app-contract)：声明示例、字段语义和运行时边界。
- [设备适配与困难内容](/design/adaptation)：字号放大、长文本与版本差异。

## 评审与维护

- [设计与实机验收](/design/acceptance)：清单、记录模板与场景矩阵。
- [AI辅助设计约定](/design/agent-workflow)：入口草案与按任务读取路径。
- [旧截图与CSS迁移](/design/migration-notes)：原草案问题与证据范围。
- [术语表](/design/glossary)与[来源、版本及待定事项](/design/sources-and-decisions)：名词、原稿下载、章节映射与决策记录。

本文档整理版本不等于新的固件发布。没有真机证据时保持未验证；没有SDK证据时保持拟议，补充建议待评审后再转为基线要求。
