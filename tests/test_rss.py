"""aion.collector.rss のテスト（取得I/Oと日付パース）"""

from datetime import UTC, datetime
from types import SimpleNamespace

from aion.collector.rss import fetch_feed, parse_published_date
from aion.models import FeedConfig


def test_parse_published_date_treats_struct_time_as_utc():
    """feedparser の published_parsed はUTC正規化済み。JSTに変換されて+9時間になる。"""
    entry = SimpleNamespace(published_parsed=(2026, 7, 27, 3, 0, 0, 0, 0, 0))

    result = parse_published_date(entry)

    expected_utc = datetime(2026, 7, 27, 3, 0, 0, tzinfo=UTC)
    assert result == expected_utc.astimezone(result.tzinfo)
    assert result.hour == 12  # UTC 3:00 -> JST 12:00


def test_parse_published_date_falls_back_to_updated_parsed():
    entry = SimpleNamespace(published_parsed=None, updated_parsed=(2026, 7, 27, 3, 0, 0, 0, 0, 0))

    result = parse_published_date(entry)

    assert result is not None
    assert result.hour == 12


def test_parse_published_date_returns_none_when_no_dates():
    entry = SimpleNamespace(published_parsed=None, updated_parsed=None)

    assert parse_published_date(entry) is None


def test_fetch_feed_parses_real_fixture(fixtures_dir, monkeypatch):
    """ITmediaの実フィードスナップショットを解析し、Article群を構築できる。"""
    xml_text = (fixtures_dir / "itmedia_aiplus.xml").read_text(encoding="utf-8")

    def fake_get(url, headers=None, follow_redirects=True, timeout=30):
        return SimpleNamespace(text=xml_text, raise_for_status=lambda: None)

    monkeypatch.setattr("aion.collector.rss.httpx.get", fake_get)

    feed_config = FeedConfig(name="ITmedia AI+", url="https://example.com/rss", category="business")
    articles = fetch_feed(feed_config)

    assert len(articles) == 20
    assert all(a.source == "ITmedia AI+" for a in articles)
    assert all(a.category == "business" for a in articles)
    assert all(a.summary is None or len(a.summary) <= 500 for a in articles)
    assert all(a.published is not None for a in articles)


def test_fetch_feed_handles_broken_feed_gracefully(fixtures_dir, monkeypatch):
    """Google Cloud Japan ブログのフィードURLは現在HTMLページを返しており、0件になる。"""
    html_text = (fixtures_dir / "google_cloud_japan_blog.xml").read_text(encoding="utf-8")

    def fake_get(url, headers=None, follow_redirects=True, timeout=30):
        return SimpleNamespace(text=html_text, raise_for_status=lambda: None)

    monkeypatch.setattr("aion.collector.rss.httpx.get", fake_get)

    feed_config = FeedConfig(name="Google Cloud Japan ブログ", url="https://example.com/broken", category="tech")
    articles = fetch_feed(feed_config)

    assert articles == []
