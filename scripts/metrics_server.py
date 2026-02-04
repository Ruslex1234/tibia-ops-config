#!/usr/bin/env python3
"""
Prometheus Metrics Server for Tibia Ops Config.

Exposes application metrics for monitoring:
- Enemy tracking statistics
- API call metrics
- Troll list statistics
- Guild monitoring data

Demonstrates: Observability, Prometheus integration, metrics-driven development
"""

import json
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (  # noqa: E402
    ENEMY_GUILDS,
    TROLLS_FILE,
    BASTEX_FILE,
    WORLDS
)
from tibia_api import get_online_guild_members  # noqa: E402

# =============================================================================
# Prometheus Metrics (manual implementation for zero dependencies)
# =============================================================================

METRICS = {
    'trolls_total': 0,
    'bastex_total': 0,
    'enemies_online': 0,
    'api_calls_total': 0,
    'api_errors_total': 0,
    'last_check_timestamp': 0,
    'last_check_duration_seconds': 0,
    'new_trolls_added_total': 0,
    'deaths_analyzed_total': 0,
    'worlds_monitored': len(WORLDS),
    'guilds_monitored': len(ENEMY_GUILDS),
}

# Per-guild metrics
GUILD_METRICS = {}


def load_list_count(filepath):
    """Load a JSON list and return its count."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            return len(data) if isinstance(data, list) else 0
    except Exception:
        return 0


def update_metrics():
    """Update all metrics by checking current state."""
    start_time = time.time()

    # Update list counts
    METRICS['trolls_total'] = load_list_count(TROLLS_FILE)
    METRICS['bastex_total'] = load_list_count(BASTEX_FILE)

    # Check online enemies per guild
    total_online = 0
    for guild_name, world in ENEMY_GUILDS.items():
        try:
            online = get_online_guild_members(guild_name)
            count = len(online) if online else 0
            GUILD_METRICS[guild_name] = {
                'online_members': count,
                'world': world
            }
            total_online += count
            METRICS['api_calls_total'] += 1
        except Exception:
            METRICS['api_errors_total'] += 1
            GUILD_METRICS[guild_name] = {
                'online_members': 0,
                'world': world
            }

    METRICS['enemies_online'] = total_online
    METRICS['last_check_timestamp'] = time.time()
    METRICS['last_check_duration_seconds'] = time.time() - start_time


def format_prometheus_metrics():
    """Format metrics in Prometheus exposition format."""
    lines = []

    # Help and type declarations
    lines.append('# HELP tibia_trolls_total Total number of players in trolls list')
    lines.append('# TYPE tibia_trolls_total gauge')
    lines.append(f'tibia_trolls_total {METRICS["trolls_total"]}')

    lines.append('# HELP tibia_bastex_total Total number of players in bastex list')
    lines.append('# TYPE tibia_bastex_total gauge')
    lines.append(f'tibia_bastex_total {METRICS["bastex_total"]}')

    lines.append('# HELP tibia_enemies_online Current number of enemies online')
    lines.append('# TYPE tibia_enemies_online gauge')
    lines.append(f'tibia_enemies_online {METRICS["enemies_online"]}')

    lines.append('# HELP tibia_api_calls_total Total API calls made')
    lines.append('# TYPE tibia_api_calls_total counter')
    lines.append(f'tibia_api_calls_total {METRICS["api_calls_total"]}')

    lines.append('# HELP tibia_api_errors_total Total API errors')
    lines.append('# TYPE tibia_api_errors_total counter')
    lines.append(f'tibia_api_errors_total {METRICS["api_errors_total"]}')

    lines.append('# HELP tibia_last_check_timestamp Unix timestamp of last check')
    lines.append('# TYPE tibia_last_check_timestamp gauge')
    lines.append(f'tibia_last_check_timestamp {METRICS["last_check_timestamp"]}')

    lines.append('# HELP tibia_last_check_duration_seconds Duration of last check')
    lines.append('# TYPE tibia_last_check_duration_seconds gauge')
    lines.append(f'tibia_last_check_duration_seconds {METRICS["last_check_duration_seconds"]:.3f}')

    lines.append('# HELP tibia_worlds_monitored Number of worlds being monitored')
    lines.append('# TYPE tibia_worlds_monitored gauge')
    lines.append(f'tibia_worlds_monitored {METRICS["worlds_monitored"]}')

    lines.append('# HELP tibia_guilds_monitored Number of enemy guilds being monitored')
    lines.append('# TYPE tibia_guilds_monitored gauge')
    lines.append(f'tibia_guilds_monitored {METRICS["guilds_monitored"]}')

    # Per-guild metrics
    lines.append('# HELP tibia_guild_online_members Online members per enemy guild')
    lines.append('# TYPE tibia_guild_online_members gauge')
    for guild_name, data in GUILD_METRICS.items():
        safe_name = guild_name.replace(' ', '_').replace('"', '')
        lines.append(
            f'tibia_guild_online_members{{guild="{safe_name}",world="{data["world"]}"}} '
            f'{data["online_members"]}'
        )

    return '\n'.join(lines) + '\n'


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint."""

    def do_GET(self):
        if self.path == '/metrics':
            # Update metrics on each scrape
            update_metrics()
            content = format_prometheus_metrics()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def run_server(port=8000):
    """Run the metrics server."""
    server = HTTPServer(('0.0.0.0', port), MetricsHandler)  # nosec B104
    print(f"Prometheus metrics server running on port {port}")
    print(f"Metrics available at http://localhost:{port}/metrics")
    print(f"Health check at http://localhost:{port}/health")
    server.serve_forever()


if __name__ == '__main__':
    port = int(os.environ.get('METRICS_PORT', 8000))
    run_server(port)
