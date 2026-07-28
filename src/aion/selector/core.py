"""記事選定のオーケストレーション"""

from pathlib import Path

from aion.collector import fetch_all_feeds, load_feeds_config
from aion.models import Article
from aion.selector.filters import (
    count_undated_by_source,
    filter_ai_related,
    filter_recent_articles,
    matched_ai_keywords,
)
from aion.selector.ranking import rank_articles
from aion.selector.scoring import score_articles

REASON_NO_DATE = "日付なし"
REASON_NO_AI_KEYWORD = "AIキーワード不一致"


def keyword_filter_exempt_sources(config_path: Path | None = None) -> frozenset[str]:
    """AIキーワードフィルタを適用しない情報源名の集合を feeds.yaml から得る

    feeds.yaml の ai_filter: false が付いたフィードが対象。
    """
    config = load_feeds_config(config_path)
    return frozenset(feed.name for feed in config.feeds if not feed.ai_filter)


def collect(days: int = 1, ai_filter: bool = True) -> list[Article]:
    """メイン収集関数: フィード取得 + フィルタリング"""
    print("RSSフィードを取得中...")
    articles = fetch_all_feeds()
    print(f"合計 {len(articles)} 件の記事を取得")

    undated = count_undated_by_source(articles)
    if undated:
        detail = ", ".join(f"{source} {count}件" for source, count in undated.items())
        print(f"⚠ 公開日時を取得できず除外: {sum(undated.values())} 件（{detail}）")

    filtered = filter_recent_articles(articles, days=days)
    print(f"直近{days}日間の記事: {len(filtered)} 件")

    exempt = keyword_filter_exempt_sources()

    if ai_filter:
        filtered = filter_ai_related(filtered, exempt_sources=exempt)
        detail = f"（{', '.join(sorted(exempt))} はキーワードフィルタ免除）" if exempt else ""
        print(f"AI関連記事: {len(filtered)} 件{detail}")

    score_articles(filtered, exempt_sources=exempt)
    return rank_articles(filtered)


def explain_selection(days: int = 1) -> list[Article]:
    """全記事に通過/除外理由とマッチキーワードを付与して返す（--explain 用）

    collect() が使うフィルタ関数をそのまま再利用し、除外された記事も
    破棄せず matched_keywords / excluded_reason を付けて返す。
    """
    articles = fetch_all_feeds()
    recent_ids = {id(a) for a in filter_recent_articles(articles, days=days)}
    exempt = keyword_filter_exempt_sources()
    score_articles(articles, exempt_sources=exempt)

    for article in articles:
        article.matched_keywords = matched_ai_keywords(article)

        if article.published is None:
            article.excluded_reason = REASON_NO_DATE
        elif id(article) not in recent_ids:
            article.excluded_reason = f"直近{days}日外"
        elif not article.matched_keywords and article.source not in exempt:
            article.excluded_reason = REASON_NO_AI_KEYWORD
        else:
            article.excluded_reason = None

    return articles
