import pygame
from game_core.ai import RandomAIPlayer
from game_core.engine import GameEngine, GameEvent
from game_core.logger import GameLogger
from game_core.state import Player
from ui.renderer import Renderer
from ui.view_config import ViewConfig
from ui.ui_state import UIState
from ui.components import Dialog, SliderDialog
from typing import Protocol, List


WINDOW_SIZE = 1000
AI_CARD_SHOW_MS = 1500


class _EventHandler(Protocol):
    def __call__(self, ev: GameEvent, ep: Player) -> None: ...


class GameSession:
    def __init__(self, screen: pygame.Surface, logger: GameLogger, players: List[Player]):
        self.logger = logger
        self.engine = GameEngine(logger, players)
        self.ui = UIState()

        view_cfg = ViewConfig("ui/coords.json", target_size=WINDOW_SIZE)
        raw_board = pygame.image.load("assets/field_corrected.png").convert()
        board_img = pygame.transform.smoothscale(raw_board, (WINDOW_SIZE, WINDOW_SIZE))
        self.renderer = Renderer(screen, view_cfg, board_img)
        self.view_cfg = view_cfg
        self.screen = screen

        for p in players:
            if isinstance(p, RandomAIPlayer):
                p.logger = logger

    @property
    def p(self):
        return self.engine.state.current_player

    @property
    def p_idx(self):
        return self.engine.state.current_player_idx

    def _is_ai(self, player: Player = None) -> bool:
        return isinstance(player or self.p, RandomAIPlayer)

    def tick(self, events: list, mouse_pos: tuple, elapsed_seconds: int, turn_count: int):
        self._process_pending_events()

        # Авто-закрытие карты события по таймеру (AI-игрок)
        ui = self.ui
        if (ui.showing_event_card_sidebar
                and ui.event_card_auto_close_at is not None
                and pygame.time.get_ticks() >= ui.event_card_auto_close_at):
            ev = self.engine.pending_events[0]
            self.engine.resolve_event_card(ev.player, ui.pending_event_card, ui.pending_event_is_good)
            self.engine.pending_events.pop(0)
            ui.pending_event_card = None
            ui.showing_event_card_sidebar = False
            ui.event_card_ok_rect = None
            ui.event_card_auto_close_at = None

        if not self.ui.is_busy and not self.engine.pending_events:
            self.engine.try_advance_turn(self.p)

        if self._is_ai() and not self.ui.is_busy:
            self._ai_tick()

        self.handle_input(events, mouse_pos)
        self.draw(mouse_pos, elapsed_seconds, turn_count)

    # ------------------------------------------------------------------
    # AI тик — принимает решения вместо UI
    # ------------------------------------------------------------------

    def _ai_tick(self):
        p = self.p
        eng = self.engine
        ai: RandomAIPlayer = p  # type: ignore

        if self.ui.is_busy:
            return

        # Ход не начат - решаем: карта или кубики
        if not p.has_moved and p.turn_checks_done and not eng.pending_events:
            opponents = [o for o in eng.state.players if o.uid != p.uid]
            decision = ai.decide_pre_roll_action(opponents)

            if decision[0] == "use":
                _, card_idx, target_idx = decision
                eng.use_card_from_hand(self.p_idx, card_idx, target_idx=target_idx)
            else:
                if p.is_finished:
                    eng.pending_events.append(GameEvent(type="FINISH_ROLL", player=p, data={}))
                    p.has_moved = True
                else:
                    rolls = eng.get_roll(p)
                    options = eng.get_move_options(p, rolls)
                    chosen = options[ai.decide_move_option(options)]
                    eng.move_player(p, chosen, is_own_move=True)
            return

        # После хода - карты или завершение
        if p.has_moved and not eng.pending_events:
            if eng.can_player_do_actions(p):
                opponents = [o for o in eng.state.players if o.uid != p.uid]
                decision = ai.decide_pre_roll_action(opponents)
                if decision[0] == "use":
                    _, card_idx, target_idx = decision
                    eng.use_card_from_hand(self.p_idx, card_idx, target_idx=target_idx)
                    return
                # "roll" здесь означает "не использовать карты, завершить ход"

            if not p.end_checks_done:
                eng.end_turn_checks(p)
                p.end_checks_done = True
            if not eng.pending_events:
                if p.has_extra_turn > 0:
                    p.has_extra_turn -= 1
                    p.reset_turn_flags()
                else:
                    eng.state.next_turn(self.logger)

    # ------------------------------------------------------------------
    # Обработка очереди событий движка
    # ------------------------------------------------------------------

    def _process_pending_events(self):
        ui, eng = self.ui, self.engine
        if not eng.pending_events or ui.is_busy:
            return

        ev = eng.pending_events[0]
        ep = ev.player

        handlers: dict[str, _EventHandler] = {
            "SLIDER_INPUT":           self._open_slider,
            "SHOP":                   self._open_shop,
            "SHOP_FREE":              self._open_shop_free,
            "SHOP_GIVE":              self._resolve_shop_give,
            "EVENT_CARD":             self._open_event_card,
            "FINISH_ROLL":            self._open_finish_roll,
            "RED_CHOICE":             self._open_red_choice,
            "TADAM_SHOW":             self._open_tadam,
            "DUEL_CHOOSE_OPPONENT":   self._open_duel_choose_opponent,
            "DUEL_CHOOSE_REWARD":     self._open_duel_reward,
            "TORNADO_DECISION":       self._open_tornado,
            "CHOOSE_TARGET":          self._open_choose_target,
            "MINE_PLACEMENT":         self._open_mine_placement,
            "INVENTORY_KEEP":         self._open_inventory_keep,
            "TAX_SHOP_CARD":          self._open_tax_shop_card,
            "CHOOSE_CARD_TO_DISCARD": self._open_choose_card_to_discard,
            "SWAP_CARD":              self._open_swap_card,
        }
        handler = handlers.get(ev.type)
        if handler:
            handler(ev, ep)

    # ------------------------------------------------------------------
    # Открытие диалогов / авто-решение для AI
    # ------------------------------------------------------------------

    def _open_slider(self, ev, ep):
        if self._is_ai(ep):
            d = ev.data
            value = ep.decide_slider(d["max_value"])
            self.engine.resolve_slider_input(ep, value, {
                "effect_id": d["effect_id"],
                "multiplier": d["multiplier"],
                "target_self": d.get("target_self", True)
            })
            self.engine.pending_events.pop(0)
            return
        d = ev.data
        self.ui.active_slider = SliderDialog(d["title"], d["description"], d["max_value"], d["multiplier"])

    def _open_shop(self, ev, ep):
        if self._is_ai(ep):
            choice = ep.decide_shop()
            self.engine.resolve_shop_choice(ep, ev.data["cards"], choice)
            self.engine.pending_events.pop(0)
            return
        self.ui.pending_shop_cards = ev.data["cards"]

    def _open_shop_free(self, ev, ep):
        if self._is_ai(ep):
            choice = ep.decide_shop_free()
            self.engine.resolve_shop_free_choice(ep, ev.data["cards"], choice)
            self.engine.pending_events.pop(0)
            return
        self.ui.pending_shop_cards = ev.data["cards"]

    def _resolve_shop_give(self, ev, ep):
        card = ev.data["card"]
        self.engine.give_card_to_player(ep, card)
        self.engine.logger.log_event(ep.uid, "SHOP_FREE", {"card": card.name})
        self.engine.pending_events.pop(0)

    def _open_event_card(self, ev, ep):
        ui = self.ui
        ui.pending_event_card = ev.data["card"]
        ui.pending_event_is_good = ev.data["is_good"]
        ui.showing_event_card_sidebar = True
        if self._is_ai(ep):
            ui.event_card_auto_close_at = pygame.time.get_ticks() + AI_CARD_SHOW_MS
        else:
            ui.event_card_auto_close_at = None

    def _open_finish_roll(self, ev, ep):
        if self._is_ai(ep):
            choice = ep.decide_finish_roll()
            bonus_map = {0: 0, 1: 5, 2: 10}
            roll, bonus, total, success = self.engine.attempt_finish(ep, bonus_map[choice])
            self.engine.pending_events.pop(0)
            self.logger.log_event(ep.uid, "AI_FINISH_ROLL", {
                "roll": roll, "bonus": bonus, "total": total, "success": success
            })
            return
        if ep.coins < 5:
            roll, bonus, total, success = self.engine.attempt_finish(ep, 0)
            self.engine.pending_events.pop(0)
            result_text = f"Выпало {roll} = {total}"
            result_text += " — ПОБЕДА!" if success else " — Не хватило... (нужно 6+)"
            self.ui.active_dialog = Dialog(result_text, ["ОК"])
            self.ui.pending_finish_result = (roll, bonus, total, success)
        else:
            opts = ["Бросить (без бонуса)", "Сбросить 5 монет (+1 к броску)"]
            if ep.coins >= 10: opts.append("Сбросить 10 монет (+2 к броску)")
            self.ui.active_dialog = Dialog(f"{ep.name}: Финиш-сейф! Нужно 6+", opts)

    def _open_red_choice(self, _ev, ep):
        if self._is_ai(ep):
            choice = ep.decide_red_choice()
            if choice == 0:
                ep.pay(3)
            else:
                self.engine.move_player(ep, 3, is_forward=False)
                self.engine.logger.log_event(ep.uid, "RED_CHOICE", {"choice": ["lose_coins", "move_back"][choice]})
            self.engine.pending_events.pop(0)
            return
        self.ui.active_dialog = Dialog(f"{ep.name}: Красная западня",
                                       ["Потерять 3 монеты", "Назад на 3 клетки"])

    def _open_tadam(self, ev, ep):
        if self._is_ai(ep):
            # AI мгновенно принимает новое правило
            self.engine.resolve_tadam_choice(ev.data["rule"])
            self.engine.pending_events.pop(0)
            return
        self.ui.pending_tadam_rule = ev.data["rule"]
        self.ui.viewing_card_sprite_id = self.ui.pending_tadam_rule.sprite_id

    def _open_duel_choose_opponent(self, ev, ep):
        if self._is_ai(ep):
            opponents = ev.data["opponents"]
            idx = ep.decide_duel_opponent(opponents)
            self.engine.resolve_duel_opponent(ep, opponents[idx])
            self.engine.pending_events.pop(0)
            return
        opts = [f'Драться с {o.name}' for o in ev.data["opponents"]]
        self.ui.active_dialog = Dialog(f"{ep.name}: Выбери противника для схватки", opts)

    def _open_duel_reward(self, ev, ep):
        if self._is_ai(ep):
            loser = ev.data["loser"]
            reward = ep.decide_duel_reward(bool(loser.hand))
            self.engine.resolve_duel_reward_choice(ep, loser, reward)
            self.engine.pending_events.pop(0)
            return
        self.ui.duel_defender = ev.data["loser"]
        opts = ["Забрать 10 монет", "Откинуть на 10 клеток"]
        if self.ui.duel_defender.hand:
            opts.append("Забрать карту Лавки")
        self.ui.active_dialog = Dialog(
            f"{ep.name}: Победа! ({ev.data['atk_roll']} vs {ev.data['def_roll']})", opts)

    def _open_tornado(self, ev, ep):
        if self._is_ai(ep):
            choice = ep.decide_tornado()
            self.engine.resolve_tornado_choice(ep, choice, ev.data["target_pos"])
            self.engine.pending_events.pop(0)
            return
        self.ui.pending_tornado_target = ev.data["target_pos"]
        if ep.coins >= 10:
            self.ui.active_dialog = Dialog(f"Смерч: {ep.name}", ["Откупиться (10 монет)", "Лететь к Смерчу!"])
        else:
            self.engine.resolve_tornado_choice(ep, 1, ev.data["target_pos"])
            self.engine.pending_events.pop(0)

    def _open_choose_target(self, ev, ep):
        if self._is_ai(ep):
            opponents = ev.data["opponents"]
            idx = ep.decide_target(opponents)
            self.engine.resolve_target_choice(ep, opponents[idx].uid,
                                              ev.data["effect_id"], ev.data["value"])
            self.engine.pending_events.pop(0)
            return
        opts = [o.name for o in ev.data["opponents"]]
        self.ui.active_dialog = Dialog(f"{ep}: Выбери цель", opts)

    def _open_mine_placement(self, ev, ep):
        if self._is_ai(ep):
            all_cell_ids = [cid for cid in self.engine.board.cells.keys()]
            enemy_positions = [o.position for o in self.engine.state.players if o.uid != ep.uid]
            chosen_cells = ep.decide_mine_placement(all_cell_ids, enemy_positions)
            for cell_id in chosen_cells:
                if ep.coins > 0 and cell_id not in self.engine.placed_mines:
                    ep.pay(1)
                    self.engine.placed_mines[cell_id] = ep.uid
                    self.logger.log_event(ep.uid, "MINE_PLACED", {"cell": cell_id})
            self.engine.pending_events.pop(0)
            return
        self.ui.mine_placement_mode = True
        self.ui.mine_placement_player = ep
        self.engine.pending_events.pop(0)

    def _open_inventory_keep(self, ev, ep):
        if self._is_ai(ep):
            idx = ep.decide_inventory_keep(ev.data["cards"])
            self.engine.resolve_inventory_keep(ep, idx)
            self.engine.pending_events.pop(0)
            return
        self.ui.pending_shop_cards = ev.data["cards"]

    def _open_tax_shop_card(self, ev, ep):
        if self._is_ai(ep):
            card_idx = ev.data["card_idx"]
            cost = ev.data["cost"]
            # Пока в руке есть карты для налога
            while card_idx < len(ep.hand):
                card = ep.hand[card_idx]
                choice = ep.decide_tax_card(ep.can_afford(cost))
                if choice == 0 and ep.pay(cost):
                    card_idx += 1
                else:
                    self.engine.state.deck_shop.discard(ep.remove_card(card_idx))
            self.engine.pending_events.pop(0)
            return
        card_idx = ev.data["card_idx"]
        cost = ev.data["cost"]
        if card_idx >= len(ep.hand):
            self.engine.pending_events.pop(0)
            return
        card = ep.hand[card_idx]
        self.ui.active_dialog = Dialog(
            f"{ep.name}: Налог — «{card.name.upper()}»",
            [f"Заплатить {cost} монет (есть: {ep.coins})", "Сбрось карту"]
        )

    def _open_choose_card_to_discard(self, ev, ep):
        if self._is_ai(ep):
            idx = ep.decide_card_to_discard(ev.data["cards"])
            self.engine.resolve_discard_enemy_card(ep, ev.data["target"], idx,
                                                   steal=ev.data.get("steal", False))
            self.engine.pending_events.pop(0)
            return
        self.ui.pending_shop_cards = ev.data["cards"]

    def _open_swap_card(self, ev, ep):
        new_card = ev.data["new_card"]
        if self._is_ai(ep):
            replace_idx = ep.decide_swap(len(ep.hand))
            self.engine.resolve_swap_card(ep, new_card, replace_idx if replace_idx < len(ep.hand) else None)
            self.engine.pending_events.pop(0)
            return
        # для человека — показываем текущую руку, даём выбрать что заменить
        self.ui.pending_shop_cards = list(ep.hand)

    # ------------------------------------------------------------------
    # Обработка ввода (только для людей)
    # ------------------------------------------------------------------

    def handle_input(self, events: list, mouse_pos: tuple):
        for event in events:
            if event.type == pygame.QUIT:
                return False

            if self.ui.showing_event_card_sidebar:
                ev = self.engine.pending_events[0] if self.engine.pending_events else None
                card_owner_is_ai = ev is not None and self._is_ai(ev.player)
                if not card_owner_is_ai:
                    self._handle_event_card_sidebar(event)
                continue  # всё остальное пока карта на экране не нужно

            if self._is_ai() and not self.ui.active_dialog:
                continue

            if self.ui.active_slider:
                self._handle_slider(event, mouse_pos)
                continue

            if self.ui.viewing_card_sprite_id:
                self._handle_card_view(event)
                continue

            if self.ui.showing_event_card_sidebar:
                self._handle_event_card_sidebar(event)
                continue

            ev = self.engine.pending_events[0] if self.engine.pending_events else None
            if ev and ev.type in ("SHOP", "SHOP_FREE", "CHOOSE_CARD_TO_DISCARD", "INVENTORY_KEEP"):
                self._handle_card_selection(event, mouse_pos, ev)
                continue

            if self.ui.mine_placement_mode:
                self._handle_mine_placement(event, mouse_pos)
                continue

            if self.ui.active_dialog:
                self._handle_dialog(event)
                continue

            self._handle_default(event, mouse_pos)

        return True

    def _handle_slider(self, event, mouse_pos):
        ui, eng = self.ui, self.engine
        result = ui.active_slider.handle_event(event, mouse_pos)
        if result:
            action, value = result
            ev = eng.pending_events[0]
            if action == 'confirm':
                eng.resolve_slider_input(ev.player, value, {
                    "effect_id": ev.data["effect_id"],
                    "multiplier": ev.data["multiplier"],
                    "target_self": ev.data.get("target_self", True)
                })
                eng.pending_events.pop(0)
            else:
                eng.pending_events.pop(0)
                self.logger.log_event(ev.player.uid, "SLIDER_CANCELLED", {})
            ui.active_slider = None

    def _handle_card_view(self, event):
        ui, eng = self.ui, self.engine
        close = (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or \
                (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE)
        if close:
            if ui.pending_tadam_rule:
                eng.resolve_tadam_choice(ui.pending_tadam_rule)
                eng.pending_events.pop(0)
                ui.pending_tadam_rule = None
            ui.viewing_card_sprite_id = None

    def _handle_event_card_sidebar(self, event):
        ui, eng = self.ui, self.engine
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if ui.event_card_ok_rect and ui.event_card_ok_rect.collidepoint(event.pos):
            ev = eng.pending_events[0]

            # Запоминаем сколько событий было ПОСЛЕ текущего
            events_after = len(eng.pending_events) - 1

            eng.resolve_event_card(ev.player, ui.pending_event_card, ui.pending_event_is_good)
            eng.pending_events.pop(0)

            # Если эффект карты породил новые события — вытаскиваем их в начало очереди
            if len(eng.pending_events) > events_after:
                newly_added = eng.pending_events[events_after:]
                pre_planned = eng.pending_events[:events_after]
                eng.pending_events = newly_added + pre_planned

            ui.pending_event_card = None
            ui.showing_event_card_sidebar = False
            ui.event_card_ok_rect = None

    def _handle_card_selection(self, event, mouse_pos, ev):
        ui, eng = self.ui, self.engine
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        for i, rect in enumerate(ui.pending_selection_rects):
            if not rect.collidepoint(mouse_pos):
                continue
            is_skip = ev.type == "SHOP" and i == len(ui.pending_selection_rects) - 1
            choice = 2 if is_skip else i
            if ev.type == "SHOP":
                eng.resolve_shop_choice(self.p, ui.pending_shop_cards, choice)
            elif ev.type == "SHOP_FREE":
                eng.resolve_shop_free_choice(self.p, ui.pending_shop_cards, choice)
            elif ev.type == "CHOOSE_CARD_TO_DISCARD":
                eng.resolve_discard_enemy_card(self.p, ev.data["target"], choice,
                                               steal=ev.data.get("steal", False))
            elif ev.type == "INVENTORY_KEEP":
                actual = choice if choice < len(ui.pending_shop_cards) else 0
                eng.resolve_inventory_keep(ev.player, actual)
            elif ev.type == "SWAP_CARD":
                new_card = ev.data["new_card"]
                is_skip = (i == len(ui.pending_shop_cards))  # последняя кнопка — «Пропустить»
                replace_idx = None if is_skip else i
                self.engine.resolve_swap_card(ev.player, new_card, replace_idx)
            eng.pending_events.pop(0)
            ui.clear_card_selection()
            break

    def _handle_mine_placement(self, event, mouse_pos):
        ui, eng = self.ui, self.engine
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        finish_btn = pygame.Rect(WINDOW_SIZE + 30, 820, 240, 55)
        if finish_btn.collidepoint(mouse_pos):
            ui.mine_placement_mode = False
            ui.mine_placement_player = None
            return
        if mouse_pos[0] < WINDOW_SIZE and ui.mine_placement_player.coins > 0:
            cell_id = self.view_cfg.get_cell_under_mouse(mouse_pos, radius=35)
            if cell_id != -1:
                cell_id = int(cell_id)
                if cell_id not in eng.placed_mines:
                    ui.mine_placement_player.pay(1)
                    eng.placed_mines[cell_id] = ui.mine_placement_player.uid
                    self.logger.log_event(ui.mine_placement_player.uid, "MINE_PLACED", {"cell": cell_id})
        if ui.mine_placement_player and ui.mine_placement_player.coins <= 0:
            ui.mine_placement_mode = False
            ui.mine_placement_player = None

    def _handle_dialog(self, event):
        # Логика разветвления по типу диалога — перенесена 1-в-1 из main.py
        ui, eng = self.ui, self.engine
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        for i, btn in enumerate(ui.active_dialog.buttons):
            if not btn.is_clicked(event.pos):
                continue
            self._dispatch_dialog_click(i)
            break

    def _dispatch_dialog_click(self, i: int):
        """Разветвление по заголовку активного диалога"""
        ui, eng = self.ui, self.engine
        title = ui.active_dialog.title
        ev = eng.pending_events[0] if eng.pending_events else None
        ep = ev.player if ev else self.p

        if "Выбери ход" in title:
            eng.move_player(self.p, ui.pending_move_options[i], is_own_move=True)
            ui.clear_dialog()
        elif "противника" in title:
            eng.resolve_duel_opponent(self.p, ev.data["opponents"][i])
            ui.clear_dialog(); eng.pending_events.pop(0)
        elif "Победа!" in title:
            reward_types = ["money", "push"] + (["steal_card"] if ui.duel_defender.hand else [])
            eng.resolve_duel_reward_choice(ep, ui.duel_defender, reward_types[i])
            ui.clear_dialog(); eng.pending_events.pop(0)
        elif "Финиш-сейф" in title:
            self._resolve_finish_roll(i, ep, ev)
        elif "западня" in title:
            if i == 0:
                ep.pay(3)
            else:
                eng.move_player(ep, 3, is_forward=False)
            eng.logger.log_event(ep.uid, "RED_CHOICE", {"choice": ["lose_coins", "move_back"][i]})
            ui.clear_dialog(); eng.pending_events.pop(0)
        elif "Смерч" in title:
            eng.resolve_tornado_choice(ep, i, ui.pending_tornado_target)
            ui.clear_dialog(); eng.pending_events.pop(0)
        elif "Выбери цель" in title:
            eng.resolve_target_choice(self.p, ev.data["opponents"][i].uid,
                                      ev.data["effect_id"], ev.data["value"])
            ui.clear_dialog(); eng.pending_events.pop(0)
        elif "Налог" in title:
            self._resolve_tax(i, ep, ev)
        elif "Выбери цель для" in title:
            opponents = [o for o in eng.state.players if o.uid != self.p.uid]
            eng.use_card_from_hand(self.p_idx, ui.pending_card_use_idx, target_idx=opponents[i].uid)
            ui.pending_card_use_idx = None; ui.clear_dialog()
        elif ui.pending_finish_result and ui.active_dialog.buttons[i].text == "ОК":
            ui.pending_finish_result = None
            ui.clear_dialog()

    def _resolve_finish_roll(self, choice_idx, ep, _ev):
        ui, eng = self.ui, self.engine
        bonus_map = {0: 0, 1: 5, 2: 10}
        roll, bonus, total, success = eng.attempt_finish(ep, bonus_map.get(choice_idx, 0))
        eng.pending_events.pop(0)
        result_text = f"Выпало {roll}" + (f"+{bonus}" if bonus else "") + f" = {total}"
        result_text += " — ПОБЕДА!" if success else " — Не хватило... (нужно 6+)"
        ui.active_dialog = Dialog(result_text, ["ОК"])
        ui.pending_finish_result = (roll, bonus, total, success)

    def _resolve_tax(self, choice_idx, ep, ev):
        ui, eng = self.ui, self.engine
        card_idx = ev.data["card_idx"]
        cost = ev.data["cost"]
        if choice_idx == 0:
            if not ep.pay(cost):
                eng.state.deck_shop.discard(ep.remove_card(card_idx))
            else:
                card_idx += 1
        else:
            eng.state.deck_shop.discard(ep.remove_card(card_idx))
        ev.data["card_idx"] = card_idx
        if card_idx >= len(ep.hand):
            eng.pending_events.pop(0)
        ui.clear_dialog()

    def _handle_default(self, event, mouse_pos):
        eng, ui = self.engine, self.ui
        p, p_idx = self.p, self.p_idx

        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if not eng.pending_events and not p.has_moved and p.turn_checks_done:
                if p.is_finished:
                    eng.pending_events.append(GameEvent(type="FINISH_ROLL", player=p, data={}))
                    p.has_moved = True
                else:
                    rolls = eng.get_roll(p)
                    options = eng.get_move_options(p, rolls)
                    if len(options) > 1:
                        ui.pending_move_options = options
                        ui.active_dialog = Dialog("Выбери ход", [f"Идти на {o}" for o in options])
                    else:
                        eng.move_player(p, options[0], is_own_move=True)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Кнопка завершения хода
            if p.has_moved and not eng.pending_events:
                if ui.end_turn_btn_rect and ui.end_turn_btn_rect.collidepoint(mouse_pos):
                    if not p.end_checks_done:
                        eng.end_turn_checks(p)
                        p.end_checks_done = True
                    if not eng.pending_events:
                        if p.has_extra_turn > 0:
                            p.has_extra_turn -= 1
                            p.reset_turn_flags()
                        else:
                            eng.state.next_turn(self.logger)
                    return

            # Клик по карте в сайдбаре
            if mouse_pos[0] > WINDOW_SIZE:
                for j, rect in enumerate(ui.sidebar_card_rects):
                    if rect.collidepoint(mouse_pos):
                        card = p.hand[j]
                        if card.is_passive: break
                        opponents = [o for o in eng.state.players if o.uid != p.uid]
                        if len(opponents) == 1:
                            eng.use_card_from_hand(p_idx, j, target_idx=opponents[0].uid)
                        else:
                            ui.pending_card_use_idx = j
                            ui.active_dialog = Dialog(f"Выбери цель для «{card.name}»",
                                                      [o.name for o in opponents])
                        break

            # Клик по карте Та-Дам на доске
            if not ui.active_dialog:
                for i, rule in enumerate(eng.state.active_rules):
                    slot_key = f'slot_{i}'
                    pos = self.view_cfg.get_screen_coords(slot_key)
                    sprite = self.renderer.rule_sprites_small[rule.sprite_id]
                    if sprite.get_rect(center=pos).collidepoint(mouse_pos):
                        ui.viewing_card_sprite_id = rule.sprite_id
                        ui.pending_tadam_rule = None
                        break

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------

    def draw(self, mouse_pos: tuple, elapsed_seconds: int, turn_count: int):
        ui, eng = self.ui, self.engine
        r = self.renderer

        self.screen.fill((30, 30, 30))
        r.draw_board()
        r.draw_active_rules(eng.state.active_rules)
        r.draw_mines(eng.placed_mines)
        r.draw_players(eng.state)

        if ui.viewing_card_sprite_id:
            r.draw_large_rule_card(ui.viewing_card_sprite_id, mouse_pos)
        elif eng.pending_events and eng.pending_events[0].type in (
                "SHOP", "SHOP_FREE", "CHOOSE_CARD_TO_DISCARD", "INVENTORY_KEEP", "SWAP_CARD"):
            ev = eng.pending_events[0]
            if ev.type == "SHOP":
                title = "Лавка Джо: выбери карту (5 монет)"
            elif ev.type == "SHOP_FREE":
                title = "Бесплатная карта Лавки Джо"
            elif ev.type == "CHOOSE_CARD_TO_DISCARD":
                title = f"Сбрось карту у {ev.data['target'].name}"
            elif ev.type == "SWAP_CARD":
                title = f"Выбери карту для замены на «{ev.data['new_card'].name}»"
            else:
                title = f"Инвентаризация: {ev.player.name} — выбери карту, которую оставишь"
            ui.pending_selection_rects = r.draw_card_selector(
                ev.data["cards"] if ev.type != "SWAP_CARD" else list(ev.player.hand),
                title, mouse_pos,
                show_skip=(ev.type not in ("CHOOSE_CARD_TO_DISCARD", "SHOP_FREE"))
                # «Пропустить» есть везде кроме принудительного сброса
            )
        else:
            r.draw_hover(mouse_pos)
            if ui.active_slider: ui.active_slider.draw(self.screen, mouse_pos)
            elif ui.active_dialog: ui.active_dialog.draw(self.screen)

        can_act = eng.can_player_do_actions(self.p) if self.p.has_moved else False
        has_pending = bool(eng.pending_events or ui.active_dialog or ui.active_slider
                          or ui.viewing_card_sprite_id or ui.mine_placement_mode)
        ui.end_turn_btn_rect, ui.sidebar_card_rects = r.draw_sidebar(
            eng.state, turn_count, elapsed_seconds, can_act, has_pending)

        if ui.mine_placement_mode and ui.mine_placement_player:
            r.draw_mine_placement_button(ui.mine_placement_player.coins, mouse_pos)

        if ui.showing_event_card_sidebar and ui.pending_event_card:
            ui.event_card_ok_rect = r.draw_event_card_sidebar(
                ui.pending_event_card, ui.pending_event_is_good, mouse_pos)
