"""
CLI interface for SaaS Idea Finder.
"""

import click
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import config
from .twitter.client import get_twitter_client
from .scoring.scorer import IdeaScorer
from .storage.database import get_db
from .output.formatter import (
    format_idea,
    format_ideas_table,
    print_stats,
    print_search_summary
)
from .output.exporters import export_to_json, export_to_csv

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    🎯 SaaS Idea Finder - Discover validated SaaS ideas from Twitter.
    
    Find, analyze, and score SaaS ideas from #buildinpublic and #indiehackers
    communities on Twitter.
    """
    pass


@cli.command()
@click.option(
    "--hashtags", "-h",
    default="buildinpublic,indiehackers,saas",
    help="Comma-separated hashtags to search (without #)"
)
@click.option(
    "--days", "-d",
    default=7,
    type=int,
    help="Number of days to look back"
)
@click.option(
    "--min-mrr", "-m",
    default=0,
    type=float,
    help="Minimum MRR to include"
)
@click.option(
    "--min-score", "-s",
    default=0,
    type=int,
    help="Minimum score to include (0-100)"
)
@click.option(
    "--max-results", "-n",
    default=100,
    type=int,
    help="Maximum number of tweets to fetch"
)
@click.option(
    "--require-image", "-i",
    is_flag=True,
    help="Only include tweets with images"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Export results to file (JSON or CSV based on extension)"
)
@click.option(
    "--no-save",
    is_flag=True,
    help="Don't save results to database"
)
@click.option(
    "--mock",
    is_flag=True,
    help="Use mock data (for testing without API)"
)
def search(
    hashtags: str,
    days: int,
    min_mrr: float,
    min_score: int,
    max_results: int,
    require_image: bool,
    output: Optional[str],
    no_save: bool,
    mock: bool
):
    """
    🔍 Search Twitter for SaaS ideas.
    
    Examples:
    
        saas-finder search --hashtags "buildinpublic,indiehackers"
        
        saas-finder search --days 3 --min-mrr 5000
        
        saas-finder search --min-score 70 --output ideas.json
    """
    # Parse hashtags
    hashtag_list = [h.strip() for h in hashtags.split(",")]
    
    console.print()
    console.print(f"[bold cyan]🔍 Searching Twitter for SaaS ideas...[/bold cyan]")
    console.print(f"   Hashtags: {', '.join('#' + h for h in hashtag_list)}")
    console.print(f"   Days: {days}")
    console.print()
    
    # Get Twitter client
    use_mock = mock or not config.twitter.bearer_token
    if use_mock and not mock:
        console.print("[yellow]⚠️  No Twitter API token found, using mock data[/yellow]")
        console.print("[dim]   Set TWITTER_BEARER_TOKEN in .env for real data[/dim]")
        console.print()
    
    client = get_twitter_client(use_mock=use_mock)
    scorer = IdeaScorer()
    
    # Search tweets
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Fetching tweets...", total=None)
        
        tweets = client.search_revenue_tweets(
            hashtags=hashtag_list,
            require_image=require_image,
            max_results=max_results,
            days=days
        )
        
        progress.update(task, description=f"Found {len(tweets)} tweets, processing...")
        
        # Process tweets into ideas
        ideas = []
        for tweet in tweets:
            idea = scorer.process_tweet(tweet)
            if idea:
                # Apply filters
                if min_mrr > 0 and (idea.reported_mrr or 0) < min_mrr:
                    continue
                if min_score > 0 and idea.total_score < min_score:
                    continue
                ideas.append(idea)
        
        progress.update(task, description="Processing complete!")
    
    # Sort by score
    ideas.sort(key=lambda x: x.total_score, reverse=True)
    
    if not ideas:
        console.print("[yellow]No ideas found matching your criteria.[/yellow]")
        return
    
    # Save to database
    new_count = 0
    updated_count = 0
    if not no_save:
        db = get_db()
        new_count, updated_count = db.save_ideas(ideas)
        db.log_search(
            query=f"hashtags:{hashtags}",
            hashtags=hashtag_list,
            results_count=len(tweets),
            new_ideas_count=new_count
        )
    
    # Display results
    console.print(format_ideas_table(ideas[:20]))
    
    if len(ideas) > 20:
        console.print(f"[dim]... and {len(ideas) - 20} more ideas[/dim]")
    
    # Print summary
    print_search_summary(
        total_found=len(ideas),
        new_saved=new_count,
        updated=updated_count,
        query=f"#{' #'.join(hashtag_list)}"
    )
    
    # Export if requested
    if output:
        if output.endswith('.csv'):
            export_to_csv([i.to_dict() for i in ideas], output)
        else:
            export_to_json([i.to_dict() for i in ideas], output)
        console.print(f"[green]✅ Exported to {output}[/green]")


@cli.command()
@click.option(
    "--min-score", "-s",
    default=0,
    type=int,
    help="Minimum score filter"
)
@click.option(
    "--min-mrr", "-m",
    default=0,
    type=float,
    help="Minimum MRR filter"
)
@click.option(
    "--category", "-c",
    help="Filter by category"
)
@click.option(
    "--favorites", "-f",
    is_flag=True,
    help="Show only favorites"
)
@click.option(
    "--limit", "-n",
    default=20,
    type=int,
    help="Number of results to show"
)
@click.option(
    "--sort", "-o",
    type=click.Choice(["score", "mrr", "date_found", "likes"]),
    default="score",
    help="Sort by field"
)
@click.option(
    "--output", "-O",
    type=click.Path(),
    help="Export results to file"
)
def list(
    min_score: int,
    min_mrr: float,
    category: Optional[str],
    favorites: bool,
    limit: int,
    sort: str,
    output: Optional[str]
):
    """
    📋 List saved SaaS ideas from database.
    
    Examples:
    
        saas-finder list --min-score 70
        
        saas-finder list --favorites --limit 10
        
        saas-finder list --category "AI/ML Tool"
    """
    db = get_db()
    
    ideas = db.list_ideas(
        min_score=min_score,
        min_mrr=min_mrr,
        category=category,
        favorites_only=favorites,
        limit=limit,
        order_by=sort
    )
    
    if not ideas:
        console.print("[yellow]No ideas found matching your criteria.[/yellow]")
        return
    
    # Display table
    console.print()
    console.print(format_ideas_table(ideas))
    
    total = db.count_ideas(min_score=min_score, min_mrr=min_mrr, category=category)
    if total > limit:
        console.print(f"[dim]Showing {limit} of {total} ideas[/dim]")
    
    # Export if requested
    if output:
        if output.endswith('.csv'):
            export_to_csv(ideas, output)
        else:
            export_to_json(ideas, output)
        console.print(f"[green]✅ Exported to {output}[/green]")


@cli.command()
@click.argument("idea_id", type=int)
def show(idea_id: int):
    """
    🔎 Show detailed view of a specific idea.
    
    Example:
    
        saas-finder show 42
    """
    db = get_db()
    idea = db.get_idea(idea_id)
    
    if not idea:
        console.print(f"[red]Idea #{idea_id} not found.[/red]")
        return
    
    console.print()
    console.print(format_idea(idea))


@cli.command()
@click.argument("idea_id", type=int)
def favorite(idea_id: int):
    """
    ⭐ Toggle favorite status for an idea.
    
    Example:
    
        saas-finder favorite 42
    """
    db = get_db()
    result = db.toggle_favorite(idea_id)
    
    if result:
        console.print(f"[green]⭐ Idea #{idea_id} added to favorites[/green]")
    else:
        console.print(f"[yellow]Idea #{idea_id} removed from favorites[/yellow]")


@cli.command()
@click.argument("idea_id", type=int)
@click.argument("note", type=str)
def note(idea_id: int, note: str):
    """
    📝 Add a note to an idea.
    
    Example:
    
        saas-finder note 42 "Interesting concept, research competitors"
    """
    db = get_db()
    success = db.add_note(idea_id, note)
    
    if success:
        console.print(f"[green]📝 Note added to idea #{idea_id}[/green]")
    else:
        console.print(f"[red]Idea #{idea_id} not found.[/red]")


@cli.command()
def stats():
    """
    📊 Show database statistics.
    """
    db = get_db()
    stats_data = db.get_stats()
    print_stats(stats_data)
    
    # Show categories
    categories = db.get_categories()
    if categories:
        console.print()
        console.print("[bold cyan]📁 Categories[/bold cyan]")
        for cat, count in categories[:10]:
            console.print(f"   {cat}: {count}")


@cli.command()
def categories():
    """
    📁 List all categories with counts.
    """
    db = get_db()
    categories = db.get_categories()
    
    if not categories:
        console.print("[yellow]No categories found.[/yellow]")
        return
    
    console.print()
    console.print("[bold cyan]📁 Categories[/bold cyan]")
    console.print()
    
    for cat, count in categories:
        bar = "█" * min(count, 30)
        console.print(f"   {cat:20} {bar} {count}")


@cli.command()
@click.argument("idea_id", type=int)
@click.confirmation_option(prompt="Are you sure you want to delete this idea?")
def delete(idea_id: int):
    """
    🗑️ Delete an idea from the database.
    
    Example:
    
        saas-finder delete 42
    """
    db = get_db()
    success = db.delete_idea(idea_id)
    
    if success:
        console.print(f"[green]🗑️ Idea #{idea_id} deleted[/green]")
    else:
        console.print(f"[red]Idea #{idea_id} not found.[/red]")


@cli.command()
def history():
    """
    📜 Show search history.
    """
    db = get_db()
    searches = db.get_search_history(limit=10)
    
    if not searches:
        console.print("[yellow]No search history found.[/yellow]")
        return
    
    console.print()
    console.print("[bold cyan]📜 Recent Searches[/bold cyan]")
    console.print()
    
    for search in searches:
        date = search.search_date.strftime("%Y-%m-%d %H:%M") if search.search_date else "?"
        console.print(f"   [{date}] {search.query}")
        console.print(f"      Found: {search.results_count}, New: {search.new_ideas_count}")


@cli.command()
@click.option(
    "--type", "-t",
    type=click.Choice(["founder", "product"]),
    default="founder",
    help="Watch type"
)
@click.argument("identifier")
@click.option("--notes", "-n", help="Optional notes")
def watch(type: str, identifier: str, notes: Optional[str]):
    """
    👀 Add a founder or product to watchlist.
    
    Examples:
    
        saas-finder watch --type founder @levelsio
        
        saas-finder watch --type product example.com
    """
    db = get_db()
    db.add_to_watchlist(identifier, type, notes)
    console.print(f"[green]👀 Added {identifier} to {type} watchlist[/green]")


@cli.command()
@click.option(
    "--type", "-t",
    type=click.Choice(["founder", "product", "all"]),
    default="all",
    help="Filter by type"
)
def watchlist(type: str):
    """
    👀 Show watchlist items.
    """
    db = get_db()
    watch_type = None if type == "all" else type
    items = db.get_watchlist(watch_type=watch_type)
    
    if not items:
        console.print("[yellow]Watchlist is empty.[/yellow]")
        return
    
    console.print()
    console.print("[bold cyan]👀 Watchlist[/bold cyan]")
    console.print()
    
    for item in items:
        emoji = "👤" if item.watch_type == "founder" else "🔗"
        console.print(f"   {emoji} [{item.watch_type}] {item.identifier}")
        if item.notes:
            console.print(f"      {item.notes}")


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
