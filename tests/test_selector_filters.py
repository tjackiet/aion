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


def test_matched_ai_keywords_fixes_substring_false_positive(make_article):
    """PR2時点では 'AI' が 'TRAINING' の部分文字列として誤爆していた（既知のバグ）。
    PR3の単語境界マッチでこの誤爆が解消されたことを固定する。"""
    article = make_article(title="社員研修(TRAINING)プログラムを刷新", summary=None)

    assert matched_ai_keywords(article) == []


def test_matched_ai_keywords_word_boundary_rejects_other_known_false_positives(make_article):
    cases = [
        "ストレージの容量を見直す",  # STORAGE に RAG
        "平均値(AVERAGE)を算出する",  # AVERAGE に RAG
        "メールでの連絡(EMAIL)手段",  # EMAIL に AI
        "詳細(DETAIL)な説明を追加",  # DETAIL に AI
    ]
    for title in cases:
        article = make_article(title=title, summary=None)
        assert matched_ai_keywords(article) == [], title


def test_matched_ai_keywords_still_matches_ai_adjacent_to_japanese(make_article):
    """日本語に直接隣接する場合は正しくマッチし続けること（回帰防止）。"""
    cases = [
        ("生成AIを業務に導入", ["AI", "生成AI"]),
        ("AIエージェントと働く", ["AI", "AIエージェント", "エージェント"]),
    ]
    for title, expected in cases:
        article = make_article(title=title, summary=None)
        assert matched_ai_keywords(article) == expected


def test_matched_ai_keywords_new_vocabulary(make_article):
    """PR3で追加した語彙（2024年以降の主要モデル・技術用語）がマッチすること。"""
    cases = [
        ("Metaが新しいLlamaモデルを発表", "Llama"),
        ("フランスのMistralが資金調達", "Mistral"),
        ("中国DeepSeekの新モデル", "DeepSeek"),
        ("OpenAIの動画生成モデルSora", "Sora"),
        ("MCPサーバーを実装する", "MCP"),
        ("LoRAで効率的にファインチューニング", "LoRA"),
        ("拡散モデルによる画像生成の仕組み", "拡散モデル"),
        ("強化学習エージェントの設計", "強化学習"),
        ("マルチモーダルLLMの活用事例", "マルチモーダル"),
        ("埋め込みベクトルの活用", "埋め込み"),
        ("量子化による軽量化手法", "量子化"),
        ("Machine Learningの基礎から学ぶ", "Machine Learning"),
    ]
    for title, expected_kw in cases:
        article = make_article(title=title, summary=None)
        assert expected_kw in matched_ai_keywords(article), title


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
