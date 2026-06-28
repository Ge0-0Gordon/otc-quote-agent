import pytest

from otc_quote_agent.agents import ProductClassifier
from otc_quote_agent.schemas import ProductType


def test_classifies_supported_products() -> None:
    classifier = ProductClassifier()

    assert classifier.classify("中证1000雪球，敲出103%").product_type is ProductType.SNOWBALL
    assert classifier.classify("USD FCN worst-of quote").product_type is ProductType.FCN
    assert (
        classifier.classify("EURUSD European call").product_type
        is ProductType.EUROPEAN_OPTION
    )


def test_classifies_known_unsupported_product() -> None:
    result = ProductClassifier().classify("请报价一笔凤凰结构")

    assert result.product_type is ProductType.UNSUPPORTED
    assert "Phoenix" in result.reason


def test_unknown_text_stays_unknown_without_llm() -> None:
    result = ProductClassifier().classify("Please provide terms.")

    assert result.product_type is ProductType.UNKNOWN


def test_official_reference_product_keywords() -> None:
    classifier = ProductClassifier()

    assert (
        classifier.classify("沪深300限亏雪球，敲入70%，敲出100%").product_type
        is ProductType.SNOWBALL
    )
    assert (
        classifier.classify("欧式早利：中证1000，36锁3").product_type
        is ProductType.SNOWBALL
    )
    assert (
        classifier.classify("买入欧式看涨期权，strike 100").product_type
        is ProductType.EUROPEAN_OPTION
    )
    assert (
        classifier.classify(
            "中证1000 2年 锁3 65-96 递减0.75%，另一方案递减1%，二选一"
        ).product_type
        is ProductType.SNOWBALL
    )


@pytest.mark.parametrize(
    "text",
    [
        "ZZ1000，DCN，最后一个月敲出降至68%",
        "中证500美式鲨鱼鳍，询绝对期权费率",
    ],
)
def test_official_unsupported_products_take_precedence(text: str) -> None:
    result = ProductClassifier().classify(text)

    assert result.product_type is ProductType.UNSUPPORTED
