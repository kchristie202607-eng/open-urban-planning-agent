# 开放城市规划智能体平台（OUPAP）

> 开源、本地优先的城市规划工作流 AI 智能体平台。
>
> **开放框架。私有知识。**

[English](./README.md) · [贡献指南](./CONTRIBUTING.md) · [治理](./GOVERNANCE.md) · [隐私](./PRIVACY.md)

---

## 这是什么

OUPAP 是一个开放式的城市规划智能体平台。它的**公共组件**——框架、接口、工作流、文档与评估工具——任何人都可以复用；而**项目数据、GIS 数据集、规划文档、企业知识库**始终留在使用者本地机器上，不上传、不被收集。

这种 "公共框架 / 私有知识" 的双层契约，让敏感行业的从业者也能安全地把 AI 工作流纳入日常生产。

## 架构（概要）

```
用户
  ↓
智能体层（Agents）
  ↓
工作流引擎（Workflow Engine）
  ↓
知识适配层（Knowledge Adapter）
  ↓
评估层（Evaluation Layer）
  ↓
产物（Output）
```

- **公共组件**：框架、接口、工作流、文档、评估工具。
- **私有组件**：项目数据、GIS 数据集、规划文档、企业知识库。

两者通过知识适配层解耦：公共组件只消费"适配后的接口"，从不直接访问私有数据。

## 快速开始（合成示例）

```bash
# 安装（示例命令，以仓库实际说明为准）
pip install -e .

# 本地运行一个工作流（使用合成输入，不涉及任何真实项目数据）
python -m oupap run --input examples/demo_project.json --output output/demo
```

> 运行前请确保未将任何私有目录（`data/`、`output/`、`project_state/`、`backups/`）纳入版本控制。见 [.gitignore](./.gitignore)。

## 目录结构（公共部分）

```
.
├── src/                 # 框架与引擎（公共）
├── config/              # 工作流与接口定义（公共）
├── schemas/             # 输入输出契约（公共）
├── agents/              # 智能体角色定义（公共）
├── examples/            # 合成示例输入（公共，仅合成数据）
├── tests/               # 验收测试（公共）
├── docs/                # 文档（公共）
└── README.md            # 本文件
```

## 贡献

欢迎贡献！请先阅读 [CONTRIBUTING.md](./CONTRIBUTING.md) 与 [行为准则](./CODE_OF_CONDUCT.md)。
所有贡献**仅使用合成或公开信息**，不得提交任何私有规划资料。

## 许可证

[Apache-2.0](./LICENSE)。
