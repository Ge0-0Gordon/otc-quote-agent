# OTC Derivatives Quote Structuring Agent

场外衍生品报价结构化智能体：将客户询价、销售邮件及机构报价文档转换为标准化、可校验、可导出的报价数据。

第一版聚焦 Snowball、FCN 和 European Vanilla Option，采用确定性工作流结合 LLM 结构化抽取，并提供 Streamlit、CLI、Docker、JSON/CSV/HTML 导出能力。

正式开发计划见 [docs/development_plan.md](docs/development_plan.md)。

## 功能范围

- 输入：文本粘贴、TXT、Markdown、DOCX、XLSX、文本型 PDF。
- 产品：Snowball、FCN、European Vanilla Option。
- 处理：规则优先分类、Schema 选择、LLM 抽取、字段标准化、业务校验和复核问题生成。
- 输出：标准 JSON、单行 CSV 报价表和自包含 HTML 报告。
- Provider：OpenAI-compatible 和 Ollama。
- 交互：Streamlit 和 CLI 共用同一个 `QuoteExtractionService`。

DCN、凤凰、经典结构及无法识别的产品不会套用受支持产品的 Schema，也不会生成伪造报价字段。系统只输出不支持状态、原文摘要、识别原因和扩展建议。

本项目不包含定价模型、希腊值、行情、对冲、结算或交易生命周期。

## 工作流

```text
DocumentParser
  → ProductClassifier
  → SchemaSelector
  → LLMExtractor
  → Normalizer
  → RuleValidator
  → ReviewQuestionGenerator
  → Exporter
```

业务字段允许为空。Pydantic 负责类型和结构，Validator 负责记录 `missing_fields`、`validation_errors` 和 `warnings`。

## 本地安装

建议使用 Python 3.11 或更高版本。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` 含真实 provider 配置，不应提交到 Git。

## Provider 配置

### OpenAI-compatible

OpenAI、DeepSeek、Kimi 和 vLLM 使用同一个客户端，只需配置对应 endpoint、模型和密钥：

```dotenv
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=replace-me
LLM_MODEL=gpt-4.1-mini
LLM_TIMEOUT_SECONDS=60
```

对于不要求密钥的私有 vLLM endpoint，`LLM_API_KEY` 可以留空。

### Ollama

先在本机启动 Ollama 并准备支持 JSON 输出的模型：

```dotenv
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_API_KEY=
LLM_MODEL=qwen2.5:7b
LLM_TIMEOUT_SECONDS=60
```

Docker 容器访问宿主机 Ollama 时，通常将地址改为：

```dotenv
LLM_BASE_URL=http://host.docker.internal:11434
```

Provider 缺少配置、不可达、超时或返回非法 JSON 时，程序会显式失败，不会返回伪造结果。

## CLI

CLI 执行真实抽取，需要先完成 `.env` 配置：

```powershell
python cli.py --input sample_data/snowball_inquiry_zh.txt --output outputs/sample_snowball
```

成功后生成：

```text
outputs/sample_snowball/
├─ extracted_quote.json
├─ quote_table.csv
└─ report.html
```

写入发生在抽取、标准化和校验全部成功之后，并使用临时文件替换目标文件。

## Streamlit

```powershell
streamlit run app.py
```

页面支持文本粘贴、文件上传、报价表格、规范 JSON、质量报告以及三个下载按钮。JSON 中百分比使用小数，例如 `1.03`；页面和 HTML 报告显示为 `103%`。

## Docker

Docker Compose 自动读取项目根目录的 `.env`：

```powershell
docker compose up --build
```

打开 `http://localhost:8501`。即使尚未配置模型，界面也能启动并明确显示配置问题；真实抽取仍要求可用 provider。

## 测试

```powershell
python -m pytest
```

pytest 使用 `FakeLLM` 完成服务 smoke test，不读取 API key、不访问外网、不要求本机安装 Ollama。FakeLLM 仅存在于 `tests/`，不是业务演示模式。

测试覆盖：

- 五类文档解析及空文本 PDF 的扫描件提示。
- 三类产品和 unsupported/unknown 分类。
- 金额、比例、期限、日期、频率和标的标准化。
- 通用及产品级校验规则。
- 两类 provider 的响应适配。
- JSON/CSV/HTML 导出。
- 三份样例的离线服务 smoke test。

## 样例

- `sample_data/snowball_inquiry_zh.txt`
- `sample_data/fcn_quote_zh.txt`
- `sample_data/european_option_email_en.txt`

样例故意缺少部分字段，用于展示缺失字段、警告和人工复核问题。

## 数据约定

- JSON 百分比：小数形式，如 `103% → 1.03`。
- 展示百分比：Streamlit、CSV 和 HTML 使用百分号格式。
- 日期：ISO `YYYY-MM-DD`。
- 期限：`12M`、`3M`、`1Y`。
- 单标的和多标的统一使用 `underlyings` 列表。
- 原文和字段证据随结果保留，便于人工复核。

## 已知限制

- PDF 仅支持可提取文本的文件；提取结果为空时按疑似扫描件处理，不执行 OCR。
- DOCX、XLSX、PDF 仅做简单文本提取，不重建复杂表格或版面。
- 不支持页码级证据定位。
- LLM 抽取质量取决于模型能力，业务使用前必须人工复核错误、警告和缺失字段。
- 当前不持久化报价，也不提供身份认证、审批或审计数据库。
