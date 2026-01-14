# AI Friend 项目文档导航

> 快速找到你需要的文档

## 📋 核心文档

### 1. [README.md](../README.md)
**项目简介和快速开始**
- 项目介绍
- 核心功能
- 安装步骤
- 配置说明
- 使用示例

### 2. [PRD.md](PRD.md)
**产品需求文档（最重要）**
- 产品概述和定位
- 功能设计详解
- 技术架构方案
- 用户体验流程
- 开发计划
- Prompt 模板设计

### 3. [TODO.md](TODO.md)
**开发任务清单**
- Phase 1-4 详细任务
- 待确认问题
- 进度追踪
- 问题记录

## 📁 项目结构

```
ai-friend/
├── docs/                    # 文档目录
│   ├── INDEX.md            # 本文件（文档导航）
│   ├── PRD.md              # 产品需求文档
│   └── TODO.md             # 开发任务清单
├── prompts/                # Prompt 模板目录
│   ├── balanced.txt        # 平衡型 Prompt（推荐）
│   ├── enthusiastic.txt    # 激励型 Prompt（热血）
│   └── gentle.txt          # 温柔型 Prompt（治愈）
├── README.md               # 项目说明
└── .vscode/                # VSCode 配置
```

## 🎯 快速导航

### 我想了解...

#### **这个项目是什么？**
→ 阅读 [README.md](../README.md)

#### **有哪些功能？怎么实现的？**
→ 阅读 [PRD.md - 功能设计](PRD.md#二功能设计)

#### **技术架构是怎样的？**
→ 阅读 [PRD.md - 技术架构](PRD.md#三技术架构)

#### **怎么开发这个插件？**
→ 阅读 [TODO.md](TODO.md)，按照 Phase 1-4 逐步开发

#### **Prompt 怎么写？**
→ 阅读 [PRD.md - 附录A](PRD.md#附录-a-核心-prompt-模板)
→ 查看 [prompts/](../prompts/) 目录下的模板文件

#### **有哪些配置项？**
→ 阅读 [PRD.md - 配置项设计](PRD.md#22-配置项设计)

#### **用户体验流程是怎样的？**
→ 阅读 [PRD.md - 用户体验](PRD.md#四用户体验)

## 🔧 开发相关

### 开发前必读
1. [PRD.md - 产品概述](PRD.md#一产品概述) - 理解产品定位
2. [PRD.md - 功能设计](PRD.md#二功能设计) - 了解所有功能
3. [TODO.md - 待确认问题](TODO.md#待确认问题-) - 确认开发方向

### 开发中参考
- [TODO.md](TODO.md) - 对照任务清单开发
- [prompts/](../prompts/) - 使用 Prompt 模板
- [PRD.md - 技术架构](PRD.md#三技术架构) - 查看技术选型

### 开发后检查
- [TODO.md - 进度追踪](TODO.md#进度追踪) - 更新完成度
- [PRD.md - 成功指标](PRD.md#七成功指标) - 对照成功指标测试

## 📝 文档更新日志

| 日期 | 更新内容 |
|------|---------|
| 2026-01-12 | 创建项目文档体系 |
| 2026-01-12 | 完成 PRD.md 初稿 |
| 2026-01-12 | 完成 TODO.md 任务清单 |
| 2026-01-12 | 创建三种 Prompt 模板 |

## 🔗 外部资源

- [AstrBot 官方文档](https://docs.astrbot.app)
- [AstrBot 插件市场](https://plugins.astrbot.app)
- [AstrBot 插件模板](https://github.com/Soulter/helloworld)
- [会话控制 API 参考](https://docs.astrbot.app/zh/dev/star/advanced-features)

---

**提示**: 建议按照 README → PRD → TODO 的顺序阅读文档，可以获得最完整的项目理解。
