"""記事選定のオーケストレーション"""

from aion.collector import fetch_all_feeds
from aion.models import Article
from aion.selector.filters import (
    count_undated_by_source,
    filter_ai_related,
    filter_recent_articles,
    matched_ai_keywords,
)

REASON_NO_DATE = "日付なし"
REASON_NO_AI_KEYWORD = "AIキーワード不一致"


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

    if ai_filter:
        filtered = filter_ai_related(filtered)
        print(f"AI関連記事: {len(filtered)} 件")

    return filtered


def explain_selection(days: int = 1) -> list[Article]:
    """全記事に通過/除外理由とマッチキーワードを付与して返す（--explain 用）

    collect() が使うフィルタ関数をそのまま再利用し、除外された記事も
    破棄せず matched_keywords / excluded_reason を付けて返す。
    """
    articles = fetch_all_feeds()
    recent_ids = {id(a) for a in filter_recent_articles(articles, days=days)}

    for article in articles:
        article.matched_keywords = matched_ai_keywords(article)

        if article.published is None:
            article.excluded_reason = REASON_NO_DATE
        elif id(article) not in recent_ids:
            article.excluded_reason = f"直近{days}日外"
        elif not article.matched_keywords:
            article.excluded_reason = REASON_NO_AI_KEYWORD
        else:
            article.excluded_reason = None

    return articles
