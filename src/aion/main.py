"""AION CLI - AI-Oriented News aggregator"""

import typer

from aion.processor import summarize_articles
from aion.publisher import publish_to_notion_sync
from aion.reporter import generate_report, save_report
from aion.selector import collect, explain_selection

app = typer.Typer(help="AION - AI分野のニュース収集・要約ツール")


@app.command()
def run(
    days: int = typer.Option(1, "--days", "-d", help="取得する日数"),
    max_articles: int = typer.Option(10, "--max", "-m", help="要約する最大記事数"),
    publish: bool = typer.Option(False, "--publish", "-p", help="Notionに書き出す"),
):
    """全工程を実行: RSS取得 → 要約 → レポート生成 → (オプション)Notion書き出し"""
    typer.echo("=" * 50)
    typer.echo("AION デイリーレポート生成")
    typer.echo("=" * 50)

    # Step 1: RSS収集
    typer.echo("\n[1/4] RSS収集...")
    articles = collect(days=days)

    if not articles:
        typer.echo("記事が見つかりませんでした。")
        raise typer.Exit()

    # Step 2: 要約生成
    typer.echo("\n[2/4] 要約生成...")
    summarized = summarize_articles(articles, max_articles=max_articles)

    # Step 3: レポート生成・保存
    typer.echo("\n[3/4] レポート生成...")
    report = generate_report(summarized)
    filepath = save_report(report)
    typer.echo(f"ローカル保存: {filepath}")

    # Step 4: Notion書き出し（オプション）
    if publish:
        typer.echo("\n[4/4] Notion書き出し...")
        result = publish_to_notion_sync(report)
        typer.echo(f"Notion: {result}")
    else:
        typer.echo("\n[4/4] Notion書き出し: スキップ（--publish で有効化）")

    typer.echo("\n" + "=" * 50)
    typer.echo("完了!")
    typer.echo("=" * 50)


@app.command()
def collect_cmd(
    days: int = typer.Option(1, "--days", "-d", help="取得する日数"),
    explain: bool = typer.Option(False, "--explain", help="記事ごとに通過/除外の理由を表示"),
):
    """RSSフィードから記事を収集"""
    if explain:
        articles = explain_selection(days=days)
        for article in articles:
            status = "通過" if article.excluded_reason is None else f"除外: {article.excluded_reason}"
            keywords = ", ".join(article.matched_keywords) if article.matched_keywords else "-"
            typer.echo(f"[{status}] {article.source} | {article.title[:60]} | matched: {keywords}")

        passed = sum(1 for a in articles if a.excluded_reason is None)
        typer.echo(f"\n合計 {len(articles)} 件 / 通過 {passed} 件")
        return

    articles = collect(days=days)
    typer.echo(f"\n取得完了: {len(articles)} 件")


@app.command()
def report(
    days: int = typer.Option(1, "--days", "-d", help="取得する日数"),
    max_articles: int = typer.Option(10, "--max", "-m", help="要約する最大記事数"),
):
    """レポートを生成して保存"""
    articles = collect(days=days)
    summarized = summarize_articles(articles, max_articles=max_articles)
    report_content = generate_report(summarized)
    filepath = save_report(report_content)
    typer.echo(f"レポート保存先: {filepath}")


@app.command()
def publish(
    filepath: str = typer.Argument(None, help="書き出すMarkdownファイル（省略時は最新レポート）"),
):
    """レポートをNotionに書き出す（MCP経由）"""
    from pathlib import Path

    if filepath is None:
        # 最新のレポートを探す
        output_dir = Path(__file__).parent.parent.parent / "outputs"
        reports = sorted(output_dir.glob("report_*.md"), reverse=True)
        if not reports:
            typer.echo("レポートが見つかりません。先に run コマンドを実行してください。")
            raise typer.Exit(1)
        filepath = str(reports[0])

    typer.echo(f"ファイル読み込み: {filepath}")
    with open(filepath) as f:
        content = f.read()

    typer.echo("Notionに書き出し中...")
    result = publish_to_notion_sync(content)
    typer.echo(f"完了: {result}")


if __name__ == "__main__":
    app()
