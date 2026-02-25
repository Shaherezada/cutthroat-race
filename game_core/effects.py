import random
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_core.engine import GameEngine

from game_core.config import CellType
from game_core.state import Player


class EffectResolver:
    def __init__(self, engine: "GameEngine"):
        self.engine = engine
        self._registry = self._build_registry()
        self._targeted_registry = self._build_targeted_registry()
        self._targeted_ids = set(self._targeted_registry.keys())

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def resolve(self, effect_id: str, src: Player, val: int = 0, tgt: Optional[Player] = None):
        if effect_id in self._targeted_ids:
            self._dispatch_targeted(effect_id, src, val, tgt)
            return
        handler = self._registry.get(effect_id)
        if handler:
            handler(src, val, tgt)
        else:
            print(f"DEBUG: Эффект {effect_id} еще не имеет реализации.")

    def execute_targeted(self, effect_id: str, src: Player, tgt: Player, val: int = 0):
        """Вызывается напрямую, когда цель уже известна (resolve_target_choice и т.д.)"""
        handler = self._targeted_registry.get(effect_id)
        if handler:
            handler(src, tgt, val)

    # ------------------------------------------------------------------
    # Простые эффекты
    # ------------------------------------------------------------------

    def _gain_coins(self, src, val, _tgt):
        src.add_coins(val)

    def _lose_coins(self, src, val, _tgt):
        src.pay(min(src.coins, val))

    def _move_self_forward(self, src, val, _tgt):
        self.engine.move_player(src, val)

    def _move_self_back(self, src, val, _tgt):
        self.engine.move_player(src, val, is_forward=False)

    def _no_effect(self, _src, _val, _tgt):
        pass

    def _move_forward_gain_coins(self, src, val, _tgt):
        self.engine.move_player(src, val)
        src.add_coins(val)

    # ------------------------------------------------------------------
    # Сложные перемещения
    # ------------------------------------------------------------------

    def _move_nearest_green(self, src, _val, _tgt):
        board = self.engine.board
        for i in range(src.position + 1, board.max_cell_id):
            if board.get_cell(i).type == CellType.GREEN:
                self.engine.move_player(src, i - src.position)
                return
        self.engine.move_player(src, 3)

    def _move_back_to_red_or_3(self, src, _val, _tgt):
        for i in range(src.position - 1, -1, -1):
            if self.engine.board.get_cell(i).type == CellType.RED:
                src.position = i
                return
        self.engine.move_player(src, 3, is_forward=False)

    # ------------------------------------------------------------------
    # Массовые эффекты
    # ------------------------------------------------------------------

    def _pay_all_others_bank(self, src, val, _tgt):
        for p in self.engine.state.players:
            if p.uid != src.uid:
                p.add_coins(val)

    def _steal_coins_from_all(self, src, val, _tgt):
        for p in self.engine.state.players:
            if p.uid != src.uid and p.pay(val):
                src.add_coins(val)

    def _others_move_forward(self, src, val, _tgt):
        for p in self.engine.state.players:
            if p.uid != src.uid:
                self.engine.move_player(p, val, apply_effects=False)

    def _all_lose_coins_global(self, _src, val, _tgt):
        for p in self.engine.state.players:
            p.pay(min(p.coins, val))

    def _others_gain_coins_move(self, src, val, _tgt):
        for p in self.engine.state.players:
            if p.uid != src.uid:
                p.add_coins(val)
                self.engine.move_player(p, val, apply_effects=False)

    def _steal_2_from_all(self, src, val, _tgt):
        for p in self.engine.state.players:
            if p.uid != src.uid:
                amount = min(p.coins, val)
                if p.pay(amount):
                    src.add_coins(amount)

    def _draw_2_bad(self, src, _val, _tgt):
        from game_core.engine import GameEvent
        for _ in range(2):
            card = self.engine.state.deck_events.draw(1)[0]
            self.engine.pending_events.append(GameEvent(
                type="EVENT_CARD", player=src,
                data={"card": card, "is_good": False}
            ))

    # ------------------------------------------------------------------
    # Эффекты с UI-вводом
    # ------------------------------------------------------------------

    def _pay_coins_move_flexible(self, src, val, _tgt):
        from game_core.engine import GameEvent
        max_coins = min(5, src.coins) if val > 0 else src.coins
        if max_coins == 0:
            return
        desc = ("За каждую сброшенную монету передвинься на 2 клетки вперёд."
                if val == 2 else
                "Сбрось сколько угодно монет, передвинься на столько же клеток вперёд.")
        self.engine.pending_events.append(GameEvent(
            type="SLIDER_INPUT", player=src,
            data={
                "effect_id": "pay_coins_move_flexible",
                "max_value": max_coins,
                "multiplier": val if val != 0 else 1,
                "title": "Сбросить монеты",
                "description": desc,
                "target_self": True,
            }
        ))

    def _place_mines(self, src, val, _tgt):
        from game_core.engine import GameEvent
        self.engine.pending_events.append(GameEvent(
            type="MINE_PLACEMENT", player=src, data={"cost_per_mine": val}
        ))

    def _tax_shop_cards(self, src, val, _tgt):
        from game_core.engine import GameEvent
        if not src.hand:
            return
        self.engine.pending_events.append(GameEvent(
            type="TAX_SHOP_CARD", player=src, data={"card_idx": 0, "cost": val}
        ))

    def _all_discard_to_one_shop_card(self, _src, _val, _tgt):
        from game_core.engine import GameEvent
        for pl in self.engine.state.players:
            if len(pl.hand) > 1:
                self.engine.pending_events.append(GameEvent(
                    type="INVENTORY_KEEP", player=pl, data={"cards": pl.hand}
                ))

    def _draw_2_keep_1_free(self, src, _val, _tgt):
        from game_core.engine import GameEvent
        cards = self.engine.state.deck_shop.draw(2)
        self.engine.pending_events.append(GameEvent(
            type="SHOP_FREE", player=src, data={"cards": cards}
        ))

    def _pay_coins_move_others_back(self, src, _val, _tgt):
        from game_core.engine import GameEvent

        active_opponents = [p for p in self.engine.state.players if p.uid != src.uid and not p.is_finished]

        if not active_opponents or src.coins == 0:
            return

        max_useful = min(p.position for p in active_opponents)
        if max_useful == 0:
            return

        self.engine.pending_events.append(GameEvent(
            type="SLIDER_INPUT", player=src,
            data={
                "effect_id": "pay_coins_move_others_back",
                "max_value": min(src.coins, max_useful),
                "multiplier": -1,
                "title": "Саботаж",
                "description": "Сбрось любое количество монет. Остальные игроки передвинутся на столько же клеток назад.",
                "target_self": False,
            }
        ))

    def _discard_shop_or_red(self, src, _val, _tgt):
        from game_core.engine import GameEvent
        if not src.hand:
            self._move_back_to_red_or_3(src, 0, None)
            return
        if len(src.hand) == 1:
            self.engine.state.deck_shop.discard(src.remove_card(0))
            return
        self.engine.pending_events.append(GameEvent(
            type="CHOOSE_CARD_TO_DISCARD", player=src,
            data={"target": src, "cards": src.hand}
        ))

    def _extra_turn_pay_coins(self, src, val, _tgt):
        if src.pay(val):
            src.has_extra_turn = True
            self.engine.logger.log_event(src.uid, "EXTRA_TURN_PAID", {"cost": val})

    # ------------------------------------------------------------------
    # Random эффекты
    # ------------------------------------------------------------------

    def _roll_lose_coins_or_move_back(self, src, _val, _tgt):
        roll = random.randint(1, 6)
        if roll <= 3:
            src.pay(5)
            self.engine.logger.log_event(src.uid, "ROLL_EFFECT", {"roll": roll, "result": "lose_coins", "value": 5})
        else:
            self.engine.move_player(src, 10, is_forward=False)
            self.engine.logger.log_event(src.uid, "ROLL_EFFECT", {"roll": roll, "result": "move_back", "value": 10})

    def _roll_gamble_money_move(self, src, _val, _tgt):
        roll = random.randint(1, 6)
        if roll <= 3:
            src.add_coins(10)
            self.engine.logger.log_event(src.uid, "ROLL_EFFECT", {"roll": roll, "result": "gain_coins", "value": 10})
        else:
            self.engine.move_player(src, 5)
            self.engine.logger.log_event(src.uid, "ROLL_EFFECT", {"roll": roll, "result": "move_forward", "value": 5})

    # ------------------------------------------------------------------
    # Та-Дам
    # ------------------------------------------------------------------

    def _rule_red_choice(self, src, _val, _tgt):
        from game_core.engine import GameEvent
        self.engine.pending_events.append(GameEvent(type="RED_CHOICE", player=src, data={}))

    # ------------------------------------------------------------------
    # Targeted
    # ------------------------------------------------------------------

    def _dispatch_targeted(self, effect_id: str, src: Player, val: int, tgt: Optional[Player]):
        from game_core.engine import GameEvent
        if effect_id == "steal_shop_card_leader":
            opponents = [p for p in self.engine.state.players
                         if p.uid != src.uid and p.position > src.position]
            if not opponents:
                return
        else:
            opponents = [p for p in self.engine.state.players if p.uid != src.uid]

        if tgt:
            self.execute_targeted(effect_id, src, tgt, val)
        elif len(opponents) == 1:
            self.execute_targeted(effect_id, src, opponents[0], val)
        else:
            self.engine.pending_events.append(GameEvent(
                type="CHOOSE_TARGET", player=src,
                data={"effect_id": effect_id, "value": val, "opponents": opponents}
            ))

    def _t_steal_coins_target(self, src, tgt, val):
        amount = min(tgt.coins, val)
        if tgt.pay(amount):
            src.add_coins(amount)
            self.engine.logger.log_event(src.uid, "EFFECT_STEAL", {
                "from": tgt.name, "target_uid": tgt.uid, "amount": amount
            })

    def _t_force_enemy_draw_bad(self, src, tgt, _val):
        from game_core.engine import GameEvent
        card = self.engine.state.deck_events.draw(1)[0]
        self.engine.pending_events.append(GameEvent(
            type="EVENT_CARD", player=tgt, data={"card": card, "is_good": False}
        ))
        self.engine.logger.log_event(src.uid, "EFFECT_FORCE_DRAW_BAD", {
            "target": tgt.name, "target_uid": tgt.uid, "card": card.bad_side.name
        })

    def _t_discard_enemy_shop_card(self, src, tgt, _val):
        from game_core.engine import GameEvent
        if not tgt.hand:
            return
        if len(tgt.hand) == 1:
            card = tgt.remove_card(0)
            self.engine.state.deck_shop.discard(card)
            self.engine.logger.log_event(src.uid, "EFFECT_DISCARD", {"target": tgt.name, "card": card.name})
        else:
            self.engine.pending_events.append(GameEvent(
                type="CHOOSE_CARD_TO_DISCARD", player=src,
                data={"target": tgt, "cards": tgt.hand}
            ))

    def _t_roll_push_enemy(self, src, tgt, _val):
        roll = random.randint(1, 6)
        self.engine.move_player(tgt, roll, apply_effects=False)
        self.engine.logger.log_event(src.uid, "EFFECT_PUSH", {"target": tgt.name, "roll": roll})

    def _t_give_coins_to_target(self, src, tgt, val):
        amount = min(src.coins, val)
        src.pay(amount)
        tgt.add_coins(amount)
        self.engine.logger.log_event(src.uid, "EFFECT_GIVE", {"to": tgt.name, "amount": amount})

    def _t_force_enemy_lose_coins(self, src, tgt, val):
        amount = min(tgt.coins, val)
        tgt.pay(amount)
        self.engine.logger.log_event(src.uid, "EFFECT_FORCE_LOSE", {"target": tgt.name, "amount": amount})

    def _t_force_enemy_gain_coins(self, src, tgt, val):
        tgt.add_coins(val)
        self.engine.logger.log_event(src.uid, "EFFECT_GAIN_TARGET", {
            "target": tgt.name, "amount": val
        })

    def _t_give_double_turn_enemy(self, src, tgt, _val):
        tgt.pending_extra_turn = True
        self.engine.logger.log_event(src.uid, "EFFECT_DOUBLE_TURN", {"target": tgt.name})

    def _t_steal_shop_card_leader(self, src, tgt, _val):
        from game_core.engine import GameEvent
        if not tgt.hand:
            return
        if len(tgt.hand) == 1:
            card = tgt.remove_card(0)
            if src.add_card(card):
                self.engine.logger.log_event(src.uid, "EFFECT_STEAL_CARD", {"target": tgt.name, "card": card.name})
            else:
                self.engine.state.deck_shop.discard(card)
        else:
            self.engine.pending_events.append(GameEvent(
                type="CHOOSE_CARD_TO_DISCARD", player=src,
                data={"target": tgt, "cards": tgt.hand}
            ))

    def _t_skip_turn_mutual(self, src, tgt, _val):
        src.skip_next_turn = True
        if len(self.engine.state.players) > 2:
            tgt.skip_next_turn = True
        self.engine.logger.log_event(src.uid, "SKIP_TURN_MUTUAL", {"target": tgt.name})

    # ------------------------------------------------------------------
    # Реестры
    # ------------------------------------------------------------------

    def _build_registry(self) -> dict:
        return {
            "gain_coins":                   self._gain_coins,
            "lose_coins":                   self._lose_coins,
            "move_self_forward":            self._move_self_forward,
            "move_self_back":               self._move_self_back,
            "no_effect":                    self._no_effect,
            "move_forward_gain_coins":      self._move_forward_gain_coins,
            "move_nearest_green":           self._move_nearest_green,
            "move_back_to_red_or_3":        self._move_back_to_red_or_3,
            "pay_all_others_bank":          self._pay_all_others_bank,
            "steal_coins_from_all":         self._steal_coins_from_all,
            "others_move_forward":          self._others_move_forward,
            "all_lose_coins_global":        self._all_lose_coins_global,
            "others_gain_coins_move":       self._others_gain_coins_move,
            "steal_2_from_all":             self._steal_2_from_all,
            "draw_2_bad":                   self._draw_2_bad,
            "pay_coins_move_flexible":      self._pay_coins_move_flexible,
            "place_mines":                  self._place_mines,
            "tax_shop_cards":               self._tax_shop_cards,
            "all_discard_to_one_shop_card": self._all_discard_to_one_shop_card,
            "draw_2_keep_1_free":           self._draw_2_keep_1_free,
            "pay_coins_move_others_back":   self._pay_coins_move_others_back,
            "discard_shop_or_red":          self._discard_shop_or_red,
            "extra_turn_pay_coins":         self._extra_turn_pay_coins,
            "roll_lose_coins_or_move_back": self._roll_lose_coins_or_move_back,
            "roll_gamble_money_move":       self._roll_gamble_money_move,
            "rule_red_choice":              self._rule_red_choice,
        }

    def _build_targeted_registry(self) -> dict:
        return {
            "steal_coins_target":      self._t_steal_coins_target,
            "force_enemy_draw_bad":    self._t_force_enemy_draw_bad,
            "discard_enemy_shop_card": self._t_discard_enemy_shop_card,
            "roll_push_enemy":         self._t_roll_push_enemy,
            "give_5_to_target":        self._t_give_coins_to_target,
            "give_10_to_target":       self._t_force_enemy_gain_coins,
            "force_enemy_lose_coins":  self._t_force_enemy_lose_coins,
            "give_double_turn_enemy":  self._t_give_double_turn_enemy,
            "steal_shop_card_leader":  self._t_steal_shop_card_leader,
            "skip_turn_mutual":        self._t_skip_turn_mutual,
        }
