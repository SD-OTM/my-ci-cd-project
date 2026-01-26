#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Price Diff Generator - Final Version
Compares stock prices between the last two commits
Saves output to artifacts folder
"""
import os
import subprocess
import re
from datetime import datetime


def get_last_two_commits():
    """Get the hash of the last two commits"""
    result = subprocess.run(
        ["git", "log", "-2", "--pretty=format:%H"],
        capture_output=True,
        text=True
    )
    commits = result.stdout.strip().split('\n')
    if len(commits) < 2:
        return None, None
    return commits[0], commits[1]  # current, previous


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


def calculate_percentage_change(old_price, new_price):
    """Calculate percentage change between two prices"""
    if old_price is None or old_price == 0:
        return 0
    return ((new_price - old_price) / old_price) * 100


def generate_diff_report():
    """Generate detailed diff report for all stocks"""

    # Create artifacts directory if it doesn't exist
    os.makedirs('artifacts', exist_ok=True)

    current_commit, previous_commit = get_last_two_commits()

    if not current_commit or not previous_commit:
        print("Error: Not enough commits to compare")
        return

    print(f"Comparing commits:")
    print(f"  Current:  {current_commit[:8]}")
    print(f"  Previous: {previous_commit[:8]}")

    stock_files = get_all_stock_files()

    if not stock_files:
        print("No stock files found")
        return

    changes = []

    for filepath in stock_files:
        # Get ticker name from filename
        ticker = os.path.basename(filepath).replace('.txt', '')

        # Get content from both commits
        current_content = get_file_content(current_commit, filepath)
        previous_content = get_file_content(previous_commit, filepath)

        # Parse prices
        current_price, current_time = parse_price_file(current_content)
        previous_price, previous_time = parse_price_file(previous_content)

        if current_price is not None and previous_price is not None:
            price_change = current_price - previous_price
            percent_change = calculate_percentage_change(previous_price, current_price)

            changes.append({
                'ticker': ticker,
                'previous_price': previous_price,
                'current_price': current_price,
                'price_change': price_change,
                'percent_change': percent_change,
                'previous_time': previous_time,
                'current_time': current_time
            })

    # Sort by absolute percentage change (biggest movers first)
    changes.sort(key=lambda x: abs(x['percent_change']), reverse=True)

    # Write diff report to artifacts folder
    output_file = os.path.join('artifacts', 'changes.diff')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("STOCK PRICE CHANGES REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Previous Update: {changes[0]['previous_time'] if changes else 'N/A'}\n")
        f.write(f"Current Update:  {changes[0]['current_time'] if changes else 'N/A'}\n")
        f.write(f"Total Stocks:    {len(changes)}\n")
        f.write("=" * 80 + "\n\n")

        # Summary statistics
        gainers = [c for c in changes if c['percent_change'] > 0]
        losers = [c for c in changes if c['percent_change'] < 0]
        unchanged = [c for c in changes if c['percent_change'] == 0]

        f.write("SUMMARY:\n")
        f.write(f"  Gainers:   {len(gainers)} stocks\n")
        f.write(f"  Losers:    {len(losers)} stocks\n")
        f.write(f"  Unchanged: {len(unchanged)} stocks\n")
        f.write("\n" + "=" * 80 + "\n\n")

        # Top 10 gainers
        f.write("TOP 10 GAINERS:\n")
        f.write("-" * 80 + "\n")
        for i, stock in enumerate(gainers[:10], 1):
            sign = "+"
            f.write(f"{i:2d}. {stock['ticker']:6s} {sign}{stock['percent_change']:6.2f}%  "
                    f"New: ${stock['current_price']:8.2f}  "
                    f"Last: ${stock['previous_price']:8.2f}\n")

        f.write("\n")

        # Top 10 losers
        f.write("TOP 10 LOSERS:\n")
        f.write("-" * 80 + "\n")
        for i, stock in enumerate(losers[:10], 1):
            sign = "-" if stock['percent_change'] < 0 else ""
            f.write(f"{i:2d}. {stock['ticker']:6s} {stock['percent_change']:7.2f}%  "
                    f"New: ${stock['current_price']:8.2f}  "
                    f"Last: ${stock['previous_price']:8.2f}\n")

        f.write("\n" + "=" * 80 + "\n\n")

        # Detailed list of all changes
        f.write("DETAILED CHANGES (All Stocks):\n")
        f.write("-" * 80 + "\n")

        for stock in changes:
            sign = "+" if stock['percent_change'] >= 0 else ""
            f.write(f"{stock['ticker']:6s} {sign}{stock['percent_change']:7.2f}%  "
                    f"New: ${stock['current_price']:8.2f}  "
                    f"Last: ${stock['previous_price']:8.2f}  "
                    f"Change: ${stock['price_change']:+8.2f}\n")

    print(f"\nDiff report generated: {output_file}")
    print(f"Total stocks analyzed: {len(changes)}")
    print(f"Gainers: {len(gainers)} | Losers: {len(losers)} | Unchanged: {len(unchanged)}")


if __name__ == "__main__":
    import sys

    # If running from PyCharm, change to the Git repo directory
    if len(sys.argv) > 1:
        repo_path = sys.argv[1]
        print(f"Changing to repository: {repo_path}")
        os.chdir(repo_path)

    # Check if we're in a Git repository
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("Error: Not in a Git repository!")
        print("Usage when testing:")
        print('  python generate_diff.py "C:\\Users\\NITRO\\Documents\\Git\\my-ci-cd-project"')
        sys.exit(1)

    generate_diff_report()