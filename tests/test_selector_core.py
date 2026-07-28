"""aion.selector.core のテスト"""

from datetime import timedelta

from aion.selector.core import collect, explain_selection, keyword_filter_exempt_sources


def test_collect_applies_date_then_keyword_filter(make_article, monkeypatch):
    recent_ai = make_article(title="ChatGPTの新機能", published_offset=timedelta(hours=-1))
    recent_non_ai = make_article(title="今日の天気", published_offset=timedelta(hours=-1))
    old_ai = make_article(title="生成AIの話題", published_offset=timedelta(days=-2))

    monkeypatch.setattr(
        "aion.selector.core.fetch_all_feeds",
        lambda: [recent_ai, recent_non_ai, old_ai],
    )

    result = collect(days=1)

    assert result == [recent_ai]


def test_collect_skips_keyword_filter_when_ai_filter_false(make_article, monkeypatch):
    recent_non_ai = make_article(title="今日の天気", published_offset=timedelta(hours=-1))

    monkeypatch.setattr("aion.selector.core.fetch_all_feeds", lambda: [recent_non_ai])

    result = collect(days=1, ai_filter=False)

    assert result == [recent_non_ai]


def test_collect_returns_articles_in_score_order(make_article, monkeypatch):
    """collect がスコアを付与し降順で返すこと（要約枠の切り出しは select_for_summary 側）。"""
    weak = make_article(title="ロボットの話", published_offset=timedelta(hours=-1))
    strong = make_article(title="AnthropicとOpenAIの新モデル", published_offset=timedelta(hours=-1))

    monkeypatch.setattr("aion.selector.core.fetch_all_feeds", lambda: [weak, strong])

    result = collect(days=1)

    assert result == [strong, weak]
    assert strong.score > weak.score > 0


def test_keyword_filter_exempt_sources_reads_feeds_yaml(tmp_path):
    config = tmp_path / "feeds.yaml"
    config.write_text(
        "feeds:\n"
        '  - name: "免除フィード"\n'
        '    url: "https://example.com/a.xml"\n'
        '    category: "research"\n'
        "    ai_filter: false\n"
        '  - name: "通常フィード"\n'
        '    url: "https://example.com/b.xml"\n'
        '    category: "tech"\n',
        encoding="utf-8",
    )

    assert keyword_filter_exempt_sources(config) == frozenset({"免除フィード"})


def test_collect_exempts_configured_sources_from_keyword_filter(make_article, monkeypatch):
    """免除フィードの記事はキーワード0件でも collect を通ること。"""
    exempt_non_ai = make_article(
        title="Sparse Matrix Reordering",
        source="arXiv CS.AI",
        published_offset=timedelta(hours=-1),
    )
    other_non_ai = make_article(
        title="今日の天気", source="Zenn", published_offset=timedelta(hours=-1)
    )

    monkeypatch.setattr(
        "aion.selector.core.fetch_all_feeds",
        lambda: [exempt_non_ai, other_non_ai],
    )
    monkeypatch.setattr(
        "aion.selector.core.keyword_filter_exempt_sources",
        lambda: frozenset({"arXiv CS.AI"}),
    )

    assert collect(days=1) == [exempt_non_ai]


def test_collect_still_applies_date_filter_to_exempt_sources(make_article, monkeypatch):
    """免除はキーワードフィルタのみ。日付フィルタは免除フィードにも効くこと。"""
    old = make_article(
        title="Sparse Matrix Reordering",
        source="arXiv CS.AI",
        published_offset=timedelta(days=-2),
    )

    monkeypatch.setattr("aion.selector.core.fetch_all_feeds", lambda: [old])
    monkeypatch.setattr(
        "aion.selector.core.keyword_filter_exempt_sources",
        lambda: frozenset({"arXiv CS.AI"}),
    )

    assert collect(days=1) == []


def test_explain_selection_marks_exempt_articles_as_passed(make_article, monkeypatch):
    """--explain 上でも免除フィードの記事は「AIキーワード不一致」で除外されないこと。"""
    exempt_non_ai = make_article(
        title="Sparse Matrix Reordering",
        source="arXiv CS.AI",
        published_offset=timedelta(hours=-1),
    )

    monkeypatch.setattr("aion.selector.core.fetch_all_feeds", lambda: [exempt_non_ai])
    monkeypatch.setattr(
        "aion.selector.core.keyword_filter_exempt_sources",
        lambda: frozenset({"arXiv CS.AI"}),
    )

    explain_selection(days=1)

    assert exempt_non_ai.excluded_reason is None
    assert exempt_non_ai.matched_keywords == []


def test_explain_selection_assigns_reasons_per_stage(make_article, monkeypatch):
    passed = make_article(title="ChatGPTの新機能", published_offset=timedelta(hours=-1))
    no_date = make_article(title="ChatGPTの新機能", published_offset=None)
    too_old = make_article(title="ChatGPTの新機能", published_offset=timedelta(days=-2))
    no_keyword = make_article(title="今日の天気", published_offset=timedelta(hours=-1))

    monkeypatch.setattr(
        "aion.selector.core.fetch_all_feeds",
        lambda: [passed, no_date, too_old, no_keyword],
    )

    result = explain_selection(days=1)

    assert passed.excluded_reason is None
    # "GPT" は "ChatGPT" の内部に単語境界なく現れるためマッチしない（PR3の単語境界マッチ）
    assert passed.matched_keywords == ["ChatGPT"]
    assert no_date.excluded_reason == "日付なし"
    assert too_old.excluded_reason == "直近1日外"
    assert no_keyword.excluded_reason == "AIキーワード不一致"
    assert result == [passed, no_date, too_old, no_keyword]
