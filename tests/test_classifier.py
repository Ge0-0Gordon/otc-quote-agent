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
