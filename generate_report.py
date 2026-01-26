#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Price HTML Report Generator - Final Version
Creates interactive HTML report with charts and statistics
Saves output to artifacts folder
"""
import os
import subprocess
import json
from datetime import datetime


def get_commit_history(max_commits=10):
    """Get the last N commits with their timestamps"""
    result = subprocess.run(
        ["git", "log", f"-{max_commits}", "--pretty=format:%H|%ai"],
        capture_output=True,
        text=True
    )

    commits = []
    for line in result.stdout.strip().split('\n'):
        if '|' in line:
            commit_hash, timestamp = line.split('|')
            commits.append({'hash': commit_hash, 'timestamp': timestamp})

    return commits


def get_file_content(commit_hash, filepath):
    """Get file content from a specific commit"""
    try:
        result = subprocess.run(
            ["git", "show", f"{commit_hash}:{filepath}"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def parse_price_file(content):
    """Parse price and timestamp from file content"""
    if not content:
        return None, None

    lines = content.split('\n')
    price = None
    timestamp = None

    for line in lines:
        if line.startswith('Price:'):
            price_str = line.replace('Price:', '').strip()
            try:
                price = float(price_str)
            except ValueError:
                pass
        elif line.startswith('Updated:'):
            timestamp = line.replace('Updated:', '').strip()

    return price, timestamp


def get_all_stock_files():
    """Get list of all stock .txt files in the repo"""
    result = subprocess.run(
        ["git", "ls-files", "*.txt"],
        capture_output=True,
        text=True
    )
    files = [f for f in result.stdout.strip().split('\n') if f and f != 'main.txt']
    return files


def get_price_history(ticker, commits):
    """Get price history for a ticker across commits"""
    filepath = f"{ticker}.txt"
    history = []

    for commit in commits:
        content = get_file_content(commit['hash'], filepath)
        price, timestamp = parse_price_file(content)

        if price is not None:
            history.append({
                'timestamp': timestamp or commit['timestamp'],
                'price': price
            })

    return history


def calculate_statistics(history):
    """Calculate statistics from price history"""
    if not history:
        return None

    prices = [h['price'] for h in history]

    current_price = prices[0]
    previous_price = prices[1] if len(prices) > 1 else current_price
    min_price = min(prices)
    max_price = max(prices)
    avg_price = sum(prices) / len(prices)

    price_change = current_price - previous_price
    percent_change = ((current_price - previous_price) / previous_price * 100) if previous_price != 0 else 0

    return {
        'current': current_price,
        'previous': previous_price,
        'min': min_price,
        'max': max_price,
        'avg': avg_price,
        'change': price_change,
        'percent_change': percent_change
    }


def generate_html_report():
    """Generate comprehensive HTML report with charts"""

    # Create artifacts directory if it doesn't exist
    os.makedirs('artifacts', exist_ok=True)

    print("Generating HTML report...")

    # Get commit history
    commits = get_commit_history(max_commits=10)

    if not commits:
        print("No commits found")
        return

    # Get all stock files
    stock_files = get_all_stock_files()

    if not stock_files:
        print("No stock files found")
        return

    # Sample top 20 stocks for charts (to keep HTML manageable)
    tickers = [os.path.basename(f).replace('.txt', '') for f in stock_files[:20]]

    # Collect data for all stocks
    all_stocks_data = []
    chart_data = {}

    print(f"Processing {len(tickers)} stocks for charts...")

    for ticker in tickers:
        history = get_price_history(ticker, commits)
        stats = calculate_statistics(history)

        if stats:
            all_stocks_data.append({
                'ticker': ticker,
                'stats': stats,
                'history': history
            })

            # Prepare chart data (reverse to show oldest to newest)
            chart_data[ticker] = {
                'labels': [h['timestamp'][:16] for h in reversed(history)],  # timestamp without seconds
                'prices': [h['price'] for h in reversed(history)]
            }

    # Sort by absolute percent change
    all_stocks_data.sort(key=lambda x: abs(x['stats']['percent_change']), reverse=True)

    # Count gainers/losers for all stocks
    all_tickers = [os.path.basename(f).replace('.txt', '') for f in stock_files]
    total_stats = {'gainers': 0, 'losers': 0, 'unchanged': 0}

    for ticker in all_tickers:
        history = get_price_history(ticker, commits[:2])  # Just last 2 commits
        stats = calculate_statistics(history)
        if stats:
            if stats['percent_change'] > 0:
                total_stats['gainers'] += 1
            elif stats['percent_change'] < 0:
                total_stats['losers'] += 1
            else:
                total_stats['unchanged'] += 1

    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Price Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}

        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}

        .stat-card h3 {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .stat-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}

        .stat-card.gainers .value {{
            color: #10b981;
        }}

        .stat-card.losers .value {{
            color: #ef4444;
        }}

        .content {{
            padding: 30px;
        }}

        .section {{
            margin-bottom: 40px;
        }}

        .section h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}

        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            margin-top: 20px;
        }}

        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        .chart-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }}

        .chart-stats {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 15px;
            font-size: 0.9em;
        }}

        .price-change {{
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }}

        .price-change.positive {{
            background: #d1fae5;
            color: #065f46;
        }}

        .price-change.negative {{
            background: #fee2e2;
            color: #991b1b;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}

        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e5e7eb;
        }}

        tr:hover {{
            background: #f9fafb;
        }}

        .positive {{
            color: #10b981;
            font-weight: bold;
        }}

        .negative {{
            color: #ef4444;
            font-weight: bold;
        }}

        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 Stock Price Report</h1>
            <p>S&P 500 Price Movement Analysis</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Stocks</h3>
                <div class="value">{len(all_tickers)}</div>
            </div>
            <div class="stat-card gainers">
                <h3>Gainers</h3>
                <div class="value">{total_stats['gainers']}</div>
            </div>
            <div class="stat-card losers">
                <h3>Losers</h3>
                <div class="value">{total_stats['losers']}</div>
            </div>
            <div class="stat-card">
                <h3>Unchanged</h3>
                <div class="value">{total_stats['unchanged']}</div>
            </div>
        </div>

        <div class="content">
            <div class="section">
                <h2>📊 Price Charts - Top Movers</h2>
                <div class="charts-grid">
"""

    # Add charts for top stocks
    for stock in all_stocks_data[:12]:  # Top 12 charts
        ticker = stock['ticker']
        stats = stock['stats']

        change_class = 'positive' if stats['percent_change'] >= 0 else 'negative'
        change_sign = '+' if stats['percent_change'] >= 0 else ''

        html_content += f"""
                    <div class="chart-container">
                        <div class="chart-title">{ticker}</div>
                        <div class="chart-stats">
                            <span>Current: ${stats['current']:.2f}</span>
                            <span class="price-change {change_class}">
                                {change_sign}{stats['percent_change']:.2f}%
                            </span>
                        </div>
                        <canvas id="chart_{ticker}"></canvas>
                    </div>
"""

    html_content += """
                </div>
            </div>

            <div class="section">
                <h2>📋 Top Movers Summary</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Ticker</th>
                            <th>Current Price</th>
                            <th>Previous Price</th>
                            <th>Change</th>
                            <th>% Change</th>
                            <th>Min</th>
                            <th>Max</th>
                            <th>Avg</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    # Add table rows
    for stock in all_stocks_data[:20]:  # Top 20 in table
        ticker = stock['ticker']
        stats = stock['stats']
        change_class = 'positive' if stats['percent_change'] >= 0 else 'negative'
        change_sign = '+' if stats['change'] >= 0 else ''
        percent_sign = '+' if stats['percent_change'] >= 0 else ''

        html_content += f"""
                        <tr>
                            <td><strong>{ticker}</strong></td>
                            <td>${stats['current']:.2f}</td>
                            <td>${stats['previous']:.2f}</td>
                            <td class="{change_class}">{change_sign}${stats['change']:.2f}</td>
                            <td class="{change_class}">{percent_sign}{stats['percent_change']:.2f}%</td>
                            <td>${stats['min']:.2f}</td>
                            <td>${stats['max']:.2f}</td>
                            <td>${stats['avg']:.2f}</td>
                        </tr>
"""

    html_content += """
                    </tbody>
                </table>
            </div>
        </div>

        <div class="footer">
            <p>Generated by Jenkins CI/CD Pipeline | Data from Yahoo Finance</p>
        </div>
    </div>

    <script>
        // Chart.js configuration
        const chartConfig = {
            type: 'line',
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toFixed(2);
                            }
                        }
                    },
                    x: {
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            }
        };

        // Chart data
        const chartData = """ + json.dumps(chart_data) + """;

        // Create charts
        Object.keys(chartData).forEach(ticker => {
            const ctx = document.getElementById('chart_' + ticker);
            if (ctx) {
                new Chart(ctx, {
                    ...chartConfig,
                    data: {
                        labels: chartData[ticker].labels,
                        datasets: [{
                            label: 'Price',
                            data: chartData[ticker].prices,
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            borderWidth: 2,
                            tension: 0.4,
                            fill: true
                        }]
                    }
                });
            }
        });
    </script>
</body>
</html>
"""

    # Write HTML file to artifacts folder
    output_file = os.path.join('artifacts', 'report.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML report generated: {output_file}")
    print(f"Charts created for {len(all_stocks_data[:12])} stocks")
    print(f"Table includes {len(all_stocks_data[:20])} stocks")


if __name__ == "__main__":
    generate_html_report()