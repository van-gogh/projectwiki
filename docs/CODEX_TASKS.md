# Codex 首板开发任务书

这份任务书用于把当前 starter 扩展成一个更有传播力的首板。

## 总目标

跑通完整闭环：

```text
创建项目 -> 摄入本地文档和代码 -> 解析为 blocks -> 抽取 facts -> 检测 conflicts -> 生成 Wiki 和 handover -> 支持 ask with evidence -> Web UI 展示
```

## Task 0：确认脚手架可运行

目标：保证当前项目可以安装、编译、启动。

执行：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m compileall projectwiki
python -m pytest -q
projectwiki init-db
projectwiki create "Demo Project"
```

验收：命令无错误。

## Task 1：强化数据模型与 schema

目标：让 Project / Source / Block / Fact / Conflict / WikiPage 的字段更稳定。

要求：

- 增加 `status`、`version_hint`、`validity_status` 等字段，但不要过度企业化。
- 为每个用户可见结论保留 evidence pointer。
- 补充 schema migration 机制，第一版可以是简单版本号表。

验收：旧数据不丢，新字段可查询。

## Task 2：改进 parser

目标：让 Word / PDF / Excel / Markdown / code 解析更可用。

要求：

- Markdown 按标题分块。
- PDF 保留 page。
- DOCX 保留 paragraph/table。
- XLSX 保留 sheet/row/range。
- Code 至少支持 Python AST；后续加 tree-sitter。

验收：每个 block 都有 source_id、path、location、text、hash。

## Task 3：Project Fact 抽取

目标：把 blocks 抽成可审查事实，而不是直接写死 Markdown。

要求：

- 支持 requirement/api/code/experiment/deployment/decision/document 分类。
- 增加 LLM extractor，但必须可关闭。
- LLM 输出必须是 JSON，并通过 schema 校验。
- 低置信度事实标记为 `needs_review`。

验收：`projectwiki build` 后 facts 数量合理，且每条 fact 有 evidence。

## Task 4：冲突检测

目标：做出能让 README 动图抓人的冲突检测。

优先规则：

- 多份文档都声称自己是最新版。
- 代码接口和文档接口不一致。
- 文档提到的脚本不存在。
- 实验记录中的模型版本和部署文档不一致。
- LSTM / Transformer 等模型架构描述不一致。

验收：示例项目能稳定生成 2-4 条冲突。

## Task 5：Wiki Generator

目标：生成结构清晰的 Markdown Wiki。

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

要求：

- 每个结论有证据。
- 不确定的内容不要假装确定。
- 人工编辑和 AI 生成区域分离，后续避免覆盖。

验收：Wiki 可直接放进 Obsidian 或 Git repo。

## Task 6：Web UI

目标：从静态占位页升级为轻量工作台。

页面：

- Projects
- Project Overview
- Sources
- Wiki
- Conflicts
- Handover
- Ask
- Settings

验收：不用命令行也能完成首板闭环。

## Task 7：示例项目和 README 传播

目标：让 GitHub 访客 30 秒内理解产品。

要求：

- 构造一个混乱示例项目。
- 包含 README、旧需求、新需求、API 文档、代码、实验表格、部署文档。
- Demo 能显示：生成 Wiki、发现冲突、生成交接包、带证据问答。
- README 第一屏突出：不是 RAG，不是文档库，而是 Project Memory。

验收：README 有一条可复制命令跑完整 Demo。
