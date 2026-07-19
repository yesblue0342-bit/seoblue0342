"""
CLI 대시보드 (rich 라이브러리)
- 터미널에서 SEO 분석 결과를 시각적으로 표시
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from datetime import datetime

from seo_analyzer import PAGE_KIND_NOTES


console = Console()


def print_header():
    """헤더 출력"""
    console.print(Panel.fit(
        "[bold green]📈 이후 소설가 — 네이버 SEO 최적화 도구[/bold green]\n"
        "[dim]네이버 검색 '이후' 키워드 상위 노출 분석기[/dim]",
        border_style="green"
    ))
    console.print(f"[dim]실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]\n")


def print_rank_results(found: dict, total_checked: int):
    """네이버 노출 여부 테이블 출력 (순위 아님 — 오픈API 순서 ≠ 통합검색 순위)"""
    table = Table(
        title="📊 네이버 노출 여부 ('소설가 이후' · 공식 오픈API)",
        box=box.ROUNDED,
        border_style="green",
        header_style="bold green",
    )
    table.add_column("페이지", style="cyan", no_wrap=True)
    table.add_column("노출", justify="center")
    table.add_column("상태", justify="center")
    table.add_column("발견 URL", style="dim", max_width=55)

    for name, info in found.items():
        exposed = info.get("exposed")
        url = info.get("url") or "-"

        if exposed is None:
            exp_text = Text("⚪ 측정 불가", style="dim")
            status = Text("키/호출 확인 필요", style="dim")
        elif exposed:
            exp_text = Text("✅ 노출됨", style="bold green")
            status = Text("👍 검색결과 노출", style="green")
        else:
            exp_text = Text("❌ 미노출", style="red")
            status = Text("⚠️ 개선 필요", style="yellow")

        table.add_row(name, exp_text, status, url[:55] if url != "-" else "-")

    console.print(table)
    console.print()


def print_seo_analysis(results: list[dict]):
    """SEO 분석 결과 출력"""
    console.print("[bold]🔍 페이지별 SEO 분석 결과[/bold]\n")

    for r in results:
        score = r["score"]
        if score >= 70:
            score_style = "bold green"
            score_emoji = "🟢"
        elif score >= 40:
            score_style = "bold yellow"
            score_emoji = "🟡"
        else:
            score_style = "bold red"
            score_emoji = "🔴"

        # 점수 패널 (측정 불가면 빨간 0점 대신 '측정 불가' 표시)
        score_text = Text()
        if r.get("measurable", True):
            score_text.append(f"{score_emoji} SEO 점수: ", style="bold")
            score_text.append(f"{score}점", style=score_style)
            score_text.append(f" ({r['passed']}/{r['total']} 통과)", style="dim")
        else:
            score_text.append("⚪ 측정 불가", style="bold")
            score_text.append(" (원인은 아래 안내 참조)", style="dim")

        meta = r.get("meta", {})
        meta_text = (
            f"응답시간: {meta.get('response_time','?')}ms  |  "
            f"HTTP: {meta.get('status','?')}  |  "
            f"크기: {meta.get('content_length', 0)//1024}KB"
        )

        # 페이지 유형 안내 (owned/profile/serp — seo_analyzer.PAGE_KIND_NOTES)
        kind_note = PAGE_KIND_NOTES.get(r.get("kind", ""))
        kind_line = f"\n[dim italic]ℹ️  {kind_note}[/dim italic]" if kind_note else ""

        console.print(Panel(
            f"{score_text}\n[dim]{meta_text}[/dim]{kind_line}",
            title=f"[bold cyan]{r['label']}[/bold cyan]",
            subtitle=f"[dim]{r['url'][:70]}[/dim]",
            border_style="cyan",
        ))

        # 체크 항목 테이블
        table = Table(box=box.SIMPLE, show_header=True,
                      header_style="bold", padding=(0, 1))
        table.add_column("상태", width=3, justify="center")
        table.add_column("SEO 항목", style="cyan", min_width=25)
        table.add_column("현재값 / 권고", style="dim")

        for c in r["checks"]:
            if c["passed"]:
                icon = "[green]✅[/green]"
                val = c["value"][:70] if c["value"] else "[dim]통과[/dim]"
                table.add_row(icon, c["label"], val)
            else:
                icon = "[red]❌[/red]"
                detail = f"[red]{c['detail'][:80]}[/red]" if c["detail"] else ""
                table.add_row(icon, f"[bold]{c['label']}[/bold]", detail)

        console.print(table)

        # 권고사항
        if r["recommendations"] and not r.get("measurable", True):
            for rec in r["recommendations"]:
                console.print(f"  [yellow]ℹ️  {rec[:110]}[/yellow]")
        elif r["recommendations"]:
            console.print(f"  [bold red]⚠️  개선 필요 항목 {len(r['recommendations'])}건[/bold red]")
            for i, rec in enumerate(r["recommendations"][:5], 1):
                console.print(f"  [red]{i}.[/red] {rec[:90]}")
            if len(r["recommendations"]) > 5:
                console.print(f"  [dim]... 외 {len(r['recommendations'])-5}건 (리포트 파일 참조)[/dim]")
        else:
            console.print("  [green]🎉 모든 SEO 항목 통과![/green]")
        console.print()


def print_strategy_summary():
    """네이버 상위 노출 핵심 전략 요약 출력"""
    strategies = [
        ("1️⃣  네이버 인물정보", "등록 확인 및 상세 정보 보강"),
        ("2️⃣  홈페이지 최적화", "Title·메타디스크립션·JSON-LD 추가"),
        ("3️⃣  위키백과 보강", "출처·대표작·외부링크 추가"),
        ("4️⃣  네이버 블로그", "'이후 소설가' 키워드 포스팅 정기 발행"),
        ("5️⃣  네이버 웹마스터", "사이트맵 제출·RSS 등록"),
        ("6️⃣  언론·저서", "네이버 뉴스·책에 정보 강화"),
        ("7️⃣  수식어 통일", "모든 채널에서 '이후 소설가' 일관 사용"),
        ("8️⃣  주기적 모니터링", "매주 순위 확인 → 전략 조정"),
    ]

    table = Table(
        title="🚀 네이버 상위 노출 핵심 전략",
        box=box.ROUNDED,
        border_style="blue",
        header_style="bold blue",
    )
    table.add_column("전략", style="bold cyan", no_wrap=True)
    table.add_column("실행 항목", style="white")

    for strategy, action in strategies:
        table.add_row(strategy, action)

    console.print(table)


def print_history(history: list[dict]):
    """순위 히스토리 출력"""
    if not history:
        console.print("[dim]순위 히스토리 없음[/dim]")
        return

    table = Table(
        title="📈 최근 순위 히스토리",
        box=box.SIMPLE_HEAD,
        border_style="dim",
    )
    table.add_column("시각", style="dim", no_wrap=True)
    table.add_column("페이지", style="cyan")
    table.add_column("순위", justify="center")

    for row in history[:15]:
        rank = row["rank"]
        rank_str = f"[green]{rank}위[/green]" if rank else "[red]미발견[/red]"
        table.add_row(row["checked_at"], row["page_name"], rank_str)

    console.print(table)
