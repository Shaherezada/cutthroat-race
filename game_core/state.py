from typing import List, Deque, Set
from collections import deque
from game_core.config import START_MONEY, MAX_HAND_SIZE, TA_DAM_QUEUE_SIZE
from game_core.cards import Card, CardLibrary, RuleCard, ShopCard
from game_core.logger import GameLogger


class Player:
    def __init__(self, uid: int, name: str):
        self.uid = uid
        self.name = name
        self.position: int = 0
        self.coins: int = START_MONEY

        self.hand: List[ShopCard] = []
        self.used_cards_indices: Set[int] = set()

        self.skip_next_turn: bool = False
        self.has_extra_turn: bool = False
        self.pending_extra_turn: bool = False # флаг, который переживёт reset_turn_flags() при смене хода

        self.has_moved = False # Совершил ли игрок основной бросок кубика
        self.turn_checks_done = False
        self.end_checks_done = False
        self.is_finished: bool = False

    def can_afford(self, amount: int) -> bool:
        return self.coins >= amount

    def pay(self, amount: int) -> bool:
        if self.coins >= amount:
            self.coins -= amount
            return True
        return False

    def add_coins(self, amount: int):
        self.coins = max(0, self.coins + amount)  # Не уходим в минус при штрафах, если правила не говорят обратного

    def add_card(self, card: Card) -> bool:
        """Возвращает False, если рука полна (нужно сбросить другую)"""
        if len(self.hand) >= MAX_HAND_SIZE:
            return False
        self.hand.append(card)
        return True

    def remove_card(self, index: int) -> Card:
        """Удаляет карту (при сбросе лишней или продаже)"""
        if 0 <= index < len(self.hand):
            return self.hand.pop(index)

    def mark_card_used(self, index: int):
        self.used_cards_indices.add(index)

    def reset_turn_flags(self):
        """Вызывается в начале хода"""
        self.used_cards_indices.clear()
        self.has_moved = False
        self.has_extra_turn = False
        self.turn_checks_done = False
        self.end_checks_done = False

class GameState:
    def __init__(self, player_count=2):
        self.players = [Player(i, f"Игрок {i+1}") for i in range(player_count)]
        self.current_player_idx = 0

        # Колоды
        self.deck_shop = CardLibrary.create_shop_deck()
        self.deck_events = CardLibrary.create_event_deck()
        self.deck_tadam = CardLibrary.create_tadam_deck()

        # Очередь глобальных правил
        self.active_rules: Deque[RuleCard] = deque(maxlen=TA_DAM_QUEUE_SIZE)

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_idx]

    def next_turn(self, logger: GameLogger):
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
        logger.inc_turn()
        self.current_player.reset_turn_flags()

    def add_rule(self, card: RuleCard):
        """Добавляет правило в Та-Дам, вытесняя старое"""
        if len(self.active_rules) == TA_DAM_QUEUE_SIZE:
            removed = self.active_rules.popleft()  # Удаляем старое (FIFO)
            # Тут можно добавить логи в будущем
        self.active_rules.append(card)
