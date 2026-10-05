import { defineConfig } from 'vitepress'
import llmstxt from 'vitepress-plugin-llms'

export default defineConfig({
  lang: 'zh-CN',
  title: 'JustRead 文档',
  description: 'JustRead 阅读器固件的使用说明、开发指南、组件查询与设计规范。',
  cleanUrls: true,
  // 原稿作为静态下载保留，不作为 Markdown 页面解析。
  srcExclude: ['public/**'],
  vite: {
    plugins: [
      llmstxt({
        ignoreFiles: ['README.md', 'public/**'],
        details: '设计规范以 v0.2.1 草案为基线，系统组件和 Mini App 接口仍属拟议契约。请先阅读 /design/overview.md，再按目录查询具体主题；使用说明和开发指南中仍有待补充页面。',
        customLLMsTxtTemplate: '# {title}\n\n{description}\n\n{details}\n\n## 文档目录\n\n{toc}'
      })
    ]
  },
  themeConfig: {
    siteTitle: 'JustRead',
    nav: [
      { text: '开始使用', link: '/guide/overview' },
      { text: '使用说明', link: '/user/overview' },
      { text: '开发指南', link: '/developer/overview' },
      { text: '在线刷机', link: '/flash' },
      { text: '设计规范', link: '/design/overview' }
    ],
    sidebar: {
      '/guide/': [
        {
          text: '项目入门',
          items: [
            { text: '文档导航', link: '/guide/overview' },
            { text: '产品与版本', link: '/guide/product-and-versions' },
            { text: '快速开始', link: '/guide/quick-start' }
          ]
        }
      ],
      '/user/': [
        {
          text: '使用说明',
          items: [
            { text: '使用说明总览', link: '/user/overview' },
            { text: '首次使用', link: '/user/getting-started' },
            { text: '阅读与文件管理', link: '/user/reading-and-files' },
            { text: '设置与更新', link: '/user/settings-and-updates' },
            { text: '故障排查', link: '/user/troubleshooting' }
          ]
        }
      ],
      '/developer/': [
        {
          text: '开发指南',
          items: [
            { text: '开发总览', link: '/developer/overview' },
            { text: '环境搭建', link: '/developer/setup' },
            { text: '构建、烧录与调试', link: '/developer/build-flash-debug' },
            { text: '代码结构', link: '/developer/codebase' },
            { text: '贡献与发布', link: '/developer/contributing-and-release' }
          ]
        },
        {
          text: '组件查询',
          items: [
            { text: '组件目录', link: '/components/index' },
            { text: '显示与刷新', link: '/components/display' },
            { text: '输入与按键', link: '/components/input' },
            { text: '存储与文件', link: '/components/storage' },
            { text: '界面组件', link: '/components/ui' }
          ]
        }
      ],
      '/design/': [
        {
          text: '基线与设备',
          items: [
            { text: '设计总览', link: '/design/overview' },
            { text: '规范范围与设计原则', link: '/design/principles-and-scope' },
            { text: '设备基准与像素单位', link: '/design/device-and-units' },
            { text: '设计分层与系统职责', link: '/design/architecture' }
          ]
        },
        {
          text: '视觉与布局',
          items: [
            { text: '视觉 Token、排版与留白', link: '/design/visual-and-typography' },
            { text: '系统栏、画布与热区', link: '/design/system-layout' },
            { text: '系统组件留白与区域分配', link: '/design/spacing-and-regions' },
            { text: '分隔线与边界', link: '/design/separators' }
          ]
        },
        {
          text: '交互与刷新',
          items: [
            { text: '导航、分页与状态', link: '/design/interaction-and-states' },
            { text: '按键、菜单与电源', link: '/design/system-actions' },
            { text: '刷新调度与功耗', link: '/design/refresh-and-power' }
          ]
        },
        {
          text: '组件与平台设计',
          items: [
            { text: '系统组件设计目录', link: '/design/components' },
            { text: '首页与小组件', link: '/design/home-and-widgets' },
            { text: 'Mini App 契约草案', link: '/design/mini-app-contract' },
            { text: '设备适配与困难内容', link: '/design/adaptation' }
          ]
        },
        {
          text: '评审与维护',
          items: [
            { text: '设计与实机验收', link: '/design/acceptance' },
            { text: 'AI 辅助设计约定', link: '/design/agent-workflow' },
            { text: '旧截图与 CSS 迁移', link: '/design/migration-notes' },
            { text: '术语表', link: '/design/glossary' },
            { text: '来源、版本与待定事项', link: '/design/sources-and-decisions' }
          ]
        }
      ]
    },
    search: {
      provider: 'local'
    },
    outline: {
      level: [2, 3],
      label: '本页目录'
    },
    docFooter: {
      prev: '上一页',
      next: '下一页'
    },
    lastUpdated: {
      text: '最后更新于'
    },
    footer: {
      message: 'JustRead 项目文档',
      copyright: '内容以各页面注明的固件版本为准。'
    }
  }
})
