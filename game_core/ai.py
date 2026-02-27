import random
from typing import List, Optional, Set

from game_core.state import Player


class RandomAIPlayer(Player):
    """AI-игрок, принимающий случайные решения. Снаружи неотличим от обычного Player."""

    def __init__(self, uid: int, name: str):
        super().__init__(uid, name)
        self.logger = None  # Устанавливается снаружи в GameSession.__init__

    def _log(self, method: str, available, chosen):
        if self.logger:
            self.logger.log_event(self.uid, "AI_DECISION", {
                "method": method,
                "available": available,
                "chosen": chosen,
            })

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
            result = ("roll",)
        else:
            card_idx = choice
            target_uid = self._pick_target(self.hand[card_idx].effect_id, opponents)
            result = ("use", card_idx, target_uid)

        self._log(
            "pre_roll_action",
            [f"use card[{i}]={self.hand[i].name}" for i in available] + ["roll"],
            str(result),
        )
        return result

    def decide_move_option(self, options: List[int]) -> int:
        """Возвращает индекс выбранного варианта перемещения."""
        result = random.randrange(len(options))
        self._log("move_option", options, options[result])
        return result

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
            result = 2
        else:
            result = random.randint(0, 2)
        labels = ["buy[0]", "buy[1]", "skip"]
        available = labels if self.can_afford(5) else ["skip"]
        self._log("shop", available, labels[result])
        return result

    def decide_shop_free(self) -> int:
        """0 или 1 — выбрать карту."""
        result = random.randint(0, 1)
        self._log("shop_free", ["card[0]", "card[1]"], f"card[{result}]")
        return result

    # ------------------------------------------------------------------
    # Диалоги одиночного выбора
    # ------------------------------------------------------------------

    def decide_red_choice(self) -> int:
        """0 — потерять 3 монеты, 1 — назад на 3 клетки."""
        result = random.randint(0, 1)
        labels = ["lose_3_coins", "back_3_cells"]
        self._log("red_choice", labels, labels[result])
        return result

    def decide_finish_roll(self) -> int:
        """0 — без бонуса, 1 — -5 монет (+1), 2 — -10 монет (+2)."""
        labels = ["no_bonus", "+1(cost=5coins)", "+2(cost=10coins)"]
        if self.coins >= 10:
            available = labels[:3]
            result = random.randint(0, 2)
        elif self.coins >= 5:
            available = labels[:2]
            result = random.randint(0, 1)
        else:
            available = labels[:1]
            result = 0
        self._log("finish_roll", available, labels[result])
        return result

    def decide_tornado(self) -> int:
        """0 — откупиться (10 монет), 1 — лететь."""
        if self.coins >= 10:
            result = random.randint(0, 1)
            available = ["pay_10", "fly"]
        else:
            result = 1
            available = ["fly"]
        self._log("tornado", available, ["pay_10", "fly"][result])
        return result

    def decide_duel_opponent(self, opponents: List[Player]) -> int:
        """Индекс в списке opponents."""
        result = random.randrange(len(opponents))
        self._log(
            "duel_opponent",
            [o.name for o in opponents],
            opponents[result].name,
        )
        return result

    def decide_duel_reward(self, has_card: bool) -> str:
        """'money', 'push' или 'steal_card'."""
        choices = ["money", "push"]
        if has_card:
            choices.append("steal_card")
        result = random.choice(choices)
        self._log("duel_reward", choices, result)
        return result

    def decide_target(self, opponents: List[Player]) -> int:
        """Индекс в списке opponents."""
        result = random.randrange(len(opponents))
        self._log(
            "target",
            [o.name for o in opponents],
            opponents[result].name,
        )
        return result

    # ------------------------------------------------------------------
    # Слайдер
    # ------------------------------------------------------------------

    def decide_slider(self, max_value: int) -> int:
        """Случайное количество монет от 0 до max_value."""
        result = random.randint(0, max_value)
        self._log("slider", f"[0..{max_value}]", result)
        return result

    # ------------------------------------------------------------------
    # Инвентаризация / налог / сброс
    # ------------------------------------------------------------------

    def decide_inventory_keep(self, cards) -> int:
        """Индекс карты, которую оставить."""
        result = random.randrange(len(cards))
        self._log(
            "inventory_keep",
            [c.name for c in cards],
            cards[result].name,
        )
        return result

    def decide_tax_card(self, can_afford: bool) -> int:
        """0 — заплатить, 1 — сбросить карту."""
        if not can_afford:
            result = 1
            available = ["discard"]
        else:
            result = random.randint(0, 1)
            available = ["pay", "discard"]
        self._log("tax_card", available, ["pay", "discard"][result])
        return result

    def decide_card_to_discard(self, cards) -> int:
        """Индекс карты для сброса."""
        result = random.randrange(len(cards))
        self._log(
            "card_to_discard",
            [c.name for c in cards],
            cards[result].name,
        )
        return result

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
            self._log("mine_placement", "no_coins", [])
            return set()

        n_mines = random.randint(0, self.coins)
        if n_mines == 0:
            self._log("mine_placement", f"coins={self.coins}", [])
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
            self._log("mine_placement", f"no_candidates, frontier={frontier}", [])
            return set()

        result = set(random.sample(candidates, k))
        self._log(
            "mine_placement",
            f"candidates={len(candidates)}, frontier={frontier}, coins={self.coins}, want={n_mines}",
            sorted(result),
        )
        return result
