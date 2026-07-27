"""aion.selector.filters のテスト"""

from datetime import timedelta

from aion.selector.filters import (
    count_undated_by_source,
    filter_ai_related,
    filter_recent_articles,
    matched_ai_keywords,
)


def test_filter_recent_articles_keeps_only_within_window(make_article):
    recent = make_article(title="新しい記事", published_offset=timedelta(hours=-2))
    old = make_article(title="古い記事", published_offset=timedelta(days=-2))
    undated = make_article(title="日付なし記事", published_offset=None)

    result = filter_recent_articles([recent, old, undated], days=1)

    assert result == [recent]


def test_filter_recent_articles_boundary_is_inclusive(make_article):
    # ちょうど境界（1日前）は含まれる想定 (>= cutoff)
    boundary = make_article(title="境界記事", published_offset=timedelta(days=-1, seconds=1))

    result = filter_recent_articles([boundary], days=1)

    assert result == [boundary]


def test_matched_ai_keywords_true_positive(make_article):
    article = make_article(title="生成AIを業務に導入", summary=None)

    assert matched_ai_keywords(article) == ["AI", "生成AI"]


def test_matched_ai_keywords_known_false_positive_substring(make_article):
    """'AI' の部分一致による既知の誤爆。PR3でのキーワード改善時の比較対象。"""
    article = make_article(title="社員研修(TRAINING)プログラムを刷新", summary=None)

    assert matched_ai_keywords(article) == ["AI"]


def test_matched_ai_keywords_no_match(make_article):
    article = make_article(title="今日の天気について", summary="全国的に晴れ")

    assert matched_ai_keywords(article) == []


def test_filter_ai_related_excludes_articles_without_keywords(make_article):
    ai_article = make_article(title="ChatGPTの新機能")
    non_ai_article = make_article(title="今日の天気")

    result = filter_ai_related([ai_article, non_ai_article])

    assert result == [ai_article]


def test_count_undated_by_source(make_article):
    a1 = make_article(source="Zenn", published_offset=None)
    a2 = make_article(source="Zenn", published_offset=None)
    a3 = make_article(source="ITmedia AI+", published_offset=timedelta(hours=-1))

    counts = count_undated_by_source([a1, a2, a3])

    assert counts == {"Zenn": 2}
