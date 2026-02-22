import pygame
import sys
from game_core.engine import GameEngine, GameEvent
from ui.view_config import ViewConfig
from ui.renderer import Renderer
from game_core.logger import GameLogger
from ui.components import Dialog, SliderDialog


WINDOW_SIZE = 1000


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_SIZE + 300, WINDOW_SIZE))  # +300 для панели инфо
    pygame.display.set_caption("Cutthroat Race: Game Mode")
    clock = pygame.time.Clock()
    start_ticks = pygame.time.get_ticks()

    logger = GameLogger()
    turn_count = 1

    active_dialog = None
    active_slider = None
    pending_shop_cards = []  # Храним карты, предложенные Лавкой
    pending_event_card = None  # Храним текущую карту события
    pending_event_is_good = True  # Какую сторону показывать
    pending_tadam_rule = None
    viewing_card_sprite_id = None
    pending_tornado_target = None
    pending_move_options = []
    pending_selection_rects = []
    pending_card_use_idx = None
    pending_finish_result = None  # (roll, bonus, total, success) — результат броска на финише
    last_rolls = None
    duel_defender = None
    mine_placement_mode = False
    mine_placement_player = None

    view_cfg = ViewConfig("ui/coords.json", target_size=WINDOW_SIZE)
    raw_board = pygame.image.load("assets/field_corrected.png").convert()  # convert() ускоряет отрисовку
    board_img = pygame.transform.smoothscale(raw_board, (WINDOW_SIZE, WINDOW_SIZE))

    engine = GameEngine(logger, player_count=2) # Передаём logger
    renderer = Renderer(screen, view_cfg, board_img)

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        elapsed_seconds = (pygame.time.get_ticks() - start_ticks) // 1000
        p = engine.state.current_player

        # 1. Обработка очереди событий (делаем это только если сейчас нет активных окон)
        if engine.pending_events and not active_dialog and not active_slider and not viewing_card_sprite_id:
            game_event = engine.pending_events[0]  # Просто смотрим первое событие
            event_player = game_event.player

            if game_event.type == "SLIDER_INPUT":
                data = game_event.data
                active_slider = SliderDialog(
                    title=data["title"],
                    description=data["description"],
                    max_value=data["max_value"],
                    multiplier=data["multiplier"]
                )
            elif game_event.type == "SHOP":
                pending_shop_cards = game_event.data["cards"]
                # pending_selection_rects возвращает draw_card_selector()
            elif game_event.type == "EVENT_CARD":
                pending_event_card = game_event.data["card"]
                pending_event_is_good = game_event.data["is_good"]
                side = pending_event_card.good_side if pending_event_is_good else pending_event_card.bad_side
                title = "Карта Хорошо" if pending_event_is_good else "Карта Плохо"
                active_dialog = Dialog(
                    f"{event_player.name}: {title}: {side.name.upper()}",
                  [side.description, "ОК"]
                )
            elif game_event.type == "FINISH_ROLL":
                opts = ["Бросить (без бонуса)"]
                if event_player.coins >= 5:
                    opts.append(f"Сбросить 5 монет (+1 к броску)")
                if event_player.coins >= 10:
                    opts.append(f"Сбросить 10 монет (+2 к броску)")
                active_dialog = Dialog(f"{event_player.name}: Финиш-сейф! Нужно 6+", opts)
            elif game_event.type == "RED_CHOICE":
                active_dialog = Dialog(f"{event_player.name}: Красная западня",
                                       ["Потерять 3 монеты", "Назад на 3 клетки"])
            elif game_event.type == "TADAM_SHOW":
                pending_tadam_rule = game_event.data["rule"]
                viewing_card_sprite_id = pending_tadam_rule.sprite_id
            elif game_event.type == "DUEL_CHOOSE_OPPONENT":
                options = [f'Драться с {opp.name}' for opp in game_event.data["opponents"]]
                active_dialog = Dialog(f"{event_player.name}: Выбери противника для схватки", options)
            elif game_event.type == "DUEL_CHOOSE_REWARD":
                duel_defender = game_event.data["loser"]
                options = ["Забрать 10 монет", "Откинуть на 10 клеток"]
                if duel_defender.hand:
                    options.append("Забрать карту Лавки")
                active_dialog = Dialog(
                    f"{event_player.name}: Победа! ({game_event.data['atk_roll']} vs {game_event.data['def_roll']})",
                    options
                )
            elif game_event.type == "TORNADO_DECISION":
                pending_tornado_target = game_event.data["target_pos"]
                active_dialog = Dialog(f"Смерч: {event_player.name}", ["Откупиться (10 монет)", "Лететь к Смерчу!"])
            elif game_event.type == "CHOOSE_TARGET":
                options = [f"{opp.name}" for opp in game_event.data["opponents"]]
                active_dialog = Dialog(f"{event_player}: Выбери цель", options)
            elif game_event.type == "CHOOSE_CARD_TO_DISCARD":
                options = [f"{c.name}" for c in game_event.data["cards"]]
                active_dialog = Dialog(f"{event_player}: Сбрось карту у {game_event.data['target'].name}", options)
            elif game_event.type == "MINE_PLACEMENT":
                mine_placement_mode = True
                mine_placement_player = event_player
                engine.pending_events.pop(0)  # сразу снимаем — режим управляется флагом
            elif game_event.type == "INVENTORY_KEEP":
                pending_shop_cards = game_event.data["cards"]
            elif game_event.type == "TAX_SHOP_CARD":
                card_idx = game_event.data["card_idx"]
                cost = game_event.data["cost"]
                if card_idx >= len(event_player.hand):
                    engine.pending_events.pop(0)  # Все карты обработаны
                else:
                    card = event_player.hand[card_idx]
                    active_dialog = Dialog(
                        f"{event_player.name}: Налог — «{card.name.upper()}»",
                        [f"Заплатить {cost} монет (есть: {event_player.coins})", "Сбросить карту"]
                    )

        # Логика завершения хода
        if p.has_moved and not engine.pending_events and not active_dialog and not viewing_card_sprite_id:
            if not p.end_checks_done:
                if not engine.can_player_do_actions(p):
                    engine.end_turn_checks(p)
                    p.end_checks_done = True
                    if engine.pending_events: continue
            if p.end_checks_done and not engine.pending_events:
                if p.has_extra_turn:
                    p.has_extra_turn = False
                    p.reset_turn_flags()
                    logger.log_event(p.uid, "EXTRA_TURN_START", {"reason": "double_roll"})
                else:
                    engine.state.next_turn(logger)

        # 2. Обработка ввода
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                logger.save()
                running = False

            if active_slider:
                result = active_slider.handle_event(event, mouse_pos)
                if result:
                    action, value = result
                    current_ev = engine.pending_events[0]

                    if action == 'confirm':
                        effect_data = {
                            "effect_id": current_ev.data["effect_id"],
                            "multiplier": current_ev.data["multiplier"],
                            "target_self": current_ev.data.get("target_self", True)
                        }
                        engine.resolve_slider_input(current_ev.player, value, effect_data)
                        engine.pending_events.pop(0)
                    elif action == "cancel":
                        # Просто закрываем
                        engine.pending_events.pop(0)
                        logger.log_event(current_ev.player.uid, "SLIDER_CANCELLED", {})

                    active_slider = None
                continue

            # Просмотр карты Та-Дам
            if viewing_card_sprite_id:
                if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or \
                   (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    # Если pending_tadam_rule есть - это новое правило, нужен resolve
                    if pending_tadam_rule:
                        engine.resolve_tadam_choice(pending_tadam_rule)
                        engine.pending_events.pop(0)
                        pending_tadam_rule = None
                    # Если None - просто смотрели активное правило
                    viewing_card_sprite_id = None
                    continue

            # Выбор карт
            if engine.pending_events and not active_dialog:
                current_ev = engine.pending_events[0]
                if current_ev.type in ["SHOP", "SHOP_FREE", "CHOOSE_CARD_TO_DISCARD", "INVENTORY_KEEP"]:
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        for i, rect in enumerate(pending_selection_rects):
                            if rect.collidepoint(mouse_pos):
                                choice_idx = i if i < len(pending_selection_rects) - 1 else 2
                                if current_ev.type == "SHOP":
                                    engine.resolve_shop_choice(p, pending_shop_cards, choice_idx)
                                elif current_ev.type == "SHOP_FREE":
                                    engine.resolve_shop_free_choice(p, pending_shop_cards, choice_idx)
                                elif current_ev.type == "CHOOSE_CARD_TO_DISCARD":
                                    engine.resolve_discard_enemy_card(p, current_ev.data["target"], choice_idx)
                                elif current_ev.type == "INVENTORY_KEEP":
                                    # Если нажат «Пропустить» — оставляем первую карту
                                    actual_keep_idx = choice_idx if choice_idx < len(pending_shop_cards) else 0
                                    engine.resolve_inventory_keep(current_ev.player, actual_keep_idx)
                                    engine.pending_events.pop(0)
                                    pending_selection_rects = []
                                    break
                                engine.pending_events.pop(0)
                                pending_selection_rects = []
                                break
                        continue

            if mine_placement_mode and mine_placement_player:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    # Кнопка завершения
                    finish_btn = pygame.Rect(WINDOW_SIZE + 30, 820, 240, 55)
                    if finish_btn.collidepoint(mouse_pos):
                        mine_placement_mode = False
                        mine_placement_player = None
                        continue

                    # Клик по клетке на доске
                    if mouse_pos[0] < WINDOW_SIZE and mine_placement_player.coins > 0:
                        cell_id = view_cfg.get_cell_under_mouse(mouse_pos, radius=35)
                        if cell_id != -1 and cell_id not in engine.placed_mines:
                            mine_placement_player.pay(1)
                            engine.placed_mines[cell_id] = mine_placement_player.uid
                            logger.log_event(mine_placement_player.uid, "MINE_PLACED", {"cell": cell_id})
                continue  # не обрабатываем другие клики в этом режиме

            if active_dialog:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, btn in enumerate(active_dialog.buttons):
                        if btn.is_clicked(event.pos):
                            title = active_dialog.title
                            if "Выбери ход" in title:
                                steps = pending_move_options[i]
                                engine.move_player(p, steps)
                                logger.log_event(p.uid, "MOVE", {"steps": steps, "to": p.position})
                                active_dialog = None
                            elif pending_finish_result and btn.text == "ОК":
                                pending_finish_result = None
                                active_dialog = None
                                if engine.is_game_over:
                                    pass  # game over отрисуется ниже
                            elif "Карта" in title:  # Сундучки
                                game_event = engine.pending_events[0]
                                engine.resolve_event_card(game_event.player, pending_event_card, pending_event_is_good)
                                active_dialog = None
                                engine.pending_events.pop(0)
                            elif "противника" in title:  # Схватка
                                game_event = engine.pending_events[0]
                                engine.resolve_duel_opponent(p, game_event.data["opponents"][i])
                                active_dialog = None
                                engine.pending_events.pop(0)
                            elif "Победа!" in title:  # Награда за победу в Схватке
                                reward_types = ["money", "push"]
                                if duel_defender.hand:
                                    reward_types.append("steal_card")
                                engine.resolve_duel_reward_choice(p, duel_defender, reward_types[i])
                                active_dialog = None
                                engine.pending_events.pop(0)
                            elif "Финиш-сейф" in title:
                                bonus_map = {0: 0, 1: 5, 2: 10}
                                coin_bonus = bonus_map.get(i, 0)
                                roll, bonus, total, success = engine.attempt_finish(
                                    game_event.player, coin_bonus
                                )
                                engine.pending_events.pop(0)
                                result_text = f"Выпало {roll}" + (f"+{bonus}" if bonus else "") + f" = {total}"
                                if success:
                                    result_text += " — ПОБЕДА!"
                                else:
                                    result_text += " — Не хватило... (нужно 6+)"
                                active_dialog = Dialog(result_text, ["ОК"])
                                pending_finish_result = (roll, bonus, total, success)
                            elif "западня" in title:
                                game_event = engine.pending_events[0]
                                target_player = game_event.player
                                if i == 0:
                                    target_player.pay(3)
                                else:
                                    engine.move_player(target_player, 3, is_forward=False)
                                active_dialog = None
                                engine.pending_events.pop(0)
                            elif "Смерч" in title:
                                engine.resolve_tornado_choice(game_event.player, i, pending_tornado_target)
                                active_dialog = None
                                engine.pending_events.pop(0)
                            elif "Выбери цель" in title:
                                target_uid = game_event.data["opponents"][i].uid
                                engine.resolve_target_choice(p, target_uid, game_event.data["effect_id"],
                                                             game_event.data["value"])
                                active_dialog = None
                                engine.pending_events.pop(0)
                            elif "Сбрось карту" in title:
                                engine.resolve_discard_enemy_card(p, game_event.data["target"], i)
                                active_dialog = None
                                engine.pending_events.pop(0)
                            elif "Налог" in title:
                                game_event = engine.pending_events[0]
                                card_idx = game_event.data["card_idx"]
                                cost = game_event.data["cost"]
                                if i == 0:  # Заплатить
                                    if not game_event.player.pay(cost):
                                        # Не хватает монет — принудительный сброс
                                        removed = game_event.player.remove_card(card_idx)
                                        engine.state.deck_shop.discard(removed)
                                    else:
                                        card_idx += 1  # Карта осталась, переходим к следующей
                                else:  # Сбросить
                                    removed = game_event.player.remove_card(card_idx)
                                    engine.state.deck_shop.discard(removed)
                                    # card_idx не меняем — после remove следующая карта сдвинулась на это место
                                # Проверяем, есть ли ещё карты
                                if card_idx < len(game_event.player.hand):
                                    game_event.data["card_idx"] = card_idx  # Обновляем индекс на месте
                                else:
                                    engine.pending_events.pop(0)
                                active_dialog = None
                            elif "Выбери цель для" in title:
                                opponents = [opp for opp in engine.state.players if opp.uid != p.uid]
                                target = opponents[i]
                                if engine.use_card_from_hand(p_idx, pending_card_use_idx, target_idx=target.uid):
                                    logger.log_event(p.uid, "CARD_USE", {
                                        "card": p.hand[pending_card_use_idx].name if pending_card_use_idx < len(
                                            p.hand) else "?",
                                        "target": target.name
                                    })
                                pending_card_use_idx = None
                                active_dialog = None
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if not engine.pending_events and not p.has_moved and not p.turn_checks_done:
                    turn_skipped = engine.start_turn_checks(p)
                    if turn_skipped: continue
                    if engine.pending_events:
                        continue

                    # Игрок застрял на финише — бросает только на сейф
                    if p.is_finished:
                        engine.pending_events.append(GameEvent(
                            type="FINISH_ROLL", player=p, data={}
                        ))
                        p.has_moved = True
                    else:
                        rolls = engine.get_roll(p)
                        options = engine.get_move_options(p, rolls)
                        if len(options) > 1:
                            pending_move_options = options
                            active_dialog = Dialog("Выбери ход", [f"Идти на {o}" for o in options])
                        else:
                            steps = options[0]
                            engine.move_player(p, steps)
                            logger.log_event(p.uid, "MOVE", {"steps": steps, "to": p.position})

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Кнопка завершения хода
                if p.has_moved and not engine.pending_events:
                    btn_rect = pygame.Rect(WINDOW_SIZE + 50, 850, 200, 60)
                    if btn_rect.collidepoint(mouse_pos):
                        if not p.end_checks_done:
                            engine.end_turn_checks(p)
                            p.end_checks_done = True
                        if not engine.pending_events:
                            if p.has_extra_turn:
                                p.has_extra_turn = False
                                p.reset_turn_flags()
                            else:
                                engine.state.next_turn(logger)
                        continue

                # Проверяем клик в зоне сайдбара
                if mouse_pos[0] > WINDOW_SIZE:
                    # Считаем, на какую карту нажал текущий игрок
                    p_idx = engine.state.current_player_idx
                    p = engine.state.current_player
                    base_y = 120 + (p_idx * 220) + 80

                    for j in range(len(p.hand)):
                        card_rect = pygame.Rect(WINDOW_SIZE + 20, base_y + (j * 35), 260, 30)
                        if card_rect.collidepoint(mouse_pos):
                            card = p.hand[j]
                            # Если карта требует цель (гарпун, вуду и т.д.)
                            # Сейчас упростим: при клике открываем диалог выбора цели
                            opponents = [opp for opp in engine.state.players if opp.uid != p.uid]
                            if len(opponents) == 1:
                                # Если враг один - применяем сразу
                                if engine.use_card_from_hand(p_idx, j, target_idx=opponents[0].uid):
                                    logger.log_event(p.uid, "CARD_USE", {"card": card.name})
                            else:
                                pending_card_use_idx = j
                                options = [opp.name for opp in opponents]
                                active_dialog = Dialog(f"Выбери цель для «{card.name}»", options)

                # Клик по карте Та-Дам
                if not active_dialog and not viewing_card_sprite_id:
                    for i, rule in enumerate(engine.state.active_rules):
                        slot_key = f'slot_{i}'
                        pos = view_cfg.get_screen_coords(slot_key)
                        sprite = renderer.rule_sprites_small[rule.sprite_id]
                        rect = sprite.get_rect(center=pos)

                        if rect.collidepoint(mouse_pos):
                            viewing_card_sprite_id = rule.sprite_id
                            pending_tadam_rule = None
                            break

        # Отрисовка
        screen.fill((30, 30, 30))
        renderer.draw_board()
        renderer.draw_active_rules(engine.state.active_rules)
        renderer.draw_mines(engine.placed_mines)
        renderer.draw_players(engine.state)

        if viewing_card_sprite_id:
            renderer.draw_large_rule_card(viewing_card_sprite_id, mouse_pos)
        elif engine.pending_events and engine.pending_events[0].type in ["SHOP", "SHOP_FREE", "CHOOSE_CARD_TO_DISCARD"]:
            ev = engine.pending_events[0]
            titles = {
                "SHOP": "Лавка Джо: выбери карту (5 монет)",
                "SHOP_FREE": "Бесплатная карта Лавки Джо",
                "CHOOSE_CARD_TO_DISCARD": f"Сбрось карту у {ev.data.get('target', '')}",
                "INVENTORY_KEEP": f"Инвентаризация: {ev.player.name} — выбери карту, которую оставишь",
            }
            pending_selection_rects = renderer.draw_card_selector(
                ev.data["cards"], titles.get(ev.type, ""), mouse_pos
            )
        else:
            renderer.draw_hover(mouse_pos)
            if active_slider: active_slider.draw(screen, mouse_pos)
            elif active_dialog: active_dialog.draw(screen)

        can_act = engine.can_player_do_actions(p) if p.has_moved else False
        has_pending = bool(engine.pending_events or active_dialog or active_slider or viewing_card_sprite_id or mine_placement_mode)
        renderer.draw_sidebar(engine.state, turn_count, elapsed_seconds, can_act, has_pending)

        if mine_placement_mode and mine_placement_player:
            renderer.draw_mine_placement_button(mine_placement_player.coins, mouse_pos)

        pygame.display.flip()

        if engine.is_game_over and engine.winner:
            overlay = pygame.Surface((WINDOW_SIZE + 300, WINDOW_SIZE), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            font_big = pygame.font.SysFont("Arial", 64, bold=True)
            win_txt = font_big.render(f"{engine.winner.name} ПОБЕДИЛ!", True, (255, 215, 0))
            screen.blit(win_txt, (
                (WINDOW_SIZE + 300) // 2 - win_txt.get_width() // 2,
                WINDOW_SIZE // 2 - win_txt.get_height() // 2
            ))

        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
