"""
Card engine: deck, hand evaluation for casino table game simulators.
"""
from __future__ import annotations
import random
from enum import IntEnum
from itertools import combinations
from typing import List, Tuple

# ─────────────────────────── Card primitives ────────────────────────────────

RANKS = '23456789TJQKA'
SUITS = 'cdhs'  # clubs, diamonds, hearts, spades
RANK_VAL = {r: i for i, r in enumerate(RANKS, 2)}  # 2→2 … A→14

class Card:
    __slots__ = ('rank', 'suit', 'value')

    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
        self.value = RANK_VAL[rank]

    def __repr__(self):
        return f"{self.rank}{self.suit}"

    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self):
        return hash((self.rank, self.suit))


class Deck:
    def __init__(self, num_decks: int = 1):
        self._cards = [Card(r, s) for r in RANKS for s in SUITS] * num_decks
        self.shuffle()

    def shuffle(self):
        random.shuffle(self._cards)
        self._pos = 0

    def deal(self, n: int = 1) -> List[Card]:
        cards = self._cards[self._pos:self._pos + n]
        self._pos += n
        return cards

    def remaining(self) -> int:
        return len(self._cards) - self._pos


# ─────────────────────────── Hand evaluation ────────────────────────────────

class HandRank(IntEnum):
    HIGH_CARD       = 1
    ONE_PAIR        = 2
    TWO_PAIR        = 3
    THREE_OF_A_KIND = 4
    STRAIGHT        = 5
    FLUSH           = 6
    FULL_HOUSE      = 7
    FOUR_OF_A_KIND  = 8
    STRAIGHT_FLUSH  = 9
    ROYAL_FLUSH     = 10


def _is_straight(vals: List[int]) -> bool:
    """Check if 5 sorted values form a straight (handles A-2-3-4-5)."""
    if vals[-1] - vals[0] == 4 and len(set(vals)) == 5:
        return True
    # Wheel: A-2-3-4-5
    if vals == [2, 3, 4, 5, 14]:
        return True
    return False


def evaluate_5(cards: List[Card]) -> Tuple[HandRank, List[int]]:
    """
    Evaluate exactly 5 cards.
    Returns (HandRank, tiebreak_values) where tiebreak_values sorts hands
    so that a simple tuple comparison determines the winner.
    """
    vals = sorted([c.value for c in cards])
    suits = [c.suit for c in cards]
    is_flush = len(set(suits)) == 1
    is_str = _is_straight(vals)

    from collections import Counter
    counts = Counter(vals)
    freq = sorted(counts.values(), reverse=True)  # e.g. [2,2,1] for two pair
    # Groups sorted by (frequency desc, value desc) for tiebreaking
    groups = sorted(counts.keys(), key=lambda v: (counts[v], v), reverse=True)

    if is_flush and is_str:
        if vals[-1] == 14 and vals[0] == 10:
            return HandRank.ROYAL_FLUSH, vals
        # Wheel straight flush: reorder for tiebreak
        tv = [1, 2, 3, 4, 5] if vals == [2, 3, 4, 5, 14] else vals
        return HandRank.STRAIGHT_FLUSH, tv

    if freq == [4, 1]:
        return HandRank.FOUR_OF_A_KIND, groups

    if freq == [3, 2]:
        return HandRank.FULL_HOUSE, groups

    if is_flush:
        return HandRank.FLUSH, sorted(vals, reverse=True)

    if is_str:
        tv = [1, 2, 3, 4, 5] if vals == [2, 3, 4, 5, 14] else vals
        return HandRank.STRAIGHT, tv

    if freq == [3, 1, 1]:
        return HandRank.THREE_OF_A_KIND, groups

    if freq == [2, 2, 1]:
        return HandRank.TWO_PAIR, groups

    if freq == [2, 1, 1, 1]:
        return HandRank.ONE_PAIR, groups

    return HandRank.HIGH_CARD, sorted(vals, reverse=True)


def best_5_from(cards: List[Card]) -> Tuple[HandRank, List[int]]:
    """Return the best 5-card hand from 2–7 cards."""
    if len(cards) <= 5:
        return evaluate_5(cards)
    best = None
    for combo in combinations(cards, 5):
        result = evaluate_5(list(combo))
        if best is None or result > best:
            best = result
    return best


def compare_hands(h1: List[Card], h2: List[Card]) -> int:
    """
    Compare two hands (each may be 2-7 cards).
    Returns: 1 if h1 wins, -1 if h2 wins, 0 if tie.
    """
    r1 = best_5_from(h1)
    r2 = best_5_from(h2)
    if r1 > r2:
        return 1
    if r1 < r2:
        return -1
    return 0


def hand_name(rank: HandRank) -> str:
    names = {
        HandRank.HIGH_CARD:       "High Card",
        HandRank.ONE_PAIR:        "One Pair",
        HandRank.TWO_PAIR:        "Two Pair",
        HandRank.THREE_OF_A_KIND: "Three of a Kind",
        HandRank.STRAIGHT:        "Straight",
        HandRank.FLUSH:           "Flush",
        HandRank.FULL_HOUSE:      "Full House",
        HandRank.FOUR_OF_A_KIND:  "Four of a Kind",
        HandRank.STRAIGHT_FLUSH:  "Straight Flush",
        HandRank.ROYAL_FLUSH:     "Royal Flush",
    }
    return names[rank]
