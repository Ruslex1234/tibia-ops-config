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
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

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

# (metric key, prometheus type, help text) - drives the exposition format
METRIC_DEFINITIONS = [
    ('trolls_total', 'gauge', 'Total number of players in trolls list'),
    ('bastex_total', 'gauge', 'Total number of players in bastex list'),
    ('enemies_online', 'gauge', 'Current number of enemies online'),
    ('api_calls_total', 'counter', 'Total API calls made'),
    ('api_errors_total', 'counter', 'Total API errors'),
    ('last_check_timestamp', 'gauge', 'Unix timestamp of last check'),
    ('last_check_duration_seconds', 'gauge', 'Duration of last check'),
    ('worlds_monitored', 'gauge', 'Number of worlds being monitored'),
    ('guilds_monitored', 'gauge', 'Number of enemy guilds being monitored'),
]


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

    for key, metric_type, help_text in METRIC_DEFINITIONS:
        value = METRICS[key]
        if key == 'last_check_duration_seconds':
            value = f'{value:.3f}'
        lines.append(f'# HELP tibia_{key} {help_text}')
        lines.append(f'# TYPE tibia_{key} {metric_type}')
        lines.append(f'tibia_{key} {value}')

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
            body = format_prometheus_metrics().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', '2')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def run_server(port=8000):
    """Run the metrics server (threaded so /health stays responsive during scrapes)."""
    server = ThreadingHTTPServer(('0.0.0.0', port), MetricsHandler)  # nosec B104
    print(f"Prometheus metrics server running on port {port}")
    print(f"Metrics available at http://localhost:{port}/metrics")
    print(f"Health check at http://localhost:{port}/health")
    server.serve_forever()


if __name__ == '__main__':
    port = int(os.environ.get('METRICS_PORT', 8000))
    run_server(port)
