"""
Simulation runner and statistics for Ultimate Texas Hold'em strategies.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import Counter

from uth_game import UltimateTHGame, HandResult
from cards import HandRank, hand_name


@dataclass
class SimStats:
    """Accumulated statistics over a simulation run."""
    strategy_name: str
    num_hands: int = 0
    total_wagered: float = 0.0   # ante + blind + play (when placed)
    total_pnl: float = 0.0

    outcomes: Counter = field(default_factory=Counter)
    hand_ranks: Counter = field(default_factory=Counter)
    dealer_ranks: Counter = field(default_factory=Counter)
    play_stages: Counter = field(default_factory=Counter)
    folds: int = 0
    dealer_no_qualify: int = 0
    trips_hands: int = 0

    pnl_history: List[float] = field(default_factory=list)   # running bankroll

    def add(self, result: HandResult, bankroll: float):
        self.num_hands += 1
        # Total wagered = ante + blind + play_bet (only what was actually placed)
        wagered = result.ante + result.blind + result.play_bet
        wagered += result.trips_bet + result.progressive_bet
        self.total_wagered += wagered
        self.total_pnl += result.total_pnl

        self.outcomes[result.outcome] += 1
        if result.player_hand_rank:
            self.hand_ranks[result.player_hand_rank] += 1
        self.dealer_ranks[result.dealer_hand_rank] += 1
        self.play_stages[result.detail.get('play_stage', 'fold')] += 1
        if result.folded:
            self.folds += 1
        if not result.dealer_qualifies:
            self.dealer_no_qualify += 1
        if result.trips_bet > 0 and result.trips_pnl > 0:
            self.trips_hands += 1

        self.pnl_history.append(bankroll)

    @property
    def house_edge(self) -> float:
        """House edge as % of total amount wagered."""
        if self.total_wagered == 0:
            return 0.0
        return -self.total_pnl / self.total_wagered * 100

    @property
    def roi(self) -> float:
        """Return on investment (P&L / wagered)."""
        if self.total_wagered == 0:
            return 0.0
        return self.total_pnl / self.total_wagered * 100

    @property
    def avg_pnl_per_hand(self) -> float:
        if self.num_hands == 0:
            return 0.0
        return self.total_pnl / self.num_hands

    def report(self) -> str:
        lines = [
            f"{'='*60}",
            f"  Strategy : {self.strategy_name}",
            f"  Hands    : {self.num_hands:,}",
            f"{'='*60}",
            f"  Total wagered  : {self.total_wagered:>12,.2f}",
            f"  Total P&L      : {self.total_pnl:>+12,.2f}",
            f"  Avg P&L/hand   : {self.avg_pnl_per_hand:>+12,.4f}",
            f"  House edge     : {self.house_edge:>11.3f}%",
            "",
            "  Outcomes",
            f"    Player wins  : {self.outcomes['player_wins']:>8,}  "
            f"({self.outcomes['player_wins']/max(1,self.num_hands)*100:.1f}%)",
            f"    Dealer wins  : {self.outcomes['dealer_wins']:>8,}  "
            f"({self.outcomes['dealer_wins']/max(1,self.num_hands)*100:.1f}%)",
            f"    Push         : {self.outcomes['push']:>8,}  "
            f"({self.outcomes['push']/max(1,self.num_hands)*100:.1f}%)",
            f"    Folded       : {self.folds:>8,}  "
            f"({self.folds/max(1,self.num_hands)*100:.1f}%)",
            "",
            f"  Dealer no-qualify : {self.dealer_no_qualify:,}  "
            f"({self.dealer_no_qualify/max(1,self.num_hands)*100:.1f}%)",
            "",
            "  Bet timing",
        ]
        for stage in ('preflop', 'flop', 'river', None):
            label = stage if stage else 'fold'
            cnt = self.play_stages[stage]
            pct = cnt / max(1, self.num_hands) * 100
            lines.append(f"    {label:>8} : {cnt:>8,}  ({pct:.1f}%)")

        lines.append("")
        lines.append("  Player hand distribution")
        for rank in sorted(HandRank, reverse=True):
            cnt = self.hand_ranks[rank]
            if cnt:
                pct = cnt / max(1, self.num_hands) * 100
                lines.append(f"    {hand_name(rank):>20} : {cnt:>8,}  ({pct:.2f}%)")

        lines.append(f"{'='*60}")
        return "\n".join(lines)


# ─────────────────────── simulator ──────────────────────────────────────────

def run_simulation(
    strategy,
    num_hands: int = 100_000,
    ante: float = 10.0,
    starting_bankroll: float = 10_000.0,
    verbose: bool = False,
    verbose_every: int = 10,
    progressive_jackpot: float = 100_000.0,
) -> SimStats:
    """
    Run *num_hands* of Ultimate Texas Hold'em with the given strategy.

    Parameters
    ----------
    strategy        : strategy instance (see strategies.py)
    num_hands       : number of hands to simulate
    ante            : ante amount per hand (blind = same)
    starting_bankroll : initial bankroll for tracking
    verbose         : print each hand result
    verbose_every   : print every N-th hand when verbose=True
    """
    game = UltimateTHGame(progressive_jackpot=progressive_jackpot)
    stats = SimStats(strategy_name=strategy.name)
    bankroll = starting_bankroll

    t0 = time.perf_counter()
    for i in range(num_hands):
        result = game.play_hand(ante, strategy)
        bankroll += result.total_pnl
        stats.add(result, bankroll)

        if verbose and (i % verbose_every == 0):
            print(f"\n--- Hand {i+1} ---")
            print(result)

    elapsed = time.perf_counter() - t0
    if not verbose:
        print(f"  [{strategy.name}] {num_hands:,} hands in {elapsed:.2f}s  "
              f"| P&L: {stats.total_pnl:+,.2f}  "
              f"| Edge: {stats.house_edge:.3f}%")
    return stats


def compare_strategies(
    strategies: list,
    num_hands: int = 100_000,
    ante: float = 10.0,
) -> Dict[str, SimStats]:
    """
    Run the same number of hands for each strategy and print a comparison table.
    """
    results: Dict[str, SimStats] = {}
    print(f"\nComparing {len(strategies)} strategies over {num_hands:,} hands "
          f"(ante={ante})...\n")
    for strat in strategies:
        stats = run_simulation(strat, num_hands=num_hands, ante=ante)
        results[strat.name] = stats

    # Summary table
    print(f"\n{'Strategy':<25} {'Win%':>6} {'Fold%':>6} {'House Edge':>11} {'Avg P&L/hand':>13}")
    print("-" * 65)
    for name, s in results.items():
        win_pct  = s.outcomes['player_wins'] / max(1, s.num_hands) * 100
        fold_pct = s.folds / max(1, s.num_hands) * 100
        print(f"{name:<25} {win_pct:>5.1f}% {fold_pct:>5.1f}%  "
              f"{s.house_edge:>10.3f}%  {s.avg_pnl_per_hand:>+12.4f}")
    print()
    return results
