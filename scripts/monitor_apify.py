#!/usr/bin/env python3
"""
Monitor and kill runaway Apify actors.
Run this periodically via cron to prevent cost overruns.

Usage:
    python scripts/monitor_apify.py           # Check status
    python scripts/monitor_apify.py --kill    # Kill actors running > 5 min
    python scripts/monitor_apify.py --kill --max-runtime 120  # Custom threshold
    
Cron example (check every 5 minutes):
    */5 * * * * cd /path/to/space && ./venv/bin/python scripts/monitor_apify.py --kill >> /tmp/apify_monitor.log 2>&1
"""
import argparse
import os
import sys
from datetime import datetime, timezone

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)


def get_api_token():
    """Get Apify API token from env or config."""
    token = os.environ.get("APIFY_API_TOKEN")
    if not token:
        try:
            from saas_finder.config import config
            token = config.scraper.apify_api_token
        except:
            pass
    return token


def get_running_actors(token: str) -> list:
    """Get list of running actor runs."""
    url = f"https://api.apify.com/v2/actor-runs?token={token}&status=RUNNING"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json().get("data", {}).get("items", [])


def abort_actor(token: str, run_id: str) -> bool:
    """Abort a running actor."""
    url = f"https://api.apify.com/v2/actor-runs/{run_id}/abort?token={token}"
    resp = requests.post(url, timeout=10)
    return resp.status_code == 200


def get_runtime_seconds(started_at: str) -> float:
    """Calculate runtime in seconds from ISO timestamp."""
    start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (now - start).total_seconds()


def main():
    parser = argparse.ArgumentParser(description="Monitor Apify actors")
    parser.add_argument("--kill", action="store_true", help="Kill long-running actors")
    parser.add_argument("--max-runtime", type=int, default=300, 
                        help="Max runtime in seconds before killing (default: 300 = 5 min)")
    args = parser.parse_args()
    
    token = get_api_token()
    if not token:
        print("❌ APIFY_API_TOKEN not set")
        sys.exit(1)
    
    try:
        actors = get_running_actors(token)
    except Exception as e:
        print(f"❌ Error fetching actors: {e}")
        sys.exit(1)
    
    if not actors:
        print(f"✅ [{datetime.now().isoformat()}] No running actors")
        return
    
    print(f"⚠️  [{datetime.now().isoformat()}] {len(actors)} actor(s) running:")
    
    for actor in actors:
        run_id = actor["id"]
        started = actor.get("startedAt", "unknown")
        runtime = get_runtime_seconds(started) if started != "unknown" else 0
        runtime_min = runtime / 60
        
        status = f"  - {run_id}: running {runtime_min:.1f} min (started: {started})"
        
        if args.kill and runtime > args.max_runtime:
            print(f"{status} -> KILLING!")
            if abort_actor(token, run_id):
                print(f"    ✅ Aborted successfully")
            else:
                print(f"    ❌ Failed to abort")
        else:
            print(status)
    
    if not args.kill and actors:
        print(f"\n💡 Run with --kill to abort actors running > {args.max_runtime}s")


if __name__ == "__main__":
    main()
