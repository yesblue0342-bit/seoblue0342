#!/usr/bin/env python3
"""
이후 소설가 — 네이버 SEO 최적화 도구
메인 실행 파일

사용법:
    python main.py              # 전체 분석 실행
    python main.py --rank-only  # 순위 체크만
    python main.py --seo-only   # SEO 분석만
    python main.py --history    # 순위 히스토리 조회
    python main.py --no-report  # 리포트 파일 생성 안 함
"""

import argparse
import os
import sys
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# 모듈 임포트
from rank_monitor import init_db, check_my_rank, save_rank_result, get_rank_history
from seo_analyzer import run_full_analysis
from report_generator import generate_html_report, generate_markdown_report
from dashboard import (
    print_header, print_rank_results, print_seo_analysis,
    print_strategy_summary, print_history
)
from config import SEARCH_KEYWORD, MAX_PAGES

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="이후 소설가 — 네이버 SEO 최적화 도구"
    )
    parser.add_argument("--rank-only", action="store_true", help="순위 체크만 실행")
    parser.add_argument("--seo-only", action="store_true", help="SEO 분석만 실행")
    parser.add_argument("--history", action="store_true", help="순위 히스토리 조회")
    parser.add_argument("--no-report", action="store_true", help="리포트 파일 생성 안 함")
    parser.add_argument("--output-dir", default=".", help="리포트 저장 디렉토리")
    args = parser.parse_args()

    print_header()

    # DB 초기화
    conn = init_db()

    # ── 히스토리 조회 모드 ───────────────────────────────────────
    if args.history:
        history = get_rank_history(conn)
        print_history(history)
        conn.close()
        return

    rank_results = None
    analysis_results = []

    # ── 순위 체크 ────────────────────────────────────────────────
    if not args.seo_only:
        console.print("[bold]📡 네이버 순위 체크 시작...[/bold]")
        console.print(f"[dim]키워드: '{SEARCH_KEYWORD}' | 상위 {MAX_PAGES*10}개 결과 분석[/dim]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("네이버 검색 결과 수집 중...", total=None)
            found, all_results, reliable = check_my_rank(SEARCH_KEYWORD)
            progress.update(task, description="[green]완료!")

        save_rank_result(conn, SEARCH_KEYWORD, found, len(all_results))
        rank_results = (found, all_results, reliable)
        print_rank_results(found, len(all_results))

    # ── SEO 분석 ─────────────────────────────────────────────────
    if not args.rank_only:
        console.print("[bold]🔎 페이지 SEO 분석 시작...[/bold]")
        console.print("[dim]홈페이지 + 위키백과 페이지 분석 중...[/dim]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("페이지 분석 중...", total=None)
            analysis_results = run_full_analysis()
            progress.update(task, description="[green]완료!")

        print_seo_analysis(analysis_results)

    # ── 전략 가이드 ──────────────────────────────────────────────
    print_strategy_summary()
    console.print()

    # ── 리포트 파일 생성 ─────────────────────────────────────────
    if not args.no_report and (analysis_results or rank_results):
        os.makedirs(args.output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = os.path.join(args.output_dir, f"seo_report_{ts}.html")
        md_path = os.path.join(args.output_dir, f"seo_report_{ts}.md")

        console.print("[bold]📁 리포트 파일 저장 중...[/bold]")
        if analysis_results:
            generate_html_report(analysis_results, rank_results, html_path)
            generate_markdown_report(analysis_results, rank_results, md_path)
            console.print(f"  [green]✅ HTML 리포트:[/green] {html_path}")
            console.print(f"  [green]✅ 마크다운 리포트:[/green] {md_path}")

    conn.close()
    console.print("\n[bold green]✅ 분석 완료![/bold green]\n")
    console.print(
        "[dim]💡 팁: 매주 실행해서 순위 변동을 추적하세요. "
        "python main.py --history 로 히스토리를 확인할 수 있습니다.[/dim]"
    )


if __name__ == "__main__":
    main()
