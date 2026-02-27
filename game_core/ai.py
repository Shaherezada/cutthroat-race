import random
from typing import List, Optional, Set

from game_core.state import Player


class RandomAIPlayer(Player):
    """AI-игрок, принимающий случайные решения. Снаружи неотличим от обычного Player."""

    def __init__(self, uid: int, name: str):
        super().__init__(uid, name)

    # ------------------------------------------------------------------
    # До броска на перемещение: использовать карту или бросать кубики?
    # ------------------------------------------------------------------

    def decide_pre_roll_action(self, opponents: List[Player]) -> tuple:
        """
        Возвращает ('use', card_idx, target_idx) или ('roll',).
        Перебирает доступные активные карты; случайно решает,
        делать ли ход картой или бросать кубики.
        """
        available = []
        for i, card in enumerate(self.hand):
            if card.is_passive or i in self.used_cards_indices:
                continue
            if not self.can_afford(card.use_cost):
                continue
            # Проверяем, есть ли подходящая цель для атакующих карт
            eid = card.effect_id
            if eid in ("attack_hook", "move_harpoon"):
                targets = [o for o in opponents
                           if not o.is_finished and 0 < (o.position - self.position) <= 10]
                if not targets:
                    continue
            elif eid in ("attack_grenade", "attack_voodoo"):
                targets = [o for o in opponents
                           if not o.is_finished and o.position > self.position]
                if not targets:
                    continue
            elif eid == "attack_hand_fate":
                targets = [o for o in opponents
                           if not o.is_finished and o.position > 0]
                if not targets:
                    continue
            available.append(i)

        # Список вариантов: все доступные карты + «бросить кубики»
        options = available + ["roll"]
        choice = random.choice(options)

        if choice == "roll":
            return ("roll",)

        card_idx = choice
        card = self.hand[card_idx]
        # Выбираем случайного подходящего врага
        target_idx = self._pick_target(card.effect_id, opponents)
        return "use", card_idx, target_idx

    def _pick_target(self, effect_id: str, opponents: List[Player]) -> Optional[int]:
        if effect_id in ("attack_hook", "move_harpoon"):
            valid = [o for o in opponents
                     if not o.is_finished and 0 < (o.position - self.position) <= 10]
        elif effect_id in ("attack_grenade", "attack_voodoo"):
            valid = [o for o in opponents
                     if not o.is_finished and o.position > self.position]
        elif effect_id == "attack_hand_fate":
            valid = [o for o in opponents
                     if not o.is_finished and o.position > 0]
        else:
            valid = [o for o in opponents if not o.is_finished]

        if not valid:
            return None
        return random.choice(valid).uid

    # ------------------------------------------------------------------
    # Лавка Джо
    # ------------------------------------------------------------------

    def decide_shop(self) -> int:
        """0 или 1 — купить карту, 2 — пропустить."""
        if not self.can_afford(5):
            return 2
        return random.randint(0, 2)  # 0, 1 — купить, 2 — скип

    def decide_shop_free(self) -> int:
        """0 или 1 — выбрать карту."""
        return random.randint(0, 1)

    # ------------------------------------------------------------------
    # Диалоги одиночного выбора
    # ------------------------------------------------------------------

    def decide_red_choice(self) -> int:
        """0 — потерять 3 монеты, 1 — назад на 3 клетки."""
        return random.randint(0, 1)

    def decide_finish_roll(self) -> int:
        """0 — без бонуса, 1 — -5 монет (+1), 2 — -10 монет (+2)."""
        if self.coins >= 10:
            return random.randint(0, 2)
        if self.coins >= 5:
            return random.randint(0, 1)
        return 0

    def decide_tornado(self) -> int:
        """0 — откупиться (10 монет), 1 — лететь."""
        if self.coins >= 10:
            return random.randint(0, 1)
        return 1

    def decide_duel_opponent(self, opponents: List[Player]) -> int:
        """Индекс в списке opponents."""
        return random.randrange(len(opponents))

    def decide_duel_reward(self, has_card: bool) -> str:
        """'money', 'push' или 'steal_card'."""
        choices = ["money", "push"]
        if has_card:
            choices.append("steal_card")
        return random.choice(choices)

    def decide_target(self, opponents: List[Player]) -> int:
        """Индекс в списке opponents."""
        return random.randrange(len(opponents))

    # ------------------------------------------------------------------
    # Слайдер
    # ------------------------------------------------------------------

    def decide_slider(self, max_value: int) -> int:
        """Случайное количество монет от 0 до max_value."""
        return random.randint(0, max_value)

    # ------------------------------------------------------------------
    # Инвентаризация / налог / сброс
    # ------------------------------------------------------------------

    def decide_inventory_keep(self, cards) -> int:
        """Индекс карты, которую оставить."""
        return random.randrange(len(cards))

    def decide_tax_card(self, can_afford: bool) -> int:
        """0 — заплатить, 1 — сбросить карту."""
        if not can_afford:
            return 1
        return random.randint(0, 1)

    def decide_card_to_discard(self, cards) -> int:
        """Индекс карты для сброса."""
        return random.randrange(len(cards))

    # ------------------------------------------------------------------
    # Расстановка мин (двухслойный рандом)
    # ------------------------------------------------------------------

    def decide_mine_placement(self, all_cell_ids: List[int],
                              enemy_positions: List[int]) -> Set[int]:
        """
        Возвращает множество cell_id для расстановки мин.
        Слой 1: случайное количество мин N = randint(0, coins).
        Слой 2: случайное N-подмножество клеток строго правее
                самого дальнего врага.
        """
        if self.coins <= 0:
            return set()

        n_mines = random.randint(0, self.coins)
        if n_mines == 0:
            return set()

        # Клетки строго правее самого дальнего врага
        if enemy_positions:
            frontier = max(enemy_positions)
        else:
            frontier = self.position  # ставим перед собой

        candidates = [cid for cid in all_cell_ids
                      if isinstance(cid, int) and cid > frontier]

        if not candidates:
            candidates = [cid for cid in all_cell_ids if isinstance(cid, int)]

        k = min(n_mines, len(candidates))
        if k == 0:
            return set()

        return set(random.sample(candidates, k))
