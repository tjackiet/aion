"""記事スコアリング（構造的シグナルのみ）

ここで扱うのは「その記事がどれくらいAIの話であることが確からしいか」だけで、
記事の中身が良いか悪いか（ニュースバリュー）は判定しない。表明止まり記事の
減点のような価値判断は別途扱う。

スコアは以下の構造的シグナルの合計:

1. マッチしたキーワードの重み和
   固有名詞ほど「本当にAIの話である」ことの証拠として強い。'AI' や 'ロボット' は
   文脈次第で何にでも付くが、'Anthropic' や 'DeepSeek' が出てくる記事はAIの話である
   確率が高い。重みは config/keywords.yaml のカテゴリ単位で与える。
2. タイトル中のマッチは概要中のマッチより強く数える
   タイトルに出てくる語がその記事の主題であることが多いため。
3. 新しさ
   同程度の確からしさなら新しい記事を優先する。
4. キーワードフィルタ免除フィードへの下駄
   免除フィード（arXiv等）はマッチ0件でも通過するため、そのままだとスコア0で
   常に最下位に沈み、クォータで枠を確保しても中身が新しさ順にしかならない。
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from aion.models import Article
from aion.selector.filters import matched_keywords_in_text
from aion.selector.keywords import AI_KEYWORD_GROUPS

JST = ZoneInfo("Asia/Tokyo")

# config/keywords.yaml のカテゴリ名 → 重み。
# 汎用語ほど軽く、固有名詞ほど重い。
KEYWORD_CATEGORY_WEIGHTS = {
    "基本用語": 1.0,  # AI / 機械学習 など。何にでも付くので軽い
    "応用分野": 1.0,  # 画像生成 / ロボット など。AI以外の文脈でも使われる
    "エージェント": 2.0,
    "技術用語": 2.0,
    "LLM・生成AI": 3.0,
    "モデル名": 3.0,  # Llama / DeepSeek など固有名詞
    "サービス・企業": 3.0,  # OpenAI / Anthropic など固有名詞
}
DEFAULT_KEYWORD_WEIGHT = 1.0

# タイトル中のマッチを概要中のマッチの何倍に数えるか
TITLE_MULTIPLIER = 2.0

# 新しさによる加点の上限と半減期。公開直後が最大で、半減期ごとに半分になる。
RECENCY_MAX_POINTS = 3.0
RECENCY_HALF_LIFE_HOURS = 24.0

# キーワードフィルタ免除フィードに与える下駄
EXEMPT_SOURCE_BASE_POINTS = 2.0


def keyword_weight(keyword: str) -> float:
    """キーワード1件あたりの重みを返す"""
    for category, keywords in AI_KEYWORD_GROUPS.items():
        if keyword in keywords:
            return KEYWORD_CATEGORY_WEIGHTS.get(category, DEFAULT_KEYWORD_WEIGHT)
    return DEFAULT_KEYWORD_WEIGHT


def keyword_score(article: Article) -> float:
    """マッチしたキーワードの重み和（タイトル中のマッチは重く数える）"""
    title_hits = set(matched_keywords_in_text(article.title))
    summary_hits = set(matched_keywords_in_text(article.summary or "")) - title_hits

    return sum(keyword_weight(kw) * TITLE_MULTIPLIER for kw in title_hits) + sum(
        keyword_weight(kw) for kw in summary_hits
    )


def recency_score(article: Article, now: datetime | None = None) -> float:
    """公開からの経過時間で半減する加点

    published が無い記事は日付フィルタで既に落ちているが、念のため0点として扱う。
    """
    if article.published is None:
        return 0.0

    now = now or datetime.now(JST)
    age_hours = (now - article.published).total_seconds() / 3600
    if age_hours < 0:  # 未来日付の記事は最新扱い
        age_hours = 0.0

    return RECENCY_MAX_POINTS * (0.5 ** (age_hours / RECENCY_HALF_LIFE_HOURS))


def score_article(
    article: Article,
    exempt_sources: frozenset[str] = frozenset(),
    now: datetime | None = None,
) -> float:
    """記事の総合スコアを算出する"""
    score = keyword_score(article) + recency_score(article, now=now)
    if article.source in exempt_sources:
        score += EXEMPT_SOURCE_BASE_POINTS
    return score


def score_articles(
    articles: list[Article],
    exempt_sources: frozenset[str] = frozenset(),
    now: datetime | None = None,
) -> list[Article]:
    """記事リストに score を付与する（同じオブジェクトを書き換えて返す）"""
    now = now or datetime.now(JST)
    for article in articles:
        article.score = score_article(article, exempt_sources=exempt_sources, now=now)
    return articles
