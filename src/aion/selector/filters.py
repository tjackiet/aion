"""記事選定ロジック（日付フィルタ・AIキーワードフィルタ）"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aion.models import Article
from aion.selector.keywords import AI_KEYWORDS

JST = ZoneInfo("Asia/Tokyo")


def count_undated_by_source(articles: list[Article]) -> dict[str, int]:
    """公開日時をパースできなかった記事数を情報源ごとに集計

    日付フィルタはこれらを黙って除外するため、件数を可視化する。
    """
    counts: dict[str, int] = {}
    for article in articles:
        if article.published is None:
            counts[article.source] = counts.get(article.source, 0) + 1
    return counts


def filter_recent_articles(articles: list[Article], days: int = 1) -> list[Article]:
    """直近N日間の記事をフィルタリング"""
    cutoff = datetime.now(JST) - timedelta(days=days)
    return [a for a in articles if a.published and a.published >= cutoff]


def matched_ai_keywords(article: Article) -> list[str]:
    """記事のタイトル・概要中でマッチしたAIキーワード一覧を返す（空ならAI関連ではない）"""
    title = article.title.upper()
    summary = (article.summary or "").upper()
    text = title + " " + summary
    return [kw for kw in AI_KEYWORDS if kw.upper() in text]


def filter_ai_related(articles: list[Article]) -> list[Article]:
    """AI関連の記事のみをフィルタリング（タイトルベース）"""
    return [a for a in articles if matched_ai_keywords(a)]
