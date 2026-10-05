# JustRead 文档站

这是独立的 VitePress 文档项目，使用 pnpm 管理前端依赖。Markdown 页面位于各内容目录中，站点配置位于 `.vitepress/config.mts`。

## 本地运行

需要 Node.js 22 或更高版本及 pnpm。首次在本目录执行：

```sh
pnpm install
pnpm docs:dev
```

终端会显示本地预览地址。编辑 Markdown 并保存后，浏览器会自动刷新。

## 常用命令

```sh
pnpm docs:dev      # 本地开发预览
pnpm docs:build    # 生成静态站点
pnpm docs:preview  # 预览静态构建结果
```

## AI Agent 访问

站点已接入 `vitepress-plugin-llms`，构建时生成供 Agent 直接读取的 Markdown。目录结构使用站点侧边栏分组。

| 路径 | 内容 |
| --- | --- |
| `/llms.txt` | 文档目录及逐页 Markdown 链接 |
| `/llms-full.txt` | 文档全文合集 |
| `/design/system-layout.md` 等 | 对应页面的 Markdown 正文 |

建议 Agent 先读取 `/llms.txt`，再按需获取主题页。索引保留设计草案与拟议接口的状态说明；文档站 README 和 `public/` 下的原稿下载文件不参与正文合集。

这些文件由 `pnpm docs:build` 生成。插件在开发模式下读取上一次构建产物，因此修改文档后需要重新构建，才会更新 Agent 访问的 Markdown。可用 `pnpm docs:preview` 查看本次构建结果。

## 新增页面

1. 在合适的目录新建 `.md` 文件，例如 `user/power.md`。
2. 在 `.vitepress/config.mts` 中对应的侧边栏分组添加链接，路径从站点根开始并以 `/` 开头。
3. 页面说明适用的固件版本、硬件修订版和验证状态。
4. 在本地开发预览中检查页面和导航。

目录按读者与任务划分：`guide/` 为入口与版本信息，`user/` 为设备使用说明，`developer/` 为固件开发流程，`components/` 为组件查询，`design/` 为设计规范。文档站本身的操作说明放在本 README 中。
