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
python -m compileall whywiki
python -m pytest -q
whywiki init-db
whywiki create "My Project"
```

验收：命令无错误。

## Task 0.5：产品化启动入口

目标：让 WhyWiki 像现代 CLI 产品一样从一行命令进入 Web 工作台，而不是要求用户先 clone 仓库。

目标入口：

```bash
npm install -g whywiki
whywiki
```

要求：

- `whywiki` 静默启动本地 Web 服务，并输出可点击链接。
- 如果 WhyWiki 已占用默认端口，输出当前端口、进程和启动信息，并让用户选择继续使用或重启 WhyWiki。
- 如果其它进程占用默认端口，输出占用进程信息，并让用户选择杀掉占用进程后启动或取消启动。
- 默认使用 `127.0.0.1:8765`，不自动 fallback 到随机端口。
- 数据目录默认放在 `~/.whywiki`。
- 增加 `whywiki log` 查看本次或最近一次启动日志。
- 保留 `whywiki status`、`open`、`stop`、`doctor` 的扩展空间。

验收：用户不需要 clone 仓库、不需要理解 Python/Docker，也能打开可用 Web 界面；启动失败时能通过 `whywiki log` 定位原因。

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

验收：`whywiki build` 后 facts 数量合理，且每条 fact 有 evidence。

## Task 4：冲突检测

目标：做出能让 README 动图抓人的冲突检测。

优先规则：

- 多份文档都声称自己是最新版。
- 代码接口和文档接口不一致。
- 文档提到的脚本不存在。
- 实验记录中的模型版本和部署文档不一致。
- LSTM / Transformer 等模型架构描述不一致。

验收：测试夹具和真实项目材料都能稳定生成可解释冲突。

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

设计方向：参考 `npx getdesign@latest add airtable` 的 Airtable/Equals 风格，做成仪表板式本地工作台，而不是说明页或 landing page。

页面：

- 项目首页：展示已有项目和创建项目入口。
- 项目工作台：进入具体项目后再显示项目内导航。
- 需求现状。
- 原始文件。
- 需求冲突点。
- 需求问答。
- 设置。

验收：执行 `whywiki` 后进入 Web UI，不用命令行也能完成首板闭环；启动或摄入失败时，界面应提示用户可运行 `whywiki log` 查看日志。

## Task 7：真实项目入口和 README 传播

目标：让 GitHub 访客 30 秒内理解产品。

要求：

- 首页默认展示已有项目；没有项目时引导用户创建项目。
- 创建项目后引导用户摄入真实本地文件夹。
- 测试夹具可以保留混乱材料，但不能作为产品内置 Demo 入口。
- 产品路径能显示：生成 Wiki、发现冲突、生成交接包、带证据问答。
- README 第一屏突出：不是 RAG，不是文档库，而是 Project Memory。

验收：README 有一条可复制命令启动本地产品，并说明如何用自己的项目完成闭环。
