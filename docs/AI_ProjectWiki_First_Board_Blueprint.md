# AI Project Wiki / Project Memory 首板蓝图

> 版本：v0.1 首板设计稿  
> 目标：把当前讨论沉淀成一个可以交给 Codex 继续开发的产品蓝图。  
> 核心定位：面向个人开发者、高校实验室、小团队、开源项目和混乱软件项目的开源 AI Project Wiki。

---

## 0. 一句话定义

ProjectWiki 是一个开源的项目记忆工具。它把 Git 仓库、Word、PDF、Excel、Markdown、实验记录、会议纪要和在线表格整理成一个可追溯、可问答、可交接、可审查的 AI 项目 Wiki。

更有传播性的表达：

```text
Git remembers your code.
ProjectWiki remembers your project.
```

中文表达：

```text
Git 记住代码怎么变。
ProjectWiki 记住项目为什么变。
```

首板不做“企业知识管理平台”，而是做：

```text
小团队项目记忆基础设施。
```

---

## 1. 本次讨论后的关键迭代

### 1.1 首发用户从企业下沉到小团队

原始想法偏“企业项目知识治理”。这条路有价值，但起步慢：企业采购慢、权限复杂、部署复杂、数据源复杂，早期很难快速获得真实用户。

本次迭代后，首板用户改为：

- 个人开发者
- 高校实验室
- 小创业团队
- 外包/咨询小团队
- 开源项目维护者
- 算法/数据科学小组
- 使用 Git 但文档混乱的项目组

产品心智从：

```text
企业知识治理系统
```

改为：

```text
项目开始时就应该初始化的 Project Memory。
```

也就是：

```bash
git init
projectwiki init
```

它要像 Git 一样成为项目启动时的默认工具之一，但它管理的不是代码版本，而是项目知识、需求、决策、交接和文档有效性。

### 1.2 Markdown 不是数据底座，而是输出格式

团队项目文档常见格式是：

- Word / DOCX
- Excel / XLSX
- PDF
- CSV
- 多人在线表格
- Markdown
- Wiki 页面
- Git 仓库里的 README、配置、代码

如果把所有内容粗暴转成 Markdown，会丢失大量结构，例如：

- Word 的标题、批注、修订、表格
- PDF 的页码、图表、版面位置
- Excel 的 sheet、range、公式、表头、行列关系
- 在线表格的版本快照和变更历史
- 代码里的函数、类、接口、依赖关系

因此首板的数据流应该是：

```text
Raw Sources 原始材料
  -> Normalized Source Blocks 归一化内容块
  -> Project Facts 项目事实层
  -> Wiki / Conflicts / Handover / Ask 输出层
```

Markdown 只是最终可读输出，不是内部唯一真相。

### 1.3 AST 和 Wiki 不重合

AST / CST 是代码的语法结构，Wiki 是项目的语义记忆。

关系应该是：

```text
源代码
  -> AST / 静态分析 / tree-sitter
  -> Code Facts
  -> Project Facts
  -> Wiki / Conflicts / Ask / Handover
```

AST 负责发现：

- 有哪些函数、类、模块
- 有哪些 API endpoint
- 有哪些 import 和依赖
- 某个接口是否真的存在
- 某个脚本是否真的存在

Wiki 负责解释：

- 这个模块是做什么的
- 为什么这样设计
- 当前有效需求是什么
- 文档和代码是否冲突
- 新人该从哪里看起
- 哪个实验结果对应当前模型
- 哪些材料已经过期

所以 AST 是输入之一，不是 Wiki 的替代品。

---

## 2. 产品边界

### 2.1 它是什么

ProjectWiki 是：

- 项目记忆工具
- 项目事实层
- 项目交接助手
- AI 维护的项目 Wiki
- 代码-文档一致性检查器
- 项目材料治理层
- 小团队项目启动时的知识基础设施

### 2.2 它不是什么

ProjectWiki 不是：

- 普通 RAG 问答
- 网盘
- 文档库
- Git 平台
- Gitea / GitLab / GitHub 替代品
- 飞书 / Confluence / Notion 替代品
- Obsidian 替代品
- 企业搜索平台
- 纯知识图谱展示工具

### 2.3 核心差异化

普通 RAG 的模式是：

```text
上传文档 -> 检索 -> 问答
```

ProjectWiki 的模式是：

```text
摄入项目材料 -> 抽取事实 -> 判断有效性 -> 发现冲突 -> 生成 Wiki -> 生成交接包 -> 带证据问答
```

重点不是“能聊”，而是“项目知识被整理、审查、追溯和交接”。

---

## 3. 目标用户与场景

### 3.1 个人开发者

痛点：项目时间一长，自己也忘了为什么这样写，README 和真实代码不一致。

价值：自动生成项目 Wiki、架构说明、接口说明、变更记忆。

### 3.2 高校实验室

痛点：学生交接频繁，实验记录、论文、代码、模型、数据集、Excel 表格混在一起。

价值：生成实验/模型/数据的项目记忆和交接包。

### 3.3 小创业团队

痛点：需求快速变化，文档老旧，新成员接手慢。

价值：识别当前有效需求，发现过期文档和代码-文档冲突。

### 3.4 外包/咨询团队

痛点：项目多，交接频繁，客户资料混乱。

价值：快速整理客户项目材料，生成交接说明和风险项。

### 3.5 开源项目维护者

痛点：贡献者不知道从哪里开始，README、docs、代码结构分散。

价值：自动生成 onboarding Wiki、模块说明、贡献者阅读顺序。

---

## 4. 首板产品目标

首板不是传统 MVP，而是 Minimum Lovable Framework：

- 架构完整
- 闭环跑通
- Demo 有冲击力
- README 抓人
- 安装简单
- 每个模块先浅做
- 后续可以持续扩展

首板闭环：

```text
1. 创建项目
2. 摄入本地文件夹 / Git 仓库
3. 解析 Markdown / PDF / DOCX / XLSX / CSV / 代码
4. 生成 Source Blocks
5. 抽取 Project Facts
6. 检测冲突
7. 生成 AI Project Wiki
8. 生成 Handover Pack
9. 支持 Ask with Evidence
10. Web UI 展示结果
```

---

## 5. 总体架构

```text
Sources
  ├── local files
  ├── git repo
  ├── markdown docs
  ├── Word / PDF / Excel / CSV
  ├── code files
  └── future connectors
        ├── GitHub / GitLab / Gitea
        ├── Feishu / Confluence / Notion
        └── online spreadsheets

Connectors
  -> Parsers
  -> Source Blocks
  -> Project Facts
  -> Review / Conflict Detector
  -> Wiki Engine
  -> Handover Engine
  -> Ask with Evidence
  -> Web UI / CLI / Markdown output
```

推荐目录结构：

```text
projectwiki/
├── web/                  # Web UI，首板可以先静态页，后续 Next.js / React
├── server/               # API 层，首板可用 FastAPI
├── workers/              # 异步任务，后续再加
├── connectors/           # 数据源连接器
│   ├── local_files
│   ├── git
│   ├── github
│   ├── gitlab
│   ├── gitea
│   ├── feishu
│   └── confluence
├── parsers/              # 格式解析
│   ├── markdown
│   ├── pdf
│   ├── docx
│   ├── xlsx
│   ├── csv
│   └── code
├── engines/
│   ├── fact_extractor
│   ├── wiki_engine
│   ├── conflict_detector
│   ├── handover_engine
│   └── ask_engine
├── storage/              # SQLite/Postgres + file store
├── cli/                  # projectwiki 命令行
└── docs/
```

本次提供的 starter zip 使用了更轻量的 Python package 结构，便于 Codex 继续演进。

---

## 6. 核心数据模型

### 6.1 Project

```json
{
  "id": "proj_xxx",
  "name": "Demo Project",
  "description": "项目描述",
  "created_at": "...",
  "updated_at": "..."
}
```

### 6.2 Source

表示一个原始来源，可以是文件、Git 文件、在线文档快照、表格快照。

```json
{
  "id": "src_xxx",
  "project_id": "proj_xxx",
  "source_type": "local_file | git | github | feishu | confluence | sheet",
  "path": "docs/需求最终版.docx",
  "title": "需求最终版",
  "content_hash": "sha256",
  "version_hint": "latest/final/v2/unknown",
  "validity_status": "unknown | active | outdated | conflict | archived",
  "metadata": {}
}
```

### 6.3 SourceBlock

统一内容块，是打破格式墙的关键。

```json
{
  "id": "blk_xxx",
  "source_id": "src_xxx",
  "project_id": "proj_xxx",
  "block_type": "markdown_section | pdf_page | docx_paragraph | table_row | code_symbol | code_endpoint",
  "text": "模型 v2 使用 Transformer，在 test set 上 F1=0.83",
  "location": {
    "page": 3,
    "sheet": "实验记录",
    "range": "A12:H12",
    "line": 42
  },
  "metadata": {},
  "content_hash": "sha256"
}
```

### 6.4 ProjectFact

项目事实层是产品核心。

```json
{
  "id": "fact_xxx",
  "project_id": "proj_xxx",
  "fact_type": "requirement | api | code | experiment | deployment | decision | document",
  "statement": "当前代码定义了 POST /api/users/create 接口。",
  "evidence": [
    {
      "source_id": "src_xxx",
      "block_id": "blk_xxx",
      "path": "app.py",
      "location": { "line": 12 }
    }
  ],
  "status": "candidate | confirmed | rejected | outdated | needs_review",
  "confidence": 0.82
}
```

### 6.5 Conflict

```json
{
  "id": "conf_xxx",
  "project_id": "proj_xxx",
  "conflict_type": "endpoint_mismatch | multiple_latest_documents | model_version_mismatch | missing_file",
  "title": "接口路径不一致",
  "description": "文档写 POST /api/user/create，但代码是 POST /api/users/create。",
  "evidence": [],
  "severity": "low | medium | high",
  "status": "open | confirmed | ignored | resolved"
}
```

### 6.6 WikiPage

Markdown 是渲染结果。

```json
{
  "id": "page_xxx",
  "project_id": "proj_xxx",
  "slug": "api",
  "title": "接口信息",
  "content": "# 接口信息...",
  "updated_at": "..."
}
```

---

## 7. 首板功能清单

### 7.1 本次 starter 已包含

随本文档提供的 `projectwiki-codex-starter.zip` 已包含：

- Python package 脚手架
- SQLite 数据库
- CLI：`init-db`、`create`、`list`、`ingest`、`build`、`ask`、`serve`
- FastAPI API
- 静态 Web UI 占位页
- local files connector
- git repo connector 的基础版本
- Markdown parser
- plaintext parser
- CSV parser
- Python/code parser 基础版
- PDF / DOCX / XLSX optional parser
- deterministic fact extractor
- deterministic conflict detector
- wiki generator
- handover generator
- ask with evidence 的基础版本
- Dockerfile
- docker-compose.yml
- AGENTS.md
- Codex 开发任务书
- demo project
- basic pytest

### 7.2 首板必须继续补强

首板继续开发的优先级：

1. Parser 稳定性
2. Fact schema 和 LLM JSON 抽取
3. 冲突检测规则
4. Wiki 页面质量
5. Web UI 工作台
6. Demo 项目和 README 动图
7. Docker 一键运行

### 7.3 后续再补，不要首板过早做

- SSO
- 多租户
- 企业权限
- 审计日志
- 复杂审批流
- 企业销售页面
- 飞书/Confluence 深连接
- GitHub/GitLab/Gitea 全量 webhook
- Neo4j 全局图谱大屏
- 高级向量库集成
- 分布式 Worker
- 商业版 / 企业版拆分

---

## 8. 关键页面设计

### 8.1 Projects

项目列表：

- 项目名称
- 来源数量
- 事实数量
- 冲突数量
- 最近构建时间
- 快速进入 Wiki / Conflicts / Ask

### 8.2 Project Overview

显示：

- 当前项目简介
- 已摄入材料
- 当前 Wiki 页面
- 高优先级冲突
- 推荐下一步

### 8.3 Sources

显示：

- 文件路径
- 来源类型
- hash
- 解析状态
- block 数量
- 版本提示
- 有效性状态

### 8.4 Wiki

页面：

- overview.md
- requirements.md
- architecture.md
- api.md
- experiments.md
- deployment.md
- conflicts.md
- handover.md
- open-questions.md

### 8.5 Conflicts

冲突卡片：

- 标题
- 严重程度
- 冲突类型
- 涉及来源
- 证据指针
- 操作：确认 / 忽略 / 标记已解决

### 8.6 Handover

一键生成项目交接包：

- 项目做什么
- 当前状态
- 最新需求
- 代码入口
- 核心模块
- 当前有效材料
- 过期/冲突材料
- 如何运行
- 如何部署
- 推荐阅读顺序
- 遗留问题

### 8.7 Ask

问答不是普通聊天，而是：

- 结论
- 引用文件
- 引用段落 / 页码 / sheet / range / 代码行
- 是否有冲突
- 置信度
- 需要人工确认的问题

---

## 9. API 设计草案

```text
POST   /api/projects
GET    /api/projects
GET    /api/projects/{project_id}

POST   /api/projects/{project_id}/ingest
POST   /api/projects/{project_id}/build

GET    /api/projects/{project_id}/sources
GET    /api/projects/{project_id}/blocks
GET    /api/projects/{project_id}/facts

GET    /api/projects/{project_id}/wiki
GET    /api/projects/{project_id}/wiki/{slug}

GET    /api/projects/{project_id}/conflicts
PATCH  /api/projects/{project_id}/conflicts/{conflict_id}

GET    /api/projects/{project_id}/handover
POST   /api/projects/{project_id}/ask
```

首板 starter 已实现其中核心接口，后续补 Sources / Blocks / Facts 详情接口和 conflict 状态更新接口。

---

## 10. CLI 设计草案

```bash
projectwiki init-db
projectwiki create "Demo Project"
projectwiki list
projectwiki ingest <project_id> ./docs
projectwiki ingest <project_id> ./repo --source-type git
projectwiki build <project_id>
projectwiki ask <project_id> "这个项目当前最新需求是什么？"
projectwiki serve --port 8080
```

后续可以演进为：

```bash
projectwiki init
projectwiki add ./docs ./experiments.xlsx ./repo
projectwiki build
projectwiki review
projectwiki export wiki
projectwiki handover
```

---

## 11. LLM 使用策略

首板不要一上来让 LLM 承担所有逻辑。推荐分层：

```text
规则解析 / 静态分析 / 表格解析
  -> 候选事实
  -> LLM 结构化抽取与合并
  -> schema 校验
  -> 人工 review
  -> Wiki 渲染
```

### 11.1 Fact extraction prompt 草案

```text
你是项目知识管理员。请从给定 source block 中抽取项目事实。

要求：
1. 只基于给定文本，不要补充外部知识。
2. 每条事实必须保留 evidence pointer。
3. 区分 requirement/api/code/experiment/deployment/decision/document。
4. 不确定的事实标记为 needs_review。
5. 输出 JSON，不要输出 Markdown。
```

### 11.2 Wiki generation prompt 草案

```text
你是 AI Project Wiki 维护者。请基于 project facts 生成 Wiki 页面。

要求：
1. 每个结论必须带证据。
2. 不要掩盖冲突。
3. 如果事实之间矛盾，把它写入待审查项。
4. Markdown 结构清晰，适合新人阅读。
5. 不要覆盖人工编辑区域。
```

### 11.3 Conflict detection prompt 草案

```text
你是项目审查助手。请判断以下 facts 是否存在冲突。

重点关注：
- 当前有效需求冲突
- 接口定义冲突
- 文档与代码不一致
- 模型/实验/部署版本不一致
- 文档提到但代码不存在的文件或脚本

输出 JSON：conflict_type、title、description、severity、evidence。
```

---

## 12. Codex 开发方式

Codex 适合开发这个首板，因为当前已经有：

- 明确产品边界
- 明确模块划分
- 明确首板闭环
- 明确不做什么
- 明确数据模型
- 明确 CLI/API/页面草案
- 可运行的 starter scaffold
- AGENTS.md 和任务书

建议不要一次性让 Codex “把全部做完”。应该拆成小任务：

```text
Task 0: 跑通安装和测试
Task 1: 改进数据模型
Task 2: 强化 parser
Task 3: 加 LLM fact extractor
Task 4: 加强 conflict detector
Task 5: 提升 Wiki 页面质量
Task 6: 做 Web UI 工作台
Task 7: 做 demo project 和 README
```

每个任务结束后运行：

```bash
python -m compileall projectwiki
python -m pytest -q
```

---

## 13. README 第一屏草案

英文：

```text
Your project docs are messy.
Requirements are outdated.
Code and documents disagree.
New teammates don't know where to start.

ProjectWiki turns your codebase and scattered docs into an AI-maintained, evidence-backed project wiki.
```

中文：

```text
项目文档混乱、版本不一、代码和需求对不上、新人接手困难？

ProjectWiki 可以把代码仓库、需求文档、会议纪要、实验记录自动整理成一个可追溯、可问答、可交接的 AI 项目 Wiki。
```

---

## 14. Demo 设计

Demo 项目应故意制造混乱：

```text
demo-project/
├── README.md
├── app.py
├── docs/
│   ├── 需求_最终版.md
│   ├── 需求_latest.md
│   ├── 接口文档_旧版.md
│   └── 部署说明.md
└── experiments/
    └── model_eval.xlsx / model_eval.csv
```

冲突示例：

- 一个文档写 `POST /api/user/create`
- 代码里是 `POST /api/users/create`
- 一个文档说当前模型是 LSTM
- 实验表格说 Transformer v2 效果最好
- 部署文档说线上仍用 model_v1.pkl
- 文档提到 `scripts/start_server.sh`，但仓库里不存在
- 两份文档都声称自己是最新版

Demo 展示顺序：

```text
上传混乱项目
  -> 自动生成 Wiki
  -> 发现冲突
  -> 生成交接包
  -> 问：当前最新需求是什么？
  -> 回答带引用和冲突提示
```

---

## 15. 路线图

### Phase 0：当前 starter

目标：提供 Codex 可继续开发的骨架。

状态：已完成。

### Phase 1：首板可运行闭环

目标：用户可以用 Docker / CLI 跑完 demo。

补强：

- parser 稳定性
- fact schema
- conflict detector
- wiki 页面
- handover 页面
- ask evidence

### Phase 2：首板可展示

目标：GitHub README 有传播力。

补强：

- Web UI 工作台
- Demo GIF
- 示例项目
- README 文案
- 一键命令

### Phase 3：首板可使用

目标：真实用户可以拿自己的项目试用。

补强：

- LLM JSON 抽取
- 事实审查队列
- 人工确认状态
- wiki 更新日志
- 导出到 Markdown repo / Obsidian

### Phase 4：连接器扩展

补强：

- GitHub
- GitLab
- Gitea
- Feishu
- Confluence
- Google Sheets / 在线表格

### Phase 5：团队与企业能力

后补：

- 权限
- 多租户
- SSO
- 审计
- webhook
- worker queue
- 企业部署方案

---

## 16. 设计原则

1. 开源优先，而不是商业化优先。
2. Web / Docker 优先，而不是桌面端优先。
3. 小团队优先，而不是企业采购优先。
4. 事实层优先，而不是 Markdown 优先。
5. 可追溯优先，而不是“AI 说了算”。
6. 冲突显式化，而不是掩盖矛盾。
7. 局部关系视图优先，而不是全局大图谱。
8. 复用 Git / Gitea / 飞书 / Confluence，而不是替代它们。
9. CLI 是开发者入口，Web UI 是团队工作台。
10. 首板做完整骨架，不做企业级深度。

---

## 17. 风险与应对

### 风险 1：变成普通 RAG

应对：始终强调 facts、conflicts、handover、wiki maintenance。

### 风险 2：格式解析复杂度过高

应对：首板用 optional parser + source blocks，中间层先稳定。

### 风险 3：LLM 幻觉

应对：所有输出必须 evidence-backed，不确定就 needs_review。

### 风险 4：Web UI 工程拖慢进度

应对：首板先静态 UI + API，后续再做 React/Next.js。

### 风险 5：开源传播点不够强

应对：Demo 必须展示“文档-代码冲突检测”和“一键交接包”。

---

## 18. 首板验收标准

一个陌生开发者 clone 项目后，可以在 10 分钟内完成：

```bash
docker compose up --build
```

然后：

1. 创建项目。
2. 摄入 demo-project。
3. 点击 build。
4. 看到 Wiki 页面。
5. 看到冲突列表。
6. 看到交接包。
7. 在 Ask 里问问题，并得到带证据回答。

首板成功的标志不是功能多，而是用户看完 Demo 后理解：

```text
这不是又一个文档问答工具。
这是一个帮项目记住上下文、发现冲突、生成交接包的 Project Memory。
```

---

## 19. 下一步最建议做的三件事

1. 用 starter zip 跑通本地 demo。
2. 让 Codex 按 `docs/CODEX_TASKS.md` 逐个任务改。
3. 尽快做 README + Demo GIF，因为开源项目的第一印象非常关键。

