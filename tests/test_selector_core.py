"""aion.selector.core のテスト"""

from datetime import timedelta

from aion.selector.core import collect, explain_selection


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
    assert passed.matched_keywords == ["GPT", "ChatGPT"]
    assert no_date.excluded_reason == "日付なし"
    assert too_old.excluded_reason == "直近1日外"
    assert no_keyword.excluded_reason == "AIキーワード不一致"
    assert result == [passed, no_date, too_old, no_keyword]
