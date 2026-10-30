# Ultimate Texas Hold'em Strategy Simulator

A modular Python simulator for testing card-game strategies.

## Files

| File | Purpose |
|---|---|
| `cards.py` | Deck, Card, and 5–7 card hand evaluator |
| `uth_game.py` | Complete UTH rules engine (all bets, payouts, qualifiers) |
| `strategies.py` | Built-in strategies + base class for custom ones |
| `simulator.py` | Runner, statistics accumulator, comparison table |
| `main.py` | CLI entry point and demos |

## Quick Start

```bash
# Default: compare all strategies over 100,000 hands
python main.py

# More hands for tighter estimates
python main.py --hands 500000

# Watch hand-by-hand (keep --hands small)
python main.py --strategy basic_optimal --verbose --hands 30

# List strategies
python main.py --list-strategies
```

## Included Strategies

| Key | Description |
|---|---|
| `always_fold` | Fold every river — worst-case baseline |
| `always_bet4` | Always raise 4× preflop — pure aggression |
| `always_bet1` | Always check to river, then bet 1× |
| `basic_optimal` | Approximation of published optimal UTH strategy |
| `optimal_trips` | Basic Optimal + Trips side bet |
| `custom` | Template — edit `CustomStrategy` in strategies.py |

## Writing a Custom Strategy

```python
from strategies import StrategyBase
from cards import Card, HandRank, best_5_from
from typing import List, Dict

class MyStrategy(StrategyBase):
    name = "My Strategy"

    def side_bets(self, ante: float) -> Dict[str, float]:
        return {'trips': 1.0}   # or {} for no side bets

    def preflop_action(self, player_cards: List[Card]) -> str:
        # 'bet4', 'bet3', or 'check'
        vals = [c.value for c in player_cards]
        if 14 in vals:           # any ace
            return 'bet4'
        return 'check'

    def flop_action(self, player_cards: List[Card], flop: List[Card]) -> str:
        # 'bet2' or 'check'
        rank, _ = best_5_from(player_cards + flop)
        return 'bet2' if rank >= HandRank.TWO_PAIR else 'check'

    def river_action(self, player_cards: List[Card], community: List[Card]) -> str:
        # 'bet1' or 'fold'
        rank, _ = best_5_from(player_cards + community)
        return 'bet1' if rank >= HandRank.ONE_PAIR else 'fold'
```

Then run it:
```python
from simulator import run_simulation
stats = run_simulation(MyStrategy(), num_hands=100_000, ante=10.0)
print(stats.report())
```

## Pay Tables

### Blind Bet
| Hand | Pays |
|---|---|
| Royal Flush | 500:1 |
| Straight Flush | 50:1 |
| Four of a Kind | 10:1 |
| Full House | 3:1 |
| Flush | 3:2 |
| Straight | 1:1 |
| Below Straight | Push |

### Trips Side Bet
| Hand | Pays |
|---|---|
| Royal Flush | 50:1 |
| Straight Flush | 40:1 |
| Four of a Kind | 30:1 |
| Full House | 8:1 |
| Flush | 7:1 |
| Straight | 4:1 |
| Three of a Kind | 3:1 |

### Progressive (hole cards + flop)
| Hand | Pays |
|---|---|
| Royal Flush | 100% of jackpot |
| Straight Flush | 10:1 |
| Four of a Kind | 3:1 |
| Full House | 2:1 |
| Three of a Kind | 1:1 |

## Adding More Games

To add Blackjack, Three Card Poker, etc.:
1. Create `blackjack_game.py` following the pattern in `uth_game.py`
2. Add strategies in `blackjack_strategies.py`
3. Use `simulator.py`'s `run_simulation()` and `compare_strategies()` directly — they work with any strategy/game pair that returns a `HandResult`-like object with `total_pnl`.
