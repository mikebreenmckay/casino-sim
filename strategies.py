"""
Strategy implementations for Ultimate Texas Hold'em.

Each strategy must implement:
    preflop_action(player_cards) -> 'check' | 'bet3' | 'bet4'
    flop_action(player_cards, flop)   -> 'check' | 'bet2'
    river_action(player_cards, community) -> 'fold' | 'bet1'
    side_bets(ante) -> dict  e.g. {'trips': 1.0, 'progressive': 1.0}

Included strategies
───────────────────
  AlwaysFoldStrategy    – fold every river (worst case baseline)
  AlwaysBet4Strategy    – always raise 4x preflop (no logic)
  BasicOptimalStrategy  – close approximation of published optimal UTH strategy
  CustomStrategy        – build your own by subclassing StrategyBase
"""
from __future__ import annotations
from collections import Counter
from typing import List, Dict
from cards import Card, HandRank, RANK_VAL, best_5_from


# ─────────────────────── helpers ────────────────────────────────────────────

def _rank_val(c: Card) -> int:
    return c.value

def _counts(cards: List[Card]) -> Counter:
    return Counter(c.value for c in cards)

def _has_pair_or_better(cards: List[Card]) -> bool:
    r, _ = best_5_from(cards)
    return r >= HandRank.ONE_PAIR

def _has_flush_draw(hole: List[Card], community: List[Card]) -> bool:
    """4 cards of same suit among hole + community."""
    from collections import Counter
    suits = Counter(c.suit for c in hole + community)
    return any(v >= 4 for v in suits.values())

def _has_open_straight_draw(hole: List[Card], community: List[Card]) -> bool:
    """8-out open-ended straight draw in hole + community."""
    vals = sorted(set(c.value for c in hole + community))
    for i in range(len(vals) - 3):
        window = vals[i:i+4]
        if window[-1] - window[0] == 3:
            return True
    return False


# ─────────────────────── base class ─────────────────────────────────────────

class StrategyBase:
    """Override any method to customise behaviour."""
    name: str = "Base"

    def side_bets(self, ante: float) -> Dict[str, float]:
        return {}

    def preflop_action(self, player_cards: List[Card]) -> str:
        raise NotImplementedError

    def flop_action(self, player_cards: List[Card], flop: List[Card]) -> str:
        raise NotImplementedError

    def river_action(self, player_cards: List[Card], community: List[Card]) -> str:
        raise NotImplementedError


# ─────────────────────── trivial baselines ──────────────────────────────────

class AlwaysFoldStrategy(StrategyBase):
    """Always fold at the river. Shows worst-case cost of never betting."""
    name = "Always Fold"

    def preflop_action(self, player_cards):
        return 'check'

    def flop_action(self, player_cards, flop):
        return 'check'

    def river_action(self, player_cards, community):
        return 'fold'


class AlwaysBet4Strategy(StrategyBase):
    """Always bet 4× preflop regardless of cards. Pure aggression baseline."""
    name = "Always Bet 4×"

    def preflop_action(self, player_cards):
        return 'bet4'

    def flop_action(self, player_cards, flop):   # never reached if preflop bet
        return 'check'

    def river_action(self, player_cards, community):
        return 'bet1'


class AlwaysBet1Strategy(StrategyBase):
    """Always check through to river, then always bet 1×."""
    name = "Always Bet 1×"

    def preflop_action(self, player_cards):
        return 'check'

    def flop_action(self, player_cards, flop):
        return 'check'

    def river_action(self, player_cards, community):
        return 'bet1'


# ─────────────────────── basic optimal strategy ─────────────────────────────

class BasicOptimalStrategy(StrategyBase):
    """
    Approximates the published optimal strategy for Ultimate Texas Hold'em.

    Preflop – bet 4× with:
      • Pair of 3s or better
      • Any ace
      • K-2 suited or K-3 offsuit and better
      • Q-6 suited or Q-8 offsuit and better
      • J-8 suited, J-T offsuit and better
    Bet 3× with any of the above not qualifying for 4×? (Rule simplification:
      we use 4× for the strong preflop list and 3× for a secondary list.)
    Actually the published rule uses 4× only; 3× is equivalent in many sources.
    We implement: 4× for the list above, else check.

    Flop – bet 2× with:
      • Two pair or better (using 5 cards)
      • Hidden pair (hole cards pair up with board)
      • Four to a flush with at least one hole card
      • Open-ended straight draw with at least one hole card

    River – bet 1× with:
      • Any pair or better in the 7 cards
      • Four cards to a flush (with at least one hole card)
    Fold otherwise.
    """
    name = "Basic Optimal"

    # ── Preflop ──────────────────────────────────────────────────────────────
    def preflop_action(self, player_cards: List[Card]) -> str:
        h = sorted(player_cards, key=_rank_val, reverse=True)
        high, low = h[0], h[1]
        suited = high.suit == low.suit
        hv, lv = high.value, low.value

        # Any pair 33 or better
        if hv == lv and hv >= 3:
            return 'bet4'

        # Any ace
        if hv == 14:
            return 'bet4'

        # King combos
        if hv == 13:
            if suited and lv >= 2:   # K2s+
                return 'bet4'
            if not suited and lv >= 3:  # K3o+
                return 'bet4'

        # Queen combos
        if hv == 12:
            if suited and lv >= 6:    # Q6s+
                return 'bet4'
            if not suited and lv >= 8:  # Q8o+
                return 'bet4'

        # Jack combos
        if hv == 11:
            if suited and lv >= 8:    # J8s+
                return 'bet4'
            if not suited and lv >= 10:  # JTo+
                return 'bet4'

        return 'check'

    # ── Flop ─────────────────────────────────────────────────────────────────
    def flop_action(self, player_cards: List[Card], flop: List[Card]) -> str:
        all5 = player_cards + flop
        rank, _ = best_5_from(all5)

        # Two pair or better
        if rank >= HandRank.TWO_PAIR:
            return 'bet2'

        # Hidden pair: at least one hole card value appears on flop
        flop_vals = {c.value for c in flop}
        for c in player_cards:
            if c.value in flop_vals:
                return 'bet2'

        # Four-flush draw with at least one hole card contributing
        from collections import Counter
        suits = Counter(c.suit for c in all5)
        if max(suits.values()) >= 4:
            # confirm a hole card is part of the flush suit
            flush_suit = max(suits, key=suits.get)
            if any(c.suit == flush_suit for c in player_cards):
                return 'bet2'

        # Open-ended straight draw
        if _has_open_straight_draw(player_cards, flop):
            return 'bet2'

        return 'check'

    # ── River ─────────────────────────────────────────────────────────────────
    def river_action(self, player_cards: List[Card], community: List[Card]) -> str:
        all7 = player_cards + community
        rank, _ = best_5_from(all7)

        if rank >= HandRank.ONE_PAIR:
            return 'bet1'

        # Four-flush draw (might still have outs, but we bet even without hitting
        # only if we have a pair; otherwise fold without the pair)
        # Standard rule: fold without at least a pair
        return 'fold'


# ─────────────────────── trips side-bet overlay ─────────────────────────────

class WithTripsMixin:
    """Mix into any strategy to also place the Trips side bet."""
    trips_unit: float = 1.0   # trips bet as a fraction/multiple of ante

    def side_bets(self, ante: float) -> Dict[str, float]:
        base = super().side_bets(ante) if hasattr(super(), 'side_bets') else {}
        base['trips'] = ante * self.trips_unit
        return base


class OptimalWithTrips(WithTripsMixin, BasicOptimalStrategy):
    name = "Basic Optimal + Trips"


# ─────────────────────── custom strategy scaffold ────────────────────────────

class CustomStrategy(StrategyBase):
    """
    Template for writing your own strategy.
    Edit the methods below with your logic.
    """
    name = "Custom"

    def side_bets(self, ante: float) -> Dict[str, float]:
        # Example: bet $1 trips side bet
        return {'trips': 1.0}

    def preflop_action(self, player_cards: List[Card]) -> str:
        # Example: bet 4× with any ace or pair
        vals = [c.value for c in player_cards]
        if 14 in vals or vals[0] == vals[1]:
            return 'bet4'
        return 'check'

    def flop_action(self, player_cards: List[Card], flop: List[Card]) -> str:
        # Example: bet 2× if we have any pair or better
        rank, _ = best_5_from(player_cards + flop)
        return 'bet2' if rank >= HandRank.ONE_PAIR else 'check'

    def river_action(self, player_cards: List[Card], community: List[Card]) -> str:
        # Example: bet 1× with pair or better, else fold
        rank, _ = best_5_from(player_cards + community)
        return 'bet1' if rank >= HandRank.ONE_PAIR else 'fold'


# ─────────────────────── registry ────────────────────────────────────────────

STRATEGIES = {
    'always_fold':    AlwaysFoldStrategy,
    'always_bet4':    AlwaysBet4Strategy,
    'always_bet1':    AlwaysBet1Strategy,
    'basic_optimal':  BasicOptimalStrategy,
    'optimal_trips':  OptimalWithTrips,
    'custom':         CustomStrategy,
}
