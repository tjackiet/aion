"""AI関連キーワード定義（記事選定のキーワードフィルタ用）

キーワード本体は config/keywords.yaml で管理する。
"""

from pathlib import Path

import yaml


def load_ai_keyword_groups(config_path: Path | None = None) -> dict[str, list[str]]:
    """AIキーワードをYAMLのカテゴリ構造を保ったまま読み込む

    マッチング（filters）はカテゴリを区別しないが、スコアリング（scoring）は
    カテゴリごとの重みを引くためにこの構造を使う。
    """
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "keywords.yaml"

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return {category: list(keywords) for category, keywords in data["ai_keywords"].items()}


def load_ai_keywords(config_path: Path | None = None) -> list[str]:
    """AIキーワードをYAMLから読み込み、カテゴリを平坦化したリストで返す"""
    keywords: list[str] = []
    for category_keywords in load_ai_keyword_groups(config_path).values():
        keywords.extend(category_keywords)
    return keywords


AI_KEYWORD_GROUPS = load_ai_keyword_groups()
AI_KEYWORDS = [kw for group in AI_KEYWORD_GROUPS.values() for kw in group]
