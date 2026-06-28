"""Generate deterministic questions for missing quote fields."""

from __future__ import annotations


class ReviewQuestionGenerator:
    FIELD_LABELS = {
        "counterparty": "交易对手",
        "quote_date": "报价日期",
        "start_date": "起始日",
        "maturity_date": "到期日",
        "notional": "名义本金",
        "currency": "币种",
        "tenor_or_maturity_date": "期限或到期日",
        "underlyings": "挂钩标的",
        "initial_price": "初始价格",
        "initial_price_date": "初始价格确定日",
        "knock_out_barrier": "敲出水平",
        "knock_in_barrier": "敲入水平",
        "coupon_rate": "票息率",
        "observation_frequency": "观察频率",
        "strike_price": "行权价格",
        "coupon_frequency": "票息支付频率",
        "worst_of": "是否为 worst-of 结构",
        "option_type": "期权方向（call/put）",
        "position": "交易方向（buy/sell）",
        "strike": "行权价",
        "expiry_date": "期权到期日",
        "premium": "权利金",
        "margin_ratio": "保证金比例",
        "max_loss": "最大亏损比例",
        "coupon_structure": "票息结构",
    }

    def generate(self, missing_fields: list[str]) -> list[str]:
        return [
            f"请补充{self.FIELD_LABELS.get(field, field)}。"
            for field in missing_fields
        ]
