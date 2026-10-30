#!/usr/bin/env python3
"""
Ultimate Texas Hold'em Strategy Simulator
==========================================
Run this file directly to see a strategy comparison demo.

Usage examples:
  python main.py                     # run default comparison
  python main.py --hands 500000      # more hands for tighter estimates
  python main.py --strategy basic_optimal --verbose --hands 20
  python main.py --list-strategies

Available strategies (use with --strategy):
  always_fold   always_bet4  always_bet1
  basic_optimal  optimal_trips  custom
"""
import argparse
import sys
import os

# Make sure imports work from any directory
sys.path.insert(0, os.path.dirname(__file__))

from strategies import STRATEGIES, BasicOptimalStrategy, AlwaysBet4Strategy, AlwaysBet1Strategy, AlwaysFoldStrategy, OptimalWithTrips
from simulator import run_simulation, compare_strategies


def demo_comparison(num_hands: int):
    """Run all main strategies head-to-head."""
    strategies = [
        AlwaysFoldStrategy(),
        AlwaysBet1Strategy(),
        AlwaysBet4Strategy(),
        BasicOptimalStrategy(),
        OptimalWithTrips(),
    ]
    results = compare_strategies(strategies, num_hands=num_hands, ante=10.0)

    # Print full report for the best strategy
    print("\n── Full report: Basic Optimal ─────────────────────────────────────")
    print(results['Basic Optimal'].report())


def demo_verbose(strategy_key: str, num_hands: int):
    """Show hand-by-hand output for a small number of hands."""
    cls = STRATEGIES.get(strategy_key)
    if cls is None:
        print(f"Unknown strategy '{strategy_key}'. Use --list-strategies.")
        sys.exit(1)
    strat = cls()
    print(f"\n=== Verbose demo: {strat.name} ===\n")
    stats = run_simulation(
        strat,
        num_hands=num_hands,
        ante=10.0,
        verbose=True,
        verbose_every=1,
    )
    print("\n" + stats.report())


def main():
    parser = argparse.ArgumentParser(
        description="Ultimate Texas Hold'em Strategy Simulator"
    )
    parser.add_argument('--hands', type=int, default=100_000,
                        help='Number of hands to simulate (default: 100000)')
    parser.add_argument('--strategy', type=str, default=None,
                        help='Run a single strategy (see --list-strategies)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print each hand (use with small --hands)')
    parser.add_argument('--list-strategies', action='store_true',
                        help='List available strategy keys and exit')
    args = parser.parse_args()

    if args.list_strategies:
        print("Available strategies:")
        for key, cls in STRATEGIES.items():
            print(f"  {key:<20} → {cls.name}")
        sys.exit(0)

    if args.strategy:
        demo_verbose(args.strategy, args.hands)
    else:
        demo_comparison(args.hands)


if __name__ == '__main__':
    main()
