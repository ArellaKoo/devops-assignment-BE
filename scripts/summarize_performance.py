#!/usr/bin/env python3
"""Reconcile the original Qwen load artifacts without modifying measurements."""
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'q6-performance/query-timing-main.jsonl'

def percentile(values, q):
    ordered = sorted(values)
    point = (len(ordered) - 1) * q
    index = int(point)
    fraction = point - index
    return ordered[index] * (1 - fraction) + ordered[min(index + 1, len(ordered) - 1)] * fraction

def summary(values):
    return {k: round(v, 3) for k, v in {
        'p50': statistics.median(values), 'p95': percentile(values, .95),
        'p99': percentile(values, .99), 'max': max(values)
    }.items()}

rows = [json.loads(line) for line in SOURCE.read_text().splitlines()]
requests = [r for r in rows if r.get('type') == 'request' and r.get('path', '').endswith('/menu')]
segments = [r for r in rows if r.get('type') == 'segment' and r.get('label') == 'menu_materialize']
assert len(requests) == len(segments) == 395
assert all(r['status'] == 200 and len(r['finds']) == 3 for r in requests)
assert all([(f['collection'], f['rows']) for f in r['finds']] == [('users', 1), ('vendors', 1), ('menu_items', 3)] for r in requests)
sums = [sum(f.get('command_ms', f.get('server_ms', 0)) for f in r['finds']) for r in requests]
walls = [r['wall_ms'] for r in requests]
result = {
    'source': str(SOURCE.relative_to(ROOT)),
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'menu_requests': len(requests), 'failures': sum(r['status'] != 200 for r in requests),
    'finds_per_request': 3,
    'timing_definition': 'Historical server_ms is PyMongo duration_micros/1000: driver-observed command duration, including transport/driver overhead, not isolated MongoDB server execution time. New instrumentation calls it command_ms.',
    'sum_of_three_command_durations_ms': summary(sums),
    'api_request_wall_ms': summary(walls),
    'menu_materialization_wall_ms': summary([s['wall_ms'] for s in segments]),
    'paired_command_share_percent': summary([100 * command / wall for command, wall in zip(sums, walls)]),
    'menu_requests_with_other_commands': sum(r['other_commands'] > 0 for r in requests),
    'other_commands_total': sum(r['other_commands'] for r in requests),
    'limits': 'Small local seeded dataset, development server. No separate server profiler, no CPU attribution, no production scaling claim. Percentiles use linear interpolation; shares are paired per request.'
}
output = ROOT / 'q6-performance/reconciled-analysis.json'
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
