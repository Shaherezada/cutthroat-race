import pygame
import sys
from game_core.engine import GameEngine
from ui.view_config import ViewConfig
from ui.renderer import Renderer
from game_core.logger import GameLogger
from ui.components import Dialog


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
    pending_shop_cards = []  # Храним карты, предложенные Лавкой
    pending_event_card = None  # Храним текущую карту события
    pending_event_is_good = True  # Какую сторону показывать
    pending_tadam_rule = None
    viewing_card_sprite_id = None
    pending_tornado_target = None
    pending_move_options = []
    pending_selection_rects = []
    last_rolls = None
    duel_defender = None

    view_cfg = ViewConfig("ui/coords.json", target_size=WINDOW_SIZE)
    raw_board = pygame.image.load("assets/field_corrected.png").convert()  # convert() ускоряет отрисовку
    board_img = pygame.transform.smoothscale(raw_board, (WINDOW_SIZE, WINDOW_SIZE))

    engine = GameEngine(logger, player_count=2) # Передаём logger
    renderer = Renderer(screen, view_cfg, board_img)

    running = True
    while running:
        logger.set_turn(turn_count)
        mouse_pos = pygame.mouse.get_pos()
        elapsed_seconds = (pygame.time.get_ticks() - start_ticks) // 1000
        p = engine.state.current_player

        # 1. Обработка очереди событий (делаем это только если сейчас нет активных окон)
        if engine.pending_events and not active_dialog and not viewing_card_sprite_id:
            game_event = engine.pending_events[0]  # Просто смотрим первое событие
            event_player = game_event.player
            if game_event.type == "SHOP":
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
            elif game_event.type == "TADAM_SHOW":
                pending_tadam_rule = game_event.data["rule"]
                viewing_card_sprite_id = pending_tadam_rule.sprite_id
            elif game_event.type == "DUEL_CHOOSE_OPPONENT":
                options = [f'Драться с {opp.name}' for opp in game_event.data["opponents"]]
                active_dialog = Dialog(f"{event_player.name}: Выбери противника для схватки", options)
            elif game_event.type == "DUEL_CHOOSE_REWARD":
                duel_defender = game_event.data["loser"]
                active_dialog = Dialog(
                    f"{event_player.name}: Победа! ({game_event.data['atk_roll']} vs {game_event.data['def_roll']})",
                 ["Забрать 10 монет", "Откинуть на 10 клеток", "Забрать карту Лавки"]
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

        if p.has_moved and not engine.pending_events and not active_dialog and not viewing_card_sprite_id:
            if not engine.can_player_do_actions(p):
                engine.end_turn_checks(p)
                engine.state.next_turn()
                turn_count += 1

        # 2. Обработка ввода
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                logger.save()
                running = False

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
                if current_ev.type in ["SHOP", "CHOOSE_CARD_TO_DISCARD"]:
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        for i, rect in enumerate(pending_selection_rects):
                            if rect.collidepoint(mouse_pos):
                                choice_idx = i if i < len(pending_selection_rects) - 1 else 2
                                if current_ev.type == "SHOP":
                                    engine.resolve_shop_choice(p, pending_shop_cards, choice_idx)
                                elif current_ev.type == "CHOOSE_CARD_TO_DISCARD":
                                    engine.resolve_discard_enemy_card(p, current_ev.data["target"], choice_idx)
                                engine.pending_events.pop(0)
                                pending_selection_rects = []
                                break
                    continue

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
                            elif "Карта" in title:  # Сундучки
                                game_event = engine.pending_events[0]
                                engine.resolve_event_card(game_event.player, pending_event_card, pending_event_is_good)
                                active_dialog = None
                                engine.pending_events.pop(0)
                            elif "противника" in title:  # Схватка
                                engine.resolve_duel_opponent(p, game_event.data["opponents"][i])
                                active_dialog = None
                                engine.pending_events.pop(0)
                            elif "Победа!" in title:  # Награда за победу в Схватке
                                reward_types = ["money", "push", "steal_card"]
                                engine.resolve_duel_reward_choice(p, duel_defender, reward_types[i])
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
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if not engine.pending_events and not p.has_moved:
                    engine.start_turn_checks(p)
                    if engine.pending_events: continue
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
                        engine.end_turn_checks(p)
                        engine.state.next_turn()
                        turn_count += 1
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
                                raise NotImplementedError("Если врагов много - нужен диалог")

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

        if viewing_card_sprite_id:
            renderer.draw_large_rule_card(viewing_card_sprite_id, mouse_pos)
        elif engine.pending_events and engine.pending_events[0].type in ["SHOP", "CHOOSE_CARD_TO_DISCARD"]:
            ev = engine.pending_events[0]
            pending_selection_rects = renderer.draw_card_selector(ev.data["cards"], "", mouse_pos)
        else:
            renderer.draw_players(engine.state)
            renderer.draw_hover(mouse_pos)
            if active_dialog: active_dialog.draw(screen)

        can_act = engine.can_player_do_actions(p) if p.has_moved else False
        has_pending = bool(engine.pending_events or active_dialog or viewing_card_sprite_id)
        renderer.draw_sidebar(engine.state, turn_count, elapsed_seconds, can_act, has_pending)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
