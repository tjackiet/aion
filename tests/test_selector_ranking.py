"""aion.selector.ranking のテスト"""

from datetime import timedelta

from aion.selector.ranking import (
    allocate_quota,
    category_breakdown,
    rank_articles,
    select_for_summary,
)


def _scored(make_article, category: str, score: float, title: str):
    article = make_article(title=title, category=category, published_offset=timedelta(hours=-1))
    article.score = score
    return article


def test_rank_articles_sorts_by_score_descending(make_article):
    low = _scored(make_article, "tech", 1.0, "低")
    high = _scored(make_article, "tech", 9.0, "高")
    mid = _scored(make_article, "tech", 5.0, "中")

    assert rank_articles([low, high, mid]) == [high, mid, low]


def test_rank_articles_does_not_mutate_input(make_article):
    low = _scored(make_article, "tech", 1.0, "低")
    high = _scored(make_article, "tech", 9.0, "高")
    original = [low, high]

    rank_articles(original)

    assert original == [low, high]


def test_rank_articles_breaks_ties_by_recency_then_title(make_article):
    older = _scored(make_article, "tech", 5.0, "b")
    older.published = older.published - timedelta(hours=5)
    newer = _scored(make_article, "tech", 5.0, "c")

    assert rank_articles([older, newer]) == [newer, older]


def test_allocate_quota_matches_default_at_ten():
    assert allocate_quota(10) == {"business": 3, "tech": 4, "research": 3}


def test_allocate_quota_always_sums_to_max_articles():
    for max_articles in range(0, 21):
        allocated = allocate_quota(max_articles)
        assert sum(allocated.values()) == max_articles, max_articles


def test_allocate_quota_scales_proportionally():
    allocated = allocate_quota(20)

    assert allocated == {"business": 6, "tech": 8, "research": 6}


def test_allocate_quota_handles_zero():
    assert allocate_quota(0) == {"business": 0, "tech": 0, "research": 0}


def test_select_for_summary_enforces_category_quota(make_article):
    """1カテゴリが上位を独占していても他カテゴリの枠が確保されること。

    これが PR4b の本題。以前は先頭N件切りだったため、feeds.yaml の先頭にある
    business が要約枠を全部食っていた。
    """
    business = [_scored(make_article, "business", 100 - i, f"b{i}") for i in range(20)]
    tech = [_scored(make_article, "tech", 10 - i, f"t{i}") for i in range(20)]
    research = [_scored(make_article, "research", 5 - i, f"r{i}") for i in range(20)]

    selected = select_for_summary(business + tech + research, max_articles=10)

    assert len(selected) == 10
    assert category_breakdown(selected) == {"business": 3, "tech": 4, "research": 3}


def test_select_for_summary_takes_highest_scored_within_each_category(make_article):
    business = [_scored(make_article, "business", score, f"b{score}") for score in (1, 50, 20)]
    tech = [_scored(make_article, "tech", score, f"t{score}") for score in (3, 80)]

    selected = select_for_summary(business + tech, max_articles=10)
    titles = [a.title for a in selected]

    # 枠(business 3 / tech 4)より記事が少ないので全件入るが、順序はカテゴリ横断のスコア順
    assert titles == ["t80", "b50", "b20", "t3", "b1"]


def test_select_for_summary_backfills_when_a_category_is_thin(make_article):
    """記事が枠に満たないカテゴリの余り枠は他カテゴリで埋めること。

    クォータのせいで要約枠が空くのは無駄なので、余りは全体のスコア順で補充する。
    """
    business = [_scored(make_article, "business", 100 - i, f"b{i}") for i in range(20)]
    tech = [_scored(make_article, "tech", 50 - i, f"t{i}") for i in range(20)]
    # research は1件しかない
    research = [_scored(make_article, "research", 1.0, "r0")]

    selected = select_for_summary(business + tech + research, max_articles=10)
    breakdown = category_breakdown(selected)

    assert len(selected) == 10
    assert breakdown["research"] == 1
    # research の余り2枠がスコア上位の business / tech に回る
    assert breakdown["business"] + breakdown["tech"] == 9
    assert breakdown["business"] >= 3
    assert breakdown["tech"] >= 4


def test_select_for_summary_returns_fewer_than_max_when_pool_is_small(make_article):
    articles = [_scored(make_article, "tech", 5.0, "t0")]

    assert select_for_summary(articles, max_articles=10) == articles


def test_select_for_summary_handles_empty_pool():
    assert select_for_summary([], max_articles=10) == []


def test_select_for_summary_ignores_unknown_categories_until_backfill(make_article):
    """クォータに無いカテゴリの記事も、余り枠があれば拾われること。"""
    unknown = [_scored(make_article, "other", 100.0, "u0")]
    tech = [_scored(make_article, "tech", 1.0, "t0")]

    selected = select_for_summary(unknown + tech, max_articles=10)

    assert set(a.title for a in selected) == {"u0", "t0"}


def test_select_for_summary_result_is_score_ordered(make_article):
    articles = [
        _scored(make_article, "business", 1.0, "b"),
        _scored(make_article, "tech", 9.0, "t"),
        _scored(make_article, "research", 5.0, "r"),
    ]

    selected = select_for_summary(articles, max_articles=10)

    assert [a.score for a in selected] == [9.0, 5.0, 1.0]


def test_category_breakdown_counts_per_category(make_article):
    articles = [
        _scored(make_article, "tech", 1.0, "a"),
        _scored(make_article, "tech", 1.0, "b"),
        _scored(make_article, "research", 1.0, "c"),
    ]

    assert category_breakdown(articles) == {"tech": 2, "research": 1}
