import json
import os
from collections import Counter
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

ALERTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'alerts', 'ids_log.json')
PER_PAGE = 25


def load_alerts():
    """Load alerts from the JSON log file. Each line is a JSON object."""
    alerts = []
    try:
        with open(ALERTS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        alerts.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        pass
    # Sort by timestamp descending (newest first)
    alerts.sort(key=lambda a: a.get('timestamp', ''), reverse=True)
    return alerts


@app.route('/')
def dashboard():
    alerts = load_alerts()
    total = len(alerts)

    # Severity breakdown
    severity_counts = Counter(a.get('severity', 'UNKNOWN') for a in alerts)
    high = severity_counts.get('HIGH', 0)
    medium = severity_counts.get('MEDIUM', 0)
    low = severity_counts.get('LOW', 0)

    # Attack type breakdown
    attack_counts = Counter(a.get('attack_type', 'Unknown') for a in alerts)

    # Latest 20 alerts
    latest = alerts[:20]

    # Timeline data — group alerts by minute
    timeline = {}
    for a in alerts:
        ts = a.get('timestamp', '')
        try:
            minute = ts[:16]  # "2026-03-22T11:12"
            timeline[minute] = timeline.get(minute, 0) + 1
        except Exception:
            continue
    sorted_timeline = sorted(timeline.items())

    return render_template('dashboard.html',
                           total=total,
                           high=high, medium=medium, low=low,
                           attack_counts=dict(attack_counts),
                           latest=latest,
                           timeline_labels=[t[0] for t in sorted_timeline],
                           timeline_data=[t[1] for t in sorted_timeline])


@app.route('/api/dashboard')
def api_dashboard():
    alerts = load_alerts()
    total = len(alerts)
    severity_counts = Counter(a.get('severity', 'UNKNOWN') for a in alerts)
    attack_counts = Counter(a.get('attack_type', 'Unknown') for a in alerts)
    latest = alerts[:20]

    timeline = {}
    for a in alerts:
        ts = a.get('timestamp', '')
        try:
            minute = ts[:16]
            timeline[minute] = timeline.get(minute, 0) + 1
        except Exception:
            continue
    sorted_timeline = sorted(timeline.items())

    return jsonify({
        'total': total,
        'high': severity_counts.get('HIGH', 0),
        'medium': severity_counts.get('MEDIUM', 0),
        'low': severity_counts.get('LOW', 0),
        'attack_counts': dict(attack_counts),
        'latest': latest,
        'timeline_labels': [t[0] for t in sorted_timeline],
        'timeline_data': [t[1] for t in sorted_timeline],
    })


@app.route('/alerts')
def alerts_page():
    alerts = load_alerts()

    # Filters
    search = request.args.get('search', '').strip()
    attack_type = request.args.get('attack_type', '')
    severity = request.args.get('severity', '')
    protocol = request.args.get('protocol', '')

    if attack_type:
        alerts = [a for a in alerts if a.get('attack_type') == attack_type]
    if severity:
        alerts = [a for a in alerts if a.get('severity') == severity]
    if protocol:
        alerts = [a for a in alerts if a.get('protocol') == protocol]
    if search:
        search_lower = search.lower()
        alerts = [a for a in alerts if
                  search_lower in a.get('src_ip', '').lower() or
                  search_lower in a.get('dst_ip', '').lower() or
                  search_lower in a.get('attack_type', '').lower() or
                  search_lower in str(a.get('src_port', '')) or
                  search_lower in str(a.get('dst_port', ''))]

    # Pagination
    page = request.args.get('page', 1, type=int)
    total = len(alerts)
    total_pages = max(1, (total + PER_PAGE - 1) // PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * PER_PAGE
    paginated = alerts[start:start + PER_PAGE]

    # Collect unique values for filter dropdowns
    all_alerts = load_alerts()
    attack_types = sorted(set(a.get('attack_type', '') for a in all_alerts))
    severities = ['HIGH', 'MEDIUM', 'LOW']
    protocols = sorted(set(a.get('protocol', '') for a in all_alerts))

    return render_template('alerts.html',
                           alerts=paginated,
                           page=page,
                           total_pages=total_pages,
                           total=total,
                           search=search,
                           attack_type=attack_type,
                           severity=severity,
                           protocol=protocol,
                           attack_types=attack_types,
                           severities=severities,
                           protocols=protocols)


@app.route('/stats')
def stats_page():
    alerts = load_alerts()

    # Top 10 source IPs
    src_ips = Counter(a.get('src_ip', '') for a in alerts).most_common(10)
    # Top 10 destination IPs
    dst_ips = Counter(a.get('dst_ip', '') for a in alerts).most_common(10)
    # Top 10 targeted ports
    dst_ports = Counter(a.get('dst_port', 0) for a in alerts).most_common(10)
    # Attack type distribution
    attack_dist = Counter(a.get('attack_type', '') for a in alerts)

    return render_template('stats.html',
                           src_ip_labels=[x[0] for x in src_ips],
                           src_ip_data=[x[1] for x in src_ips],
                           dst_ip_labels=[x[0] for x in dst_ips],
                           dst_ip_data=[x[1] for x in dst_ips],
                           dst_port_labels=[str(x[0]) for x in dst_ports],
                           dst_port_data=[x[1] for x in dst_ports],
                           attack_labels=list(attack_dist.keys()),
                           attack_data=list(attack_dist.values()))


@app.route('/api/stats')
def api_stats():
    alerts = load_alerts()
    src_ips = Counter(a.get('src_ip', '') for a in alerts).most_common(10)
    dst_ips = Counter(a.get('dst_ip', '') for a in alerts).most_common(10)
    dst_ports = Counter(a.get('dst_port', 0) for a in alerts).most_common(10)
    attack_dist = Counter(a.get('attack_type', '') for a in alerts)

    return jsonify({
        'src_ip_labels': [x[0] for x in src_ips],
        'src_ip_data': [x[1] for x in src_ips],
        'dst_ip_labels': [x[0] for x in dst_ips],
        'dst_ip_data': [x[1] for x in dst_ips],
        'dst_port_labels': [str(x[0]) for x in dst_ports],
        'dst_port_data': [x[1] for x in dst_ports],
        'attack_labels': list(attack_dist.keys()),
        'attack_data': list(attack_dist.values()),
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
