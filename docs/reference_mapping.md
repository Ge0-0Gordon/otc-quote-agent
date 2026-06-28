# 官方参考材料映射

## 来源

本项目已适配官方材料 `given-data/金融创新业务部衍生品参考资料.docx`：

- “3）标准化衍生品结构要素”结构化为 `reference_materials/standard_derivative_terms.yaml`。
- “4）相关询价案例”中的案例 7–13 结构化为 `reference_materials/inquiry_cases.yaml`。

材料中的案例 1–6 为内嵌图片；本轮按题目要求重点保留可直接读取的案例 7–13。

## 标准要素到项目 Schema

| 官方字段 | 项目字段 | 处理方式 |
|---|---|---|
| 收益结构（结构名称） | `structure_name` / `product_type` | 原文结构名与系统产品枚举分开保存 |
| 挂钩标的 | `underlyings` | 通过 canonical mapper 规范名称和 ticker |
| 名义本金 | `notional` | 万、w/W 等单位统一为基础数值 |
| 交易时间（起始日期） | `trade_date` / `start_date` | 日期统一为 ISO 格式 |
| 期初价格 | `initial_price` | 允许为空 |
| 保证金比例 | `margin_ratio` | JSON 小数、界面百分号 |
| 最大亏损 | `max_loss` | JSON 小数、界面百分号 |
| 敲出/敲入价格 | `knock_out_barrier` / `knock_in_barrier` | 产品 schema 字段 |
| 期限/锁定期 | `tenor` / `lockout_period` | 归一化为 `36M`、`3M` |
| 票息结构 | `coupon_structure` / `coupon_rate` / `annualized_rebate` / `absolute_rebate` | 复杂分段票息保留原文，返息和主票息按标签拆分 |
| 前端/后端年化收益率 | `front_back_annualized_return` | 保留结构化原文 |
| 前端收益率 | `front_return` | JSON 小数、界面百分号 |
| 备注 | `remarks` | 保存规模限制、交易时间和方案选择等信息 |

## 询价案例到 Sample Data

| 官方案例 | Sample Data | 处理状态 |
|---|---|---|
| 案例 9：沪深300限亏雪球 | `sample_data/reference_case_09_limited_loss_snowball.txt` | Snowball，支持 |
| 案例 11：中证1000 DCN | `sample_data/reference_case_11_dcn_unsupported.txt` | Unsupported |
| 案例 12：中证500美式鲨鱼鳍 | `sample_data/reference_case_12_sharkfin_unsupported.txt` | Unsupported |
| 案例 13：两个中证1000雪球方案二选一 | `sample_data/reference_case_13_snowball_two_choices.txt` | Snowball，部分支持 |

样例文件保持官方原文，不补充材料中不存在的信息。

## 当前产品边界

当前完整 schema 支持：

- Snowball
- FCN
- European Option

DCN、凤凰、美式鲨鱼鳍、鲨鱼鳍等结构会识别为 `unsupported`，跳过 Snowball/FCN/European Option schema 和报价字段抽取，仅输出原文摘要、识别原因和扩展建议，避免伪造报价。

## 后续扩展方式

新增产品时沿用当前 deterministic workflow：

1. 从 `standard_derivative_terms.yaml` 选择通用字段并补充产品专属字段。
2. 从 `inquiry_cases.yaml` 建立真实原文 golden cases。
3. 注册新 Pydantic schema 和分类关键词。
4. 增加数值、期限、标的和票息表达的 deterministic normalization。
5. 增加产品级业务校验和人工复核问题。
6. 以字段准确率、缺失字段识别率、unsupported 误判率和证据一致性作为验收指标。
