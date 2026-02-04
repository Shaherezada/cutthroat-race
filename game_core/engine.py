import random
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from game_core.config import CellType, WINNING_ROLL
from game_core.board import Board
from game_core.logger import GameLogger
from game_core.state import GameState, Player
from game_core.cards import Card, ShopCard, EventCard, RuleCard

@dataclass
class GameEvent:
    """События, которые должен обработать UI или AI"""
    type: str  # "SHOP", "EVENT_CARD", "DUEL_START", etc.
    player: Player
    data: dict = None

class GameEngine:
    def __init__(self, logger: GameLogger, player_count: int = 2):
        self.board = Board()
        self.state = GameState(player_count)
        self.logger = logger  # Внедряем логгер
        self.is_game_over = False
        self.winner: Optional[Player] = None
        self.placed_mines: Dict[int, int] = {} # Для хранения мин (карта Хорошо): {cell_id: owner_uid}
        self.pending_events: List[GameEvent] = []

    def get_roll(self, player: Player) -> List[int]:
        pos = player.position
        cell = self.board.get_cell(pos)

        # Кубик удачи (ID 40)
        if cell and cell.type == CellType.FORTUNE_CUBE:
            return [random.randint(1, 6) for _ in range(3)]

        count = 2 if 24 <= pos <= 97 else 1
        rolls = [random.randint(1, 6) for _ in range(count)]

        # Та-Дам "дубль-ход"
        if count == 2 and rolls[0] == rolls[1]:
            for rule in self.state.active_rules:
                if rule.effect_id == "rule_double_reroll":
                    # TODO: дать повторный ход (main.py)
                    self.logger.log_event(player.uid, "RULE_TRIGGER", {
                        "rule": rule.name, "rolls": rolls
                    })
                    raise NotImplementedError("Правило: 'дубль ход': требуется механика повторного хода")

        # Та-Дам "проклятие шестёрки"
        if any(r == 6 for r in rolls):
            for rule in self.state.active_rules:
                if rule.effect_id == "rule_six_skip":
                    player.skip_next_turn = True
                    self.logger.log_event(player.uid, "RULE_SIX_SKIP", {})
        return rolls

    def get_move_options(self, player: Player, rolls: List[int]) -> List[int]:
        """
        Принимает «сырые» броски и возвращает список доступных вариантов перемещения.
        Учитывает зоны, Кубик удачи и пассивку Волшебный куб.
        """
        pos = player.position
        cell = self.board.get_cell(pos)
        has_cube = any(c.effect_id == "passive_roll_plus_1" for c in player.hand)

        options = []

        # Зоны суммирования
        if (cell and cell.type == CellType.FORTUNE_CUBE) or (68 <= pos <= 97):
            s = sum(rolls)
            return [s, s + 1] if has_cube else [s]

        options = []
        # Если Зона 1, rolls содержит 1 элемент. Если Зона 2 - два элемента.
        for r in rolls:
            options.append(r)
            if has_cube:
                options.append(r + 1)

        return sorted(list(set(options)))

    def can_player_do_actions(self, player: Player) -> bool:
        """Проверка, есть ли у игрока доступные активные карты, которые он может оплатить"""
        opponents = [o for o in self.state.players if o.uid != player.uid]
        for i, card in enumerate(player.hand):
            if card.is_passive or i in player.used_cards_indices:
                continue

            if player.can_afford(card.use_cost):
                if card.effect_id in ["attack_hook", "move_harpoon"]:
                    if any(0 < (o.position - player.position) <= 10 for o in opponents):
                        return True
                elif card.effect_id in ["attack_grenade", "attack_voodoo", "attack_hand_fate"]:
                    if opponents: return True
                else: return True
        return False

    def move_player(self, player: Player, steps: int, is_forward: bool = True):
        """
        Передвигает игрока и запускает цепочку проверок приземления.
        События складываются в self.pending_events для обработки UI
        """
        actual_steps = steps if is_forward else -steps
        start_pos = player.position
        target_pos = self.board.resolve_move(start_pos, actual_steps)

        # Та-дам "карманник"
        if is_forward:
            for other in self.state.players:
                if other.uid != player.uid:
                    # Если позиция другого игрока находится между стартом и финишем движения
                    if start_pos < other.position <= target_pos:
                        for rule in self.state.active_rules:
                            if rule.effect_id == "rule_overtake_steal":
                                amount = min(other.coins, rule.value)
                                if other.pay(amount):
                                    player.add_coins(amount)
                                    self.logger.log_event(player.uid, "RULE_OVERTAKE",
                                                          {"from": other.name, "amount": amount})

        player.position = target_pos

        # Эффекты срабатывают только при движении ВПЕРЁД в свой ход
        if is_forward:
            player.has_moved = True
            cell = self.board.get_cell(player.position)
            # Проверка портала (чтобы не зациклиться, просто прыгаем и НЕ вызываем лендинг снова)
            if cell.type == CellType.PORTAL and cell.portal_target is not None:
                player.position = cell.portal_target
            else:
                self._handle_landing(player)

    def _handle_landing(self, player: Player):
        cell = self.board.get_cell(player.position)

        # 1. Проверка мин (подрывается даже владелец)
        if player.position in self.placed_mines:
            self.placed_mines.pop(player.position)
            player.skip_next_turn = True
            self.logger.log_event(player.uid, "MINE_TRIGGERED", {
                "position": player.position
            })
            return # Эффект клетки не срабатывает

        # 2. Проверка пассивных предметов Лавки Джо
        self._check_passives(player, cell)

        # 3. Проверка глобальных правил (Та-Дам)
        self._check_global_rules(player, cell)

        # 4. Активация механики клетки
        self._trigger_cell_effect(player, cell)

    def _check_passives(self, player: Player, cell):
        """Проверка пассивных карт (магнит, клевер, траволатор)."""
        for card in player.hand:
            if not isinstance(card, ShopCard) or not card.is_passive:
                continue

            if card.effect_id == "passive_red_income" and cell.type == CellType.RED:
                player.add_coins(card.value)
            elif card.effect_id == "passive_empty_income" and cell.type == CellType.EMPTY:
                player.add_coins(card.value)
            elif card.effect_id == "passive_empty_move" and cell.type == CellType.EMPTY:
                self.move_player(player, card.value)  # Рекурсивный прыжок вперед
            elif card.effect_id == "passive_roll_plus_1":
                pass  # Обрабатывается в логике броска (в UI или Engine до вызова move)

    def start_turn_checks(self, player: Player):
        """Для правил, действующих в начале хода (бонусы отстающим и т.д.)"""
        # Проверка пропуска хода
        if player.skip_next_turn:
            player.skip_next_turn = False
            self.logger.log_event(player.uid, "TURN_SKIPPED", {})
            # Завершаем ход немедленно
            self.state.next_turn()
            return True

        is_last = self._is_last(player)

        for rule in self.state.active_rules:
            eid = rule.effect_id
            if is_last:
                if eid == "rule_last_player_income":
                    player.add_coins(rule.value)
                    self.logger.log_event(player.uid, "RULE_TRIGGER", {
                        "rule": rule.name, "gain": rule.value
                    })
                elif eid == "rule_last_aid":
                    if len(player.hand) < 3:
                        card = self.state.deck_shop.draw(1)[0]
                        player.add_card(card)
                        self.logger.log_event(player.uid, "RULE_TRIGGER", {
                            "rule": rule.name, "card": card.name
                        })
                elif eid == 'rule_last_draw_good':
                    card = self.state.deck_events.draw(1)[0]
                    self.pending_events.append(GameEvent(type="EVENT_CARD", player=player, data={
                        "card": card,
                        "is_good": True
                    }))
                    self.logger.log_event(player.uid, "RULE_TRIGGER", {"rule": rule.name})

        return False

    def end_turn_checks(self, player: Player):
        """Правила, действующие в конце хода игрока"""
        is_last = self._is_last(player)

        for rule in self.state.active_rules:
            eid = rule.effect_id

            if is_last:
                if eid == "rule_last_dice_coins":
                    roll = random.randint(1, 6)
                    player.add_coins(roll)
                    self.logger.log_event(player.uid, "RULE_TRIGGER", {
                        "rule": rule.name, "roll": roll, "gain": roll
                    })

                elif eid == "rule_last_move_5":
                    self.move_player(player, rule.value)
                    self.logger.log_event(player.uid, "RULE_TRIGGER", {
                        "rule": rule.name, "move": rule.value
                    })

    def _check_global_rules(self, player: Player, cell):
        """Проверка правил Та-Дам после броска на передвижение."""
        for rule in self.state.active_rules:
            eid = rule.effect_id

            # Срабатывают при приземлении на цвет
            if cell.type == CellType.RED:
                if eid == "rule_red_bad":
                    card = self.state.deck_events.draw(1)[0]
                    self.pending_events.append(GameEvent(
                        type="EVENT_CARD",
                        player=player,
                        data={"card": card, "is_good": False}
                    ))
                elif eid == "rule_red_tax_all":
                    # 2 монеты всем (4 если вдвоем)
                    amount = 4 if len(self.state.players) == 2 else 2
                    for p in self.state.players:
                        if p.uid != player.uid:
                            if player.pay(amount): p.add_coins(amount)
                elif eid == "rule_red_choice":
                    raise NotImplementedError("Та-Дам 'Красная западня': Нужен выбор -3 монеты или -3 шага в UI")

            if cell.type == CellType.GREEN:
                if eid == "rule_green_good":
                    card = self.state.deck_events.draw(1)[0]
                    self.pending_events.append(GameEvent(
                        type="EVENT_CARD",
                        player=player,
                        data={"card": card, "is_good": True}
                    ))
                elif eid == "rule_green_income":
                    player.add_coins(rule.value)
                elif eid == "rule_green_move":
                    self.move_player(player, rule.value)
                elif eid == "rule_green_extra_turn":
                    raise NotImplementedError("Та-Дам 'зелёный разгон': Реализовать повторный ход текущего игрока")

            # Правила, требующие сложной проверки контекста
            if eid == "rule_six_skip":
                pass  # Уже обработано в get_roll()

            if eid == "rule_overtake_steal":
                pass  # Уже обработано в move_player()

            if rule.effect_id == "rule_collision_duel":
                for other in self.state.players:
                    if other.uid != player.uid and other.position == player.position:
                        opponents = [other]
                        self.pending_events.append(GameEvent(
                            type="DUEL_CHOOSE_OPPONENT",
                            player=player,
                            data={"opponents": opponents}
                        ))
                        break

    def _trigger_cell_effect(self, player: Player, cell):
        """Логика конкретных типов клеток."""
        ctype = cell.type

        if ctype == CellType.SHOP:
            cards = self.state.deck_shop.draw(2)
            self.pending_events.append(GameEvent(
                type="SHOP",
                player=player,
                data={"cards": cards}
            ))

        elif ctype == CellType.CHEST_GOOD:
            card = self.state.deck_events.draw(1)[0]
            self.pending_events.append(GameEvent(
                type="EVENT_CARD",
                player=player,
                data={"card": card, "is_good": True}
            ))

        elif ctype == CellType.CHEST_BAD:
            card = self.state.deck_events.draw(1)[0]
            self.pending_events.append(GameEvent(
                type="EVENT_CARD",
                player=player,
                data={"card": card, "is_good": False}
            ))

        elif ctype == CellType.TA_DAM:
            new_rule = self.state.deck_tadam.draw(1)[0]
            self.pending_events.append(GameEvent(
                type="TADAM_SHOW",
                player=player,
                data={"rule": new_rule},
            ))

        elif ctype == CellType.PORTAL:
            if cell.portal_target is not None:
                player.position = cell.portal_target

        elif ctype == CellType.MINE:
            # Шахта: 1 - пропуск, 2-5 - деньги, 6 - победа
            roll = random.randint(1, 6)
            if roll == 1: player.skip_next_turn = True
            elif roll == 6: self.is_game_over, self.winner = True, player
            else: player.add_coins(10)

        elif ctype == CellType.TORNADO:
            # Создаем события выбора для всех остальных игроков
            for p in self.state.players:
                if p.uid != player.uid:
                    self.pending_events.append(GameEvent(
                        type="TORNADO_DECISION",
                        player=p,
                        data={"target_pos": player.position}
                    ))

        elif ctype == CellType.DUEL:
            other_players = [p for p in self.state.players if p.uid != player.uid] # Выбор противника для схватки
            self.pending_events.append(GameEvent(
                type="DUEL_CHOOSE_OPPONENT",
                player=player,
                data={"opponents": other_players}
            ))

        elif ctype == CellType.BICYCLE:
            self.move_player(player, 10)

        elif ctype == CellType.OH_NO:
            player.pay(10)

        elif ctype == CellType.FORTUNATE_SETUP:
            # Это серия событий - создаём их по очереди

            # 1. Событие Хорошо
            good_card = self.state.deck_events.draw(1)[0]
            self.pending_events.append(GameEvent(
                type="EVENT_CARD",
                player=player,
                data={"card": good_card, "is_good": True}
            ))

            # 2. Бесплатная карта Лавки
            shop_card = self.state.deck_shop.draw(1)[0]
            player.add_card(shop_card)

            # 3. Новое правило
            new_rule = self.state.deck_tadam.draw(1)[0]
            self.state.add_rule(new_rule)

            # 4. Враги тянут Плохо
            for p in self.state.players:
                if p.uid != player.uid:
                    bad_card = self.state.deck_events.draw(1)[0]
                    self.pending_events.append(GameEvent(
                        type="EVENT_CARD",
                        player=p,
                        data={"card": bad_card, "is_good": False}
                    ))

        elif ctype == CellType.TRIBUTE:
            total_collected = 0
            for p in self.state.players:
                if p.uid != player.uid:
                    roll = random.randint(1, 6)
                    # Игрок платит сколько выпало (или всё, что есть)
                    payment = min(p.coins, roll)
                    if p.pay(payment):
                        total_collected += payment
            player.add_coins(total_collected)

        elif ctype == CellType.FINISH_SAFE:
            player.is_finished = True

        elif ctype == CellType.RED or ctype == CellType.GREEN:
            pass  # Зелёные и красные клетки обрабатываются через правила Та-Дам

        elif ctype == CellType.EMPTY:
            pass

        else:
            raise Exception(f"КУДА МЫ ВСТАЛИ БЛ?Ё! тип клетки: {ctype}")

    def resolve_shop_choice(self, player: Player, cards: List[ShopCard], choice_idx: int):
        """Разрешение выбора в Лавке Джо (0, 1 - купить, 2 - сбросить)"""
        if choice_idx < 2:
            card = cards[choice_idx]
            if player.pay(5):
                player.add_card(card)
                self.logger.log_event(player.uid, "SHOP_BUY", {
                    "card": card.name,
                    "cost": 5
                })
            self.state.deck_shop.discard(cards[1 - choice_idx]) # вторую карту в сброс?
        else:
            for c in cards:
                self.state.deck_shop.discard(c)
            self.logger.log_event(player.uid, "SHOP_SKIP", {})

    def resolve_duel_opponent(self, attacker: Player, defender: Player):
        """
        Проводит дуэль и создаёт событие с результатом
        """
        atk_roll, def_roll, winner = self.resolve_duel_roll(attacker, defender)
        if winner:
            self.pending_events.append(GameEvent(
                type="DUEL_CHOOSE_REWARD",
                player=winner,
                data={
                    "loser": defender if winner == attacker else attacker,
                    "atk_roll": atk_roll,
                    "def_roll": def_roll
                }
            ))
        else:
            # надо тоже что-нибудь логировать тут
            pass

    @staticmethod
    def resolve_duel_roll(attacker: Player, defender: Player) -> Tuple[int, int, Player]:
        """
        Проводит броски для схватки.
        Возвращает: (бросок_атк + 2, бросок_деф, победитель)
        """
        atk_roll = random.randint(1, 6) + 2
        def_roll = random.randint(1, 6)

        winner = attacker if atk_roll > def_roll else defender
        if atk_roll == def_roll:
            winner = None  # Ничья

        return atk_roll, def_roll, winner

    def resolve_duel_reward_choice(self, winner: Player, loser: Player, reward_type: str, card_idx: int = -1):
        """Игрок выбрал награду за дуэль"""
        self.apply_duel_reward(winner, loser, reward_type, card_idx)

    def resolve_tornado_choice(self, victim: Player, choice_idx: int, target_pos: int):
        """
        :param victim: игрок, которого засасывает
        :param choice_idx: 0 - откупиться (10 монет), 1 - лететь к смерчу
        """
        if choice_idx == 0:
            if not victim.pay(10):
                victim.position = target_pos
        else:
            victim.position = target_pos

    def resolve_tadam_choice(self, rule: RuleCard):
        """Вызывается из UI после закрытия диалога с новым правилом"""
        self.state.add_rule(rule)

    def apply_duel_reward(self, winner: Player, loser: Player, reward_type: str, card_idx: int = -1):
        """
        Применяет выбранную победителем награду.
        reward_type: 'money', 'push', 'steal_card'
        """
        if reward_type == 'money':
            # Забрать 10 монет (или сколько есть)
            amount = min(loser.coins, 10)
            if loser.pay(amount):
                winner.add_coins(amount)

        elif reward_type == 'push':
            # Отпихнуть на 10 клеток назад
            self.move_player(loser, 10, is_forward=False)

        elif reward_type == 'steal_card':
            # Забрать карту Лавки Джо по индексу
            card = loser.remove_card(card_idx)
            if card:
                if not winner.add_card(card):
                    # Если у победителя нет места, карта уходит в сброс лавки
                    self.state.deck_shop.discard(card)

    def resolve_event_card(self, player: Player, card: EventCard, is_good: bool):
        """Разыгрывает карту из сундучка"""
        side = card.good_side if is_good else card.bad_side

        # Логируем карту ДО применения эффекта
        self.logger.log_event(player.uid, "EVENT_CARD", {
            "type": "Хорошо" if is_good else "Плохо",
            "name": side.name,
            "effect": side.effect_id,
            "value": side.value,
        })

        self.apply_effect(side.effect_id, player, side.value)
        self.state.deck_events.discard(card)

    def apply_effect(self, effect_id: str, source: Player, value: int = 0, target: Optional[Player] = None):
        """
        Маппинг строковых ID эффектов на код.
        :param target: Нужен для карт-атак (Гарпун, Воровство и т.д.)
        """

        # --- БАЗОВОЕ ДВИЖЕНИЕ И ДЕНЬГИ ---
        if effect_id == "gain_coins": source.add_coins(value)
        elif effect_id == "lose_coins": source.pay(value)
        elif effect_id == "move_self_forward": self.move_player(source, value)
        elif effect_id == "move_self_back": self.move_player(source, value, is_forward=False)
        elif effect_id == "no_effect": pass
        elif effect_id == "move_forward_gain_coins":
            self.move_player(source, value)
            source.add_coins(value)

        # --- СЛОЖНЫЕ ПЕРЕМЕЩЕНИЯ ---
        elif effect_id == "move_nearest_green":
            curr = source.position
            found = False
            for i in range(curr + 1, self.board.max_cell_id):
                if self.board.get_cell(i).type == CellType.GREEN:
                    self.move_player(source, i - curr)
                    found = True
                    break
            if not found: self.move_player(source, 3)  # Если впереди нет зеленой

        elif effect_id == "move_back_to_red_or_3":
            found = False
            for i in range(source.position - 1, -1, -1):
                if self.board.get_cell(i).type == CellType.RED:
                    source.position = i
                    found = True
                    break
            if not found: self.move_player(source, 3, is_forward=False)

        # --- ВЗАИМОДЕЙСТВИЕ С ИГРОКАМИ (МАССОВОЕ) ---
        elif effect_id == "pay_all_others_bank":
            for p in self.state.players:
                if p.uid != source.uid: p.add_coins(value)

        elif effect_id == "steal_coins_from_all":
            for p in self.state.players:
                if p.uid != source.uid:
                    if p.pay(value): source.add_coins(value)

        elif effect_id == "others_move_forward":
            for p in self.state.players:
                if p.uid != source.uid: self.move_player(p, value)

        elif effect_id == "all_lose_coins_global":
            for p in self.state.players: p.pay(value)

        elif effect_id == "others_gain_coins_move":
            for p in self.state.players:
                if p.uid != source.uid:
                    p.add_coins(value)
                    self.move_player(p, value)

        elif effect_id == "steal_2_from_all":
            for p in self.state.players:
                if p.uid != source.uid:
                    amount = min(p.coins, value)
                    if p.pay(amount):
                        source.add_coins(amount)

        elif effect_id == "draw_2_bad":
            for _ in range(2):
                card = self.state.deck_events.draw(1)[0]
                self.pending_events.append(GameEvent(
                    type="EVENT_CARD",
                    player=source,
                    data={"card": card, "is_good": False}
                ))

        # --- ЭФФЕКТЫ С ВЫБОРОМ (UI REQUIRED) ---
        elif effect_id == "give_double_turn_enemy":
            raise NotImplementedError("Событие 'благородство': требуется механика двойного хода в UI")

        elif effect_id == "pay_coins_move_flexible":
            raise NotImplementedError("Нужен ввод кол-ва монет (1-5) в UI")

        elif effect_id == "place_mines":
            raise NotImplementedError("Нужен выбор клеток для размещения мин в UI")

        elif effect_id == "tax_shop_cards":
            raise NotImplementedError("Событие 'налог на имущество': Диалог оплаты/сброса для каждой карты в руке")

        elif effect_id == "all_discard_to_one_shop_card":
            raise NotImplementedError("Событие 'инвентаризация': Групповое событие сброса лишних карт")

        elif effect_id == "draw_2_keep_1_free":
            raise NotImplementedError("Событие 'подарок Джо': Генерация события SHOP с ценой 0")

        elif effect_id == "pay_coins_move_others_back":
            raise NotImplementedError("Событие 'саботаж': Выбор суммы сброса и расчет отката врагов")

        elif effect_id == "skip_turn_mutual":
            raise NotImplementedError("Событие 'общая задержка': Выбор цели для совместного пропуска хода")

        elif effect_id == "discard_shop_or_red":
            if source.hand:
                raise NotImplementedError("Нужен выбор карты Лавки Джо для сброса в UI")
            else:
                self.apply_effect("move_back_to_red_or_3", source)

        elif effect_id == "extra_turn_pay_coins":
            raise NotImplementedError("Выбор сбрасывать две монеты или нет")

        # --- РАНДОМ И КУБИКИ ---
        elif effect_id == "roll_lose_coins_or_move_back":
            roll = random.randint(1, 6)
            if roll <= 3: source.pay(5)
            else: self.move_player(source, 10, is_forward=False)

        elif effect_id == "roll_gamble_money_move":
            roll = random.randint(1, 6)
            if roll <= 3: source.add_coins(10)
            else: self.move_player(source, 5)

        # target required
        elif effect_id in ["steal_coins_target", "force_enemy_draw_bad", "discard_enemy_shop_card", "roll_push_enemy",
                           "give_5_to_target", "give_10_to_target", "force_enemy_lose_coins", "give_double_turn_enemy",
                           "steal_shop_card_leader"]:
            if effect_id == "steal_shop_card_leader":
                opponents = [p for p in self.state.players if p.uid != source.uid and p.position > source.position]
                if not opponents:
                    return
            else:
                opponents = [p for p in self.state.players if p.uid != source.uid]

            if target:
                self._execute_targeted_logic(effect_id, source, target, value)
                return

            if len(opponents) == 1:
                self._execute_targeted_logic(effect_id, source, opponents[0], value)
            else:
                self.pending_events.append(GameEvent(
                    type="CHOOSE_TARGET",
                    player=source,
                    data={'effect_id': effect_id, "value": value, "opponents": opponents}
                ))

        # --- ТА-ДАМ ГЛОБАЛЬНЫЕ ПРАВИЛА ---
        elif effect_id == "rule_red_choice":
            raise NotImplementedError("Та-Дам: Выбор -3 монеты или -3 шага в UI")

        elif effect_id == "rule_last_player_income":
            if self._is_last(source): source.add_coins(value)
        else:
            print(f"DEBUG: Эффект {effect_id} еще не имеет реализации.")

    def _execute_targeted_logic(self, effect_id: str, source: Player, target: Player, value: int):
        if effect_id == "steal_coins_target":
            amount = min(target.coins, value)
            if target.pay(amount):
                source.add_coins(amount)
                self.logger.log_event(source.uid, "EFFECT_STEAL", {
                    "from": target.name,
                    "target_uid": target.uid,
                    "amount": amount
                })

        elif effect_id == "force_enemy_draw_bad":
            card = self.state.deck_events.draw(1)[0]
            self.pending_events.append(GameEvent(
                type="EVENT_CARD",
                player=target,
                data={"card": card, "is_good": False}
            ))
            self.logger.log_event(source.uid, "EFFECT_FORCE_DRAW_BAD", {
                "target": target.name,
                "target_uid": target.uid,
                "card": card.bad_side.name
            })

        elif effect_id == "discard_enemy_shop_card":
            if not target.hand:
                print(f"У игрока {target.name} нет карт для сброса")
                return

            if len(target.hand) == 1:
                card = target.remove_card(0)
                self.state.deck_shop.discard(card)
                self.logger.log_event(source.uid, "EFFECT_DISCARD", {
                    "target": target, "card": card.name
                })
            else:
                self.pending_events.append(GameEvent(
                    type="CHOOSE_CARD_TO_DISCARD",
                    player=source,
                    data={"target": target, "cards": target.hand}
                ))

        elif effect_id == "roll_push_enemy":
            if not target:
                opponents = [p for p in self.state.players if p.uid != source.uid]
                if len(opponents) == 1:
                    target = opponents[0]
                else:
                    self.pending_events.append(GameEvent(
                        type="CHOOSE_TARGET",
                        player=source,
                        data={'effect_id': effect_id, "value": 0, "opponents": opponents}
                    ))
                    return

            roll = random.randint(1, 6)
            self.move_player(target, roll)
            self.logger.log_event(source.uid, "EFFECT_PUSH", {
                "target": target.name, "roll": roll
            })

        elif effect_id == "give_5_to_target" or effect_id == "give_10_to_target":
            if value == 10: target.add_coins(value)
            elif source.pay(value):
                target.add_coins(value)
                self.logger.log_event(source.uid, "EFFECT_GIVE", {
                    "to": target.name, "amount": value
                })
            else:
                amount = source.coins
                source.pay(amount)
                target.add_coins(amount)
                self.logger.log_event(source.uid, "EFFECT_GIVE", {
                    "to": target.name, "amount": amount
                })

        elif effect_id == "force_enemy_lose_coins":
            opponents = [p for p in self.state.players if p.uid != source.uid]
            if target:
                target.pay(value)
                self.logger.log_event(source.uid, "EFFECT_FORCE_LOSE", {
                    "target": target.name, "amount": value
                })
            elif len(opponents) == 1:
                opponents[0].pay(value)
            else:
                self.pending_events.append(GameEvent(
                    type="CHOOSE_TARGET",
                    player=source,
                    data={'effect_id': effect_id, "value": value, "opponents": opponents}
                ))

        elif effect_id == "give_double_turn_enemy":
            raise NotImplementedError("Событие 'благородство': требуется механика двойного хода в UI")

        elif effect_id == "steal_shop_card_leader":
            if not target.hand:
                return

            if len(target.hand) == 1:
                card = target.remove_card(0)
                if source.add_card(card):
                    self.logger.log_event(source.uid, "EFFECT_STEAL_CARD", {
                        "target": target.name, "card": card.name
                    })
                else:
                    self.state.deck_shop.discard(card)
            else:
                self.pending_events.append(GameEvent(
                    type="CHOOSE_CARD_TO_DISCARD",
                    player=source,
                    data={"target": target, "cards": target.hand}
                ))

    def resolve_target_choice(self, source: Player, target_uid: int, effect_id: str, value: int):
        target = next(p for p in self.state.players if p.uid == target_uid)
        self._execute_targeted_logic(effect_id, source, target, value)

    def resolve_discard_enemy_card(self, source: Player, target: Player, card_idx: int):
        card = target.remove_card(card_idx)
        self.logger.log_event(source.uid, "EFFECT_DISCARD_CHOICE", {
            "target": target.name, "card": card.name
        })

    def use_card_from_hand(self, player_idx: int, card_idx: int, target_idx: Optional[int] = None) -> bool:
        player = self.state.players[player_idx]
        card = player.hand[card_idx]
        target = self.state.players[target_idx] if target_idx is not None else None

        # Пассивные карты нельзя активировать кнопкой
        if card.is_passive: return False

        if card_idx in player.used_cards_indices: return False
        if not player.pay(card.use_cost): return False

        eid = card.effect_id
        if eid == "attack_grenade" and target:
            self.move_player(target, card.value, is_forward=False)
        elif eid == "attack_voodoo" and target:
            card = self.state.deck_events.draw(1)[0]
            self.pending_events.append(GameEvent(
                type="EVENT_CARD",
                player=target,
                data={"card": card, "is_good": False}
            ))
        elif eid == "move_rocket":
            self.move_player(player, card.value)
        elif eid == "attack_hand_fate" and target:
            # На 2 назад (на 1 если мало игроков)
            steps = 1 if len(self.state.players) <= 3 else 2
            self.move_player(target, steps, is_forward=False)
        elif eid == "attack_hook" and target:
            # Притянуть к себе
            if 0 < (target.position - player.position) <= 10:
                target.position = player.position
        elif eid == "move_harpoon" and target:
            # Прыгнуть к нему
            if 0 < (target.position - player.position) <= 10:
                player.position = target.position

        player.mark_card_used(card_idx)
        return True

    def attempt_finish(self, player: Player):
        """Попытка открыть сейф в конце игры."""
        if not player.is_finished: return
        roll = random.randint(1, 6)
        # Тут можно добавить механику доплаты монет за +1 к кубику
        if roll >= WINNING_ROLL:
            self.is_game_over = True
            self.winner = player

    def _get_last_players(self) -> List[Player]:
        """Возвращает список игроков, находящихся дальше всех от финиша."""
        min_pos = min(p.position for p in self.state.players)
        return [p for p in self.state.players if p.position == min_pos]

    def _is_last(self, player: Player) -> bool:
        return player in self._get_last_players()
