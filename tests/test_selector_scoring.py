"""aion.selector.scoring のテスト"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aion.selector.scoring import (
    EXEMPT_SOURCE_BASE_POINTS,
    RECENCY_MAX_POINTS,
    TITLE_MULTIPLIER,
    keyword_score,
    keyword_weight,
    recency_score,
    score_article,
    score_articles,
)

JST = ZoneInfo("Asia/Tokyo")


def test_keyword_weight_is_higher_for_proper_nouns():
    """固有名詞は汎用語より重いこと。"""
    assert keyword_weight("Anthropic") > keyword_weight("AI")
    assert keyword_weight("DeepSeek") > keyword_weight("ロボット")


def test_keyword_weight_falls_back_for_unknown_keyword():
    assert keyword_weight("存在しないキーワード") == 1.0


def test_keyword_score_counts_title_matches_more_than_summary(make_article):
    in_title = make_article(title="Anthropicの新モデル", summary="詳細は後日")
    in_summary = make_article(title="新モデルの話", summary="Anthropicが発表した")

    assert keyword_score(in_title) == keyword_weight("Anthropic") * TITLE_MULTIPLIER
    assert keyword_score(in_summary) == keyword_weight("Anthropic")
    assert keyword_score(in_title) > keyword_score(in_summary)


def test_keyword_score_does_not_double_count_same_keyword(make_article):
    """タイトルと概要の両方に出る語はタイトル側の重みだけで数えること。"""
    both = make_article(title="Anthropicの新モデル", summary="Anthropicが発表")

    assert keyword_score(both) == keyword_weight("Anthropic") * TITLE_MULTIPLIER


def test_keyword_score_accumulates_over_distinct_keywords(make_article):
    one = make_article(title="Anthropicの発表")
    two = make_article(title="AnthropicとOpenAIの発表")

    assert keyword_score(two) > keyword_score(one)


def test_keyword_score_is_zero_without_matches(make_article):
    assert keyword_score(make_article(title="今日の天気", summary="全国的に晴れ")) == 0.0


def test_recency_score_decays_with_age(make_article):
    now = datetime(2026, 7, 27, 12, 0, tzinfo=JST)
    fresh = make_article(title="x")
    fresh.published = now
    day_old = make_article(title="x")
    day_old.published = now - timedelta(hours=24)

    assert recency_score(fresh, now=now) == RECENCY_MAX_POINTS
    # 半減期は24時間
    assert recency_score(day_old, now=now) == RECENCY_MAX_POINTS / 2


def test_recency_score_is_zero_without_published_date(make_article):
    assert recency_score(make_article(title="x", published_offset=None)) == 0.0


def test_recency_score_clamps_future_dates(make_article):
    now = datetime(2026, 7, 27, 12, 0, tzinfo=JST)
    future = make_article(title="x")
    future.published = now + timedelta(hours=5)

    assert recency_score(future, now=now) == RECENCY_MAX_POINTS


def test_score_article_gives_base_points_to_exempt_sources(make_article):
    """免除フィードはマッチ0件がありうるので、スコア0で常に沈まないこと。"""
    now = datetime(2026, 7, 27, 12, 0, tzinfo=JST)
    article = make_article(title="Sparse Matrix Reordering", source="arXiv CS.AI")
    article.published = now

    without = score_article(article, now=now)
    with_exemption = score_article(article, exempt_sources=frozenset({"arXiv CS.AI"}), now=now)

    assert with_exemption - without == EXEMPT_SOURCE_BASE_POINTS
    assert with_exemption > 0


def test_score_articles_assigns_score_field(make_article):
    now = datetime(2026, 7, 27, 12, 0, tzinfo=JST)
    ai = make_article(title="Anthropicの新モデル")
    ai.published = now
    non_ai = make_article(title="今日の天気")
    non_ai.published = now

    score_articles([ai, non_ai], now=now)

    assert ai.score > non_ai.score
    assert non_ai.score == RECENCY_MAX_POINTS  # キーワード0件でも新しさ分は付く
