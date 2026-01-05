# AION

AI分野のニュース・論文を自動収集・要約し、Notionに書き出すCLIツール（MCP連携）

## 概要

AION（AI-Oriented News aggregator）は、複数のRSSフィードからAI関連ニュースを収集し、Claude APIで要約を生成、MCP（Model Context Protocol）経由でNotionに自動書き出しするPython製CLIツールです。

## 参考

本プロジェクトは以下の記事を参考に作成しました：

- [AI系の情報収集手法を紹介（ビジネス・開発・研究）【2025年版】](https://zenn.dev/mkj/articles/1357a7ea2970c4) （小川 雄太郎さん）

## 機能

- RSS経由でAI関連ニュース・論文を収集（6メディア対応）
- AIキーワードフィルタで関連記事を自動抽出
- Claude APIによる要約 + "Why it matters" 生成
- Markdownレポート出力
- MCP経由でNotionに自動書き出し

## セットアップ

```bash
pip install -e .
```

### 環境変数の設定

Anthropic APIキーを設定してください：

```bash
# ~/.zshrc に追記
export ANTHROPIC_API_KEY="your-api-key"
```

> **注意**: `.zshrc` を編集した後は `source ~/.zshrc` を実行するか、新しいターミナルを開いてください。

### Notion MCP の設定

Notion への書き出しには MCP 認証が必要です。初回実行時にブラウザで認証を行ってください。

## 使い方

```bash
# 全工程実行（RSS取得 → 要約 → レポート → Notion書き出し）
python3 -m aion run --publish

# オプション指定
python3 -m aion run --days 3 --max 5 --publish

# Notion書き出しなし
python3 -m aion run

# ヘルプ
python3 -m aion --help
```

### コマンド一覧

| コマンド | 説明 |
|----------|------|
| `run` | 全工程実行（`--publish` でNotion書き出し） |
| `collect-cmd` | RSS収集のみ |
| `report` | レポート生成のみ |
| `publish` | 既存レポートをNotionに書き出し |

## 技術スタック

- Python 3.11+
- feedparser + httpx（RSS取得）
- Claude API（要約生成）
- MCP Python SDK（Notion連携）
- typer（CLI）
- Pydantic（データモデル）

## ライセンス

MIT
