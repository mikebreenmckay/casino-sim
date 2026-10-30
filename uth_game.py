"""
Ultimate Texas Hold'em – full game logic.

Betting structure:
  - Ante (A) + Blind (A) placed before deal (equal amounts).
  - Optional side bets: Trips, Progressive.
  - PREFLOP:  Check  OR  Play 3x or 4x ante.
  - FLOP:     Check  OR  Play 2x ante  (only if no play bet yet).
  - RIVER:    Fold   OR  Play 1x ante  (only if no play bet yet).

Payouts:
  Play / Ante  → 1:1 if player beats dealer, push on tie, lose if dealer wins.
  Ante         → pushes when dealer doesn't qualify (needs pair+).
  Blind        → pays schedule only if player WINS and hand ≥ straight;
                  pushes if player wins with less than straight.
  Trips        → pays schedule regardless of dealer hand.
  Progressive  → pays on player's 2 hole cards + flop (first 3 community).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from cards import Deck, Card, HandRank, best_5_from, compare_hands, hand_name

# ─────────────────────── Pay tables ─────────────────────────────────────────

BLIND_PAYS: Dict[HandRank, float] = {
    HandRank.ROYAL_FLUSH:     500,
    HandRank.STRAIGHT_FLUSH:  50,
    HandRank.FOUR_OF_A_KIND:  10,
    HandRank.FULL_HOUSE:       3,
    HandRank.FLUSH:            1.5,
    HandRank.STRAIGHT:         1,
}

TRIPS_PAYS: Dict[HandRank, float] = {
    HandRank.ROYAL_FLUSH:     50,
    HandRank.STRAIGHT_FLUSH:  40,
    HandRank.FOUR_OF_A_KIND:  30,
    HandRank.FULL_HOUSE:       8,
    HandRank.FLUSH:            7,
    HandRank.STRAIGHT:         4,
    HandRank.THREE_OF_A_KIND:  3,
}

# Progressive pays on player's 2 hole cards + first 3 community cards (5 total)
PROGRESSIVE_PAYS: Dict[HandRank, float] = {
    HandRank.ROYAL_FLUSH:     "jackpot",   # 100% of progressive
    HandRank.STRAIGHT_FLUSH:  10,
    HandRank.FOUR_OF_A_KIND:  3,
    HandRank.FULL_HOUSE:      2,
    HandRank.THREE_OF_A_KIND: 1,
}
PROGRESSIVE_JACKPOT_DEFAULT = 100_000  # starting jackpot


# ─────────────────────── State containers ───────────────────────────────────

@dataclass
class HandResult:
    """Detailed result of one hand for record-keeping / strategy feedback."""
    ante: float
    blind: float
    play_bet: float            # 0 if folded
    trips_bet: float
    progressive_bet: float
    folded: bool

    player_cards: List[Card]
    dealer_cards: List[Card]
    community_cards: List[Card]

    player_hand_rank: Optional[HandRank]
    dealer_hand_rank: Optional[HandRank]

    dealer_qualifies: bool
    outcome: str               # "player_wins", "dealer_wins", "push"

    ante_pnl: float
    blind_pnl: float
    play_pnl: float
    trips_pnl: float
    progressive_pnl: float
    total_pnl: float

    detail: Dict[str, Any] = field(default_factory=dict)

    def __str__(self):
        lines = [
            f"  Player: {self.player_cards}  ({hand_name(self.player_hand_rank) if self.player_hand_rank else 'folded'})",
            f"  Dealer: {self.dealer_cards}  ({hand_name(self.dealer_hand_rank) if self.dealer_hand_rank else '?'})",
            f"  Board:  {self.community_cards}",
            f"  Bets — Ante:{self.ante}  Blind:{self.blind}  Play:{self.play_bet}  "
            f"Trips:{self.trips_bet}  Prog:{self.progressive_bet}",
            f"  Outcome: {self.outcome}  |  Dealer qualifies: {self.dealer_qualifies}",
            f"  P&L → ante:{self.ante_pnl:+.1f}  blind:{self.blind_pnl:+.1f}  "
            f"play:{self.play_pnl:+.1f}  trips:{self.trips_pnl:+.1f}  "
            f"prog:{self.progressive_pnl:+.1f}  = {self.total_pnl:+.1f}",
        ]
        return "\n".join(lines)


# ─────────────────────── Game engine ────────────────────────────────────────

class UltimateTHGame:
    """
    Runs a single hand of Ultimate Texas Hold'em.

    The *strategy* object must implement:
        preflop_action(player_cards) -> 'check' | 'bet3' | 'bet4'
        flop_action(player_cards, flop) -> 'check' | 'bet2'
        river_action(player_cards, community) -> 'fold' | 'bet1'
        side_bets(ante) -> {'trips': float, 'progressive': float}
              (return 0 for any side bet you don't want)
    """

    def __init__(self, progressive_jackpot: float = PROGRESSIVE_JACKPOT_DEFAULT):
        self.progressive_jackpot = progressive_jackpot

    def play_hand(self, ante: float, strategy) -> HandResult:
        deck = Deck()

        # ── Side bets ──────────────────────────────────────────────────────
        sb = strategy.side_bets(ante)
        trips_bet = float(sb.get('trips', 0))
        prog_bet  = float(sb.get('progressive', 0))

        # ── Deal hole cards ────────────────────────────────────────────────
        player_cards = deck.deal(2)
        dealer_cards = deck.deal(2)  # face down

        # ── Community card placeholders ────────────────────────────────────
        flop  = deck.deal(3)
        turn  = deck.deal(1)
        river = deck.deal(1)
        community = flop + turn + river

        # ── Preflop action ─────────────────────────────────────────────────
        play_bet = 0.0
        play_stage = None
        pf_action = strategy.preflop_action(list(player_cards))
        if pf_action == 'bet3':
            play_bet = 3 * ante
            play_stage = 'preflop'
        elif pf_action == 'bet4':
            play_bet = 4 * ante
            play_stage = 'preflop'

        # ── Flop action ────────────────────────────────────────────────────
        if play_bet == 0:
            fl_action = strategy.flop_action(list(player_cards), list(flop))
            if fl_action == 'bet2':
                play_bet = 2 * ante
                play_stage = 'flop'

        # ── River action ───────────────────────────────────────────────────
        folded = False
        if play_bet == 0:
            rv_action = strategy.river_action(list(player_cards), list(community))
            if rv_action == 'bet1':
                play_bet = 1 * ante
                play_stage = 'river'
            else:
                folded = True

        # ── Evaluate hands ─────────────────────────────────────────────────
        player_all = player_cards + community
        dealer_all = dealer_cards + community

        p_rank, p_tb = best_5_from(player_all)
        d_rank, d_tb = best_5_from(dealer_all)

        # Dealer qualifies with at least a pair
        dealer_qualifies = d_rank >= HandRank.ONE_PAIR

        # Overall outcome
        if folded:
            outcome = 'dealer_wins'
        else:
            cmp = compare_hands(player_all, dealer_all)
            if cmp == 1:
                outcome = 'player_wins'
            elif cmp == -1:
                outcome = 'dealer_wins'
            else:
                outcome = 'push'

        # ── Settle bets ────────────────────────────────────────────────────
        ante_pnl  = 0.0
        blind_pnl = 0.0
        play_pnl  = 0.0
        trips_pnl = 0.0
        prog_pnl  = 0.0

        if folded:
            # Forfeit ante + blind; play_bet was never placed
            ante_pnl  = -ante
            blind_pnl = -ante
        else:
            if outcome == 'player_wins':
                # Play always pays 1:1
                play_pnl = play_bet

                # Ante: pays 1:1 if dealer qualifies, else push
                ante_pnl = ante if dealer_qualifies else 0.0

                # Blind: pays schedule if hand ≥ straight, else push
                mult = BLIND_PAYS.get(p_rank)
                if mult is not None:
                    blind_pnl = ante * mult   # blind = ante amount
                else:
                    blind_pnl = 0.0           # push

            elif outcome == 'dealer_wins':
                play_pnl  = -play_bet
                ante_pnl  = -ante
                blind_pnl = -ante

            else:  # push
                # All main bets push
                ante_pnl  = 0.0
                blind_pnl = 0.0
                play_pnl  = 0.0

        # Trips – independent of dealer hand, pays on player's best 5
        if trips_bet > 0:
            t_mult = TRIPS_PAYS.get(p_rank)
            if t_mult:
                trips_pnl = trips_bet * t_mult
            else:
                trips_pnl = -trips_bet

        # Progressive – uses player hole + flop (5 cards)
        if prog_bet > 0:
            prog_5 = player_cards + flop
            prog_rank, _ = best_5_from(prog_5)
            p_mult = PROGRESSIVE_PAYS.get(prog_rank)
            if p_mult == "jackpot":
                prog_pnl = self.progressive_jackpot - prog_bet
            elif p_mult:
                prog_pnl = prog_bet * p_mult
            else:
                prog_pnl = -prog_bet

        total_pnl = ante_pnl + blind_pnl + play_pnl + trips_pnl + prog_pnl

        return HandResult(
            ante=ante,
            blind=ante,
            play_bet=play_bet,
            trips_bet=trips_bet,
            progressive_bet=prog_bet,
            folded=folded,
            player_cards=player_cards,
            dealer_cards=dealer_cards,
            community_cards=community,
            player_hand_rank=p_rank if not folded else None,
            dealer_hand_rank=d_rank,
            dealer_qualifies=dealer_qualifies,
            outcome=outcome,
            ante_pnl=ante_pnl,
            blind_pnl=blind_pnl,
            play_pnl=play_pnl,
            trips_pnl=trips_pnl,
            progressive_pnl=prog_pnl,
            total_pnl=total_pnl,
            detail={'play_stage': play_stage},
        )
