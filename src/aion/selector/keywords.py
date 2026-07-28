"""AI関連キーワード定義（記事選定のキーワードフィルタ用）

キーワード本体は config/keywords.yaml で管理する。
"""

from pathlib import Path

import yaml


def load_ai_keywords(config_path: Path | None = None) -> list[str]:
    """AIキーワードをYAMLから読み込み、カテゴリを平坦化したリストで返す"""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "keywords.yaml"

    with open(config_path) as f:
        data = yaml.safe_load(f)

    keywords: list[str] = []
    for category_keywords in data["ai_keywords"].values():
        keywords.extend(category_keywords)
    return keywords


AI_KEYWORDS = load_ai_keywords()
