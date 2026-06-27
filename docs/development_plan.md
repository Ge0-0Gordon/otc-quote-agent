# OTC 报价结构化智能体：第一版收敛开发计划

## 1. 第一版最终范围

第一版直接交付完整、可演示项目，不再拆分 P0/P1。

- 支持 Snowball、FCN、European Option。
- 支持文本粘贴及 `txt、md、docx、xlsx、文本型 pdf`。
- DOCX/XLSX/PDF 仅提取文本；扫描 PDF 明确报错。
- 使用确定性工作流结合 LLM 结构化抽取。
- 实现 OpenAI-compatible 和 Ollama 两种客户端。
- DeepSeek、Kimi、vLLM 通过 OpenAI-compatible 配置接入。
- 提供 Streamlit、CLI 和 Docker Compose。
- 提供三份中英文样例，故意保留部分缺失字段。
- 每次成功运行生成：
  - `extracted_quote.json`
  - `quote_table.csv`
  - `report.html`
- 提供 pytest 测试、README 和 `.env.example`。

第一版完成标准是四条指定命令均可运行，而不是仅完成架构骨架。

## 2. 明确不做项

- 不实现定价、希腊值、行情、回测、对冲和结算。
- 不实现交易生命周期、邮件收发、审批和数据库。
- 不使用 ReAct 或多 Agent 自主规划。
- 不实现 OCR、复杂表格重建、版面分析和页码级证据定位。
- 不为 DeepSeek、Kimi、vLLM 分别编写客户端。
- FakeLLM 仅用于 pytest，不暴露为业务 provider 或演示模式。
- DCN、凤凰、经典结构仅识别为 `unknown` 或 `unsupported`。
- 不引入复杂判别联合、插件框架、任务队列和异步处理。

## 3. 调整后的系统架构

```text
Streamlit ─┐
           ├─ QuoteExtractionService.run()
CLI ───────┘
               │
               ├─ DocumentParser
               ├─ ProductClassifier
               ├─ SchemaSelector
               ├─ LLMExtractor
               ├─ Normalizer
               ├─ RuleValidator
               ├─ ReviewQuestionGenerator
               └─ Exporter
```

### 核心组件

- `DocumentParser`
  - 按扩展名路由解析器。
  - TXT/MD 直接解码。
  - DOCX 提取段落和简单表格文本。
  - XLSX 按工作表和行提取可见单元格。
  - PDF 提取文本；提取结果为空时报告“疑似扫描件，不支持 OCR”。

- `ProductClassifier`
  - 先用中英文关键词规则识别三类产品。
  - 规则无法确定或关键词冲突时，由 LLM 辅助分类。
  - DCN、凤凰、经典及其他产品返回 `unknown` 或 `unsupported`。

- `SchemaSelector`
  - 使用简单字典将产品类型映射到对应 Pydantic 模型。
  - 不建立复杂插件或动态加载机制。
  - `unknown` 或 `unsupported` 产品不套用 Snowball、FCN、European Option schema。
  - 不为不支持产品生成或补齐任何伪造报价字段。
  - 不支持产品可以生成独立报告，内容仅包括支持状态、原文摘要、识别原因及后续扩展建议。

- `LLMExtractor`
  - 根据目标 schema 生成严格抽取提示。
  - 缺失字段输出 `null`，不得推测。
  - 非法 JSON 或 schema 无法解析时最多重试一次，之后显式失败。
  - `unknown` 或 `unsupported` 产品不会进入产品报价字段抽取流程。

- `Normalizer`
  - 统一金额、币种、百分比、期限、日期及常用标的名称。
  - JSON 中百分比保存为小数。
  - Streamlit、CSV 展示列和 HTML 中格式化为 `103%`、`15%`。

- `RuleValidator`
  - 输出 `missing_fields` 及结构化 `ValidationIssue`。
  - 错误、警告与缺失字段分开处理。
  - nullable 字段不会阻止 Pydantic 模型创建。

- `ReviewQuestionGenerator`
  - 按缺失字段使用固定模板生成补录问题，不额外调用 LLM。

- `Exporter`
  - JSON 保留完整嵌套结构。
  - CSV 输出一行扁平报价，列表和复杂对象序列化为 JSON 字符串。
  - HTML 显示条款表、百分比格式、证据、缺失项、错误、警告和复核问题。
  - 对 `unknown` 或 `unsupported` 产品，仅导出不支持报告，不生成伪造的产品报价表。

### Schema 范围

只保留以下模型：

- `BaseQuote`
- `Underlying`
- `EvidenceItem`
- `ValidationIssue`
- `SnowballQuote`
- `FCNQuote`
- `EuropeanOptionQuote`
- `ExtractionResult`

实现原则：

- 产品 schema 继承 `BaseQuote`。
- `product_type` 使用普通枚举或 Literal 约束。
- SchemaSelector 直接选择具体模型，不依赖复杂 discriminated union。
- 抽取字段均可 nullable。
- `underlyings` 统一为列表；Snowball 和 European Option 校验为单标的。
- `ValidationIssue` 至少包含 `field、severity、code、message`。
- `ExtractionResult` 包含报价、复核问题及必要处理元数据。
- 不支持产品的 `ExtractionResult` 不包含产品报价对象，只记录状态、分类依据和报告信息。

### Provider 接口

```text
LLMClient.extract(prompt, schema) -> dict
```

仅实现：

- `OpenAICompatibleClient`
- `OllamaClient`

环境变量：

- `LLM_PROVIDER=openai|ollama`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`

运行约束：

- pytest 默认注入 FakeLLM，不需要 API key、不访问外网，也不要求 Ollama。
- CLI 和 Streamlit 执行真实抽取时，必须在 `.env` 中配置可用的 OpenAI-compatible 或 Ollama provider。
- DeepSeek、Kimi、vLLM 通过 OpenAI-compatible 的 base URL、模型名及密钥配置接入。
- provider 不可达、缺少配置、请求超时或结果不合法时，Streamlit 和 CLI 必须显示实际错误并返回失败状态，不生成伪造报价文件。

## 4. 调整后的目录结构

```text
otc-quote-agent/
├─ README.md
├─ pyproject.toml
├─ requirements.txt
├─ .env.example
├─ .gitignore
├─ Dockerfile
├─ docker-compose.yml
├─ app.py
├─ cli.py
├─ docs/
│  └─ development_plan.md
├─ src/
│  └─ otc_quote_agent/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ service.py
│     ├─ schemas/
│     │  ├─ common.py
│     │  ├─ products.py
│     │  └─ output.py
│     ├─ parsers/
│     │  ├─ base.py
│     │  └─ document_parser.py
│     ├─ llm/
│     │  ├─ base.py
│     │  ├─ openai_compatible.py
│     │  ├─ ollama.py
│     │  └─ prompts.py
│     ├─ agents/
│     │  ├─ classifier.py
│     │  ├─ extractor.py
│     │  └─ reviewer.py
│     ├─ normalizers/
│     │  └─ quote_normalizer.py
│     ├─ validators/
│     │  └─ quote_validator.py
│     └─ exporters/
│        ├─ json_exporter.py
│        ├─ csv_exporter.py
│        └─ html_exporter.py
├─ sample_data/
│  ├─ snowball_inquiry_zh.txt
│  ├─ fcn_quote_zh.txt
│  └─ european_option_email_en.txt
├─ tests/
│  ├─ conftest.py
│  ├─ fakes.py
│  ├─ test_parsers.py
│  ├─ test_classifier.py
│  ├─ test_normalizers.py
│  ├─ test_validators.py
│  ├─ test_exporters.py
│  └─ test_service_smoke.py
└─ outputs/
   └─ .gitkeep
```

同类简单逻辑合并到较少模块中，避免为每个字段或规则建立独立文件。

## 5. 调整后的实现顺序

1. **建立项目与数据契约**
   - 创建目录、配置、schema、依赖和样例。
   - 确认三种不完整报价都能实例化及序列化。

2. **完成全部文件解析**
   - 实现 TXT、MD、DOCX、XLSX、文本 PDF。
   - 为每种格式准备最小测试 fixture。
   - 明确区分不支持格式、损坏文件和扫描 PDF。
   - 扫描件测试使用“提取文本为空的 PDF”模拟，不构造复杂扫描文件。

3. **实现分类、标准化和校验**
   - 完成三产品关键词分类及 unsupported 处理。
   - 完成金额、日期、期限、百分比、标的映射。
   - 落实题目指定的全部通用和产品规则。

4. **实现 LLM 层**
   - 建立统一接口。
   - 完成 OpenAI-compatible、Ollama 及结构化 prompt。
   - 对非法响应执行一次格式重试，其余错误直接抛出。

5. **串联 QuoteExtractionService**
   - 固定执行顺序和阶段错误类型。
   - 使用 FakeLLM 完成三个样例的离线 service smoke test。
   - unsupported/unknown 分支跳过 schema 和报价抽取，只构造不支持报告。

6. **完成导出**
   - 同一次服务结果生成 JSON、CSV、HTML。
   - Streamlit 及 HTML 统一使用百分比展示函数。

7. **完成 CLI 和 Streamlit**
   - CLI 负责输入文件、输出目录、退出码和简洁摘要。
   - Streamlit 提供上传/粘贴、provider 展示、执行、结果页和下载按钮。
   - 两者只调用 QuoteExtractionService，不复制业务逻辑。

8. **完成 Docker 与 README**
   - Docker 默认运行 Streamlit。
   - Compose 通过环境变量连接 API、Ollama 或 vLLM endpoint。
   - README 记录安装、配置、运行、演示、限制和测试方式。

9. **最终验收**
   - 跑完整 pytest。
   - 分别验证 CLI、Streamlit 和 Docker。
   - 检查输出文件内容一致、无密钥、无缓存和大文件。

## 6. 测试与验收命令

pytest 默认完全离线，不访问真实 API，也不要求 Ollama。

测试覆盖：

- Parser：五种格式、空文件、损坏文件，以及以“提取文本为空的 PDF”模拟扫描件。
- Classifier：三产品、中英文表达、unknown、unsupported。
- Normalizer：中英文金额、比例、期限、日期和标的映射。
- Validator：题目规定的所有通用及产品规则。
- Exporter：JSON 可读取、CSV 字段稳定、HTML 百分比显示正确。
- Service smoke：使用 FakeLLM 跑通三份样例并生成三种文件。
- Failure path：provider 失败、非法 JSON 和 unsupported 产品不得伪造输出。

验收命令：

```powershell
python -m pytest
python cli.py --input sample_data/snowball_inquiry_zh.txt --output outputs/sample_snowball
streamlit run app.py
docker compose up --build
```

CLI 真实抽取前必须在 `.env` 配置可用的 OpenAI-compatible 或 Ollama provider。成功后必须存在：

```text
outputs/sample_snowball/extracted_quote.json
outputs/sample_snowball/quote_table.csv
outputs/sample_snowball/report.html
```

Streamlit 与 Docker 使用真实配置的 provider 完成演示；pytest 使用 FakeLLM 验证业务链路。

## 7. 风险点与对应处理

- **LLM 输出不稳定**
  - 使用低温度、明确 JSON Schema、nullable 字段和一次格式重试。
  - 重试后仍失败则显式报错。

- **不同 provider 结构化输出能力不同**
  - 统一要求返回 JSON；客户端适配请求格式，Pydantic 负责最终校验。

- **文档解析质量有限**
  - 第一版只保证文本提取，不承诺版面还原。
  - 空 PDF 提示扫描件不受支持。

- **客户目标与正式报价混淆**
  - Prompt 要求区分语气；必要时保留数值并生成“目标值而非确定报价”警告。

- **nullable 字段与业务必填冲突**
  - Schema 允许缺失，RuleValidator 集中管理业务完整性。

- **百分比内部值和界面显示不一致**
  - 统一内部小数表示，所有展示和导出表格调用同一格式化函数。

- **unsupported 产品误套 schema**
  - SchemaSelector 在 unknown/unsupported 时停止产品抽取。
  - 报告只说明不支持状态、原文摘要、识别原因及扩展建议。

- **CLI 失败后留下半成品**
  - 先完成全部处理，再写入目标文件；失败时返回非零退出码。

- **Docker 无法访问宿主机 Ollama**
  - README 及 Compose 提供可配置 base URL，并说明 `host.docker.internal` 用法。

## 8. Plan 落文件并开始开发

1. 在当前工作区新建 `otc-quote-agent/`，不修改现有 `given-data/`。
2. 将本计划保存为 `otc-quote-agent/docs/development_plan.md`。
3. 创建 `.gitignore`，排除 `.env`、缓存、运行输出和本地环境。
4. 创建 README 初版，说明项目定位及正式计划位置。
5. 在 `otc-quote-agent/` 内初始化 Git，并提交第一版基线。
6. 后续按“Schema → Parser → Deterministic Core → LLM → Service → Exporter → CLI/UI → Docker/README”的顺序开发。
7. 每完成一个阶段立即运行对应 pytest；不积累到最后统一修复。
8. 最终运行四条验收命令，并在 README 记录真实测试结果、provider 配置和已知限制。
