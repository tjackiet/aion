"""記事選定ロジック（日付フィルタ・AIキーワードフィルタ）"""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aion.models import Article
from aion.selector.keywords import AI_KEYWORDS

JST = ZoneInfo("Asia/Tokyo")


def _compile_keyword_pattern(keyword: str) -> re.Pattern[str]:
    """キーワードの前後境界を考慮した正規表現にコンパイル

    素朴な部分一致では 'AI' が 'TRAINING' の中の文字列として誤爆する。
    通常の正規表現の \\b は日本語文字も「単語文字」とみなすため、
    単純に \\b で挟むと '生成AI' や 'AIエージェント' のような実際のマッチも
    取りこぼしてしまう。

    そこで、キーワード自身の端の文字がASCII英数字の場合にのみ
    「直前/直後がASCII英数字でないこと」を要求する。キーワードの端がCJK文字
    （日本語）の場合は境界条件を課さない。日本語は英語と違って単語間にスペースを
    置かないのが通常であり、'マルチモーダルLLM' のような表記でも
    'マルチモーダル' 単体として正しくマッチさせたいため。
    """
    prefix = r"(?<![A-Za-z0-9])" if keyword[0].isascii() and keyword[0].isalnum() else ""
    suffix = r"(?![A-Za-z0-9])" if keyword[-1].isascii() and keyword[-1].isalnum() else ""
    return re.compile(prefix + re.escape(keyword) + suffix, re.IGNORECASE)


_KEYWORD_PATTERNS = [(kw, _compile_keyword_pattern(kw)) for kw in AI_KEYWORDS]


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
    text = article.title + " " + (article.summary or "")
    return [kw for kw, pattern in _KEYWORD_PATTERNS if pattern.search(text)]


def filter_ai_related(
    articles: list[Article],
    exempt_sources: frozenset[str] = frozenset(),
) -> list[Article]:
    """AI関連の記事のみをフィルタリング（タイトルベース）

    exempt_sources に名前が含まれる情報源はキーワードフィルタを適用せず全件通過させる。
    arXiv CS.AI のように「配信元がすでにAI分野で絞り込んでいる」フィードでは、
    キーワードの網羅性がそのまま取りこぼしになるため、フィルタ自体が不適切な道具になる。
    """
    return [a for a in articles if a.source in exempt_sources or matched_ai_keywords(a)]
