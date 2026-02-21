import os.path

import pygame

from game_core.cards import ShopCard
from game_core.state import GameState
from ui.view_config import ViewConfig


class Renderer:
    def __init__(self, screen: pygame.Surface, view_cfg: ViewConfig, board_img: pygame.Surface):
        self.screen = screen
        self.view_cfg = view_cfg
        self.board_img = board_img
        self.font = pygame.font.SysFont("Arial", 18, bold=True)
        self._load_sprites()

        # Цвета игроков (кружки)
        self.player_colors = [
            (255, 50, 50),  # Красный
            (50, 255, 50),  # Зеленый
            (50, 50, 255),  # Синий
            (255, 255, 50)  # Желтый
        ]

    def _load_sprites(self):
        self._load_rule_sprites()
        self._load_shop_sprites()
        self._load_coin_sprites()

    def _load_rule_sprites(self):
        self.rule_sprites_small = {}
        self.rule_sprites_large = {}

        small_size = tuple([round(dim * 0.17) for dim in (738, 1039)])
        large_size = tuple([round(dim * 0.73) for dim in (738, 1039)])

        for i in range(1, 17):
            path = f'assets/rule_cards/{i}.png'
            if os.path.exists(path):
                raw = pygame.image.load(path).convert_alpha()
                self.rule_sprites_small[i] = pygame.transform.smoothscale(raw, small_size)
                self.rule_sprites_large[i] = pygame.transform.smoothscale(raw, large_size)

    def _load_shop_sprites(self):
        self.shop_sprites = {}
        size = tuple([round(dim * 0.41) for dim in (738, 1039)])
        for i in range(1, 11):
            path = f'assets/shop_cards/{i}.png'
            if os.path.exists(path):
                raw = pygame.image.load(path).convert_alpha()
                self.shop_sprites[i] = pygame.transform.smoothscale(raw, size)

    def _load_coin_sprites(self):
        self.coin_sprites = {}
        self.coin_sprites_small = {}
        self.coin_sprites_board = {}
        for denom in [1, 5]:
            path = f'assets/coins/{denom}.png'
            if os.path.exists(path):
                raw = pygame.image.load(path).convert_alpha()
                self.coin_sprites[denom] = pygame.transform.smoothscale(raw, (26, 26))
                self.coin_sprites_small[denom] = pygame.transform.smoothscale(raw, (18, 18))
                self.coin_sprites_board[denom] = pygame.transform.smoothscale(raw, (52, 52))

    def draw_board(self):
        self.screen.blit(self.board_img, (0, 0))

    def draw_hover(self, mouse_pos: tuple):
        """Рисует мягкую подсветку клетки"""
        cid = self.view_cfg.get_cell_under_mouse(mouse_pos)
        if cid != -1:
            pos = self.view_cfg.get_screen_coords(cid)
            # Рисуем полупрозрачный круг
            overlay = pygame.Surface((100, 100), pygame.SRCALPHA)
            pygame.draw.circle(overlay, (255, 255, 255, 80), (50, 50), 40)
            self.screen.blit(overlay, (pos[0] - 50, pos[1] - 50))

    def draw_players(self, state: GameState):
        # Группируем игроков по позициям
        pos_groups = {}
        for p in state.players:
            pos_groups.setdefault(p.position, []).append(p)

        for position, players in pos_groups.items():
            base_pos = self.view_cfg.get_screen_coords(position)
            count = len(players)

            for i, player in enumerate(players):
                # Если игрок один - смещение 0. Если много - считаем смещение
                if count > 1:
                    offset_x = (i - (count - 1) / 2) * 25
                    offset_y = (i % 2) * 10
                else:
                    offset_x, offset_y = 0, 0

                final_pos = (base_pos[0] + offset_x, base_pos[1] + offset_y)
                color = self.player_colors[player.uid % len(self.player_colors)]

                pygame.draw.circle(self.screen, (0, 0, 0), final_pos, 18) # Обводка
                pygame.draw.circle(self.screen, color, final_pos, 15)
                txt = self.font.render(str(player.uid + 1), True, (255, 255, 255))
                self.screen.blit(txt, (final_pos[0] - 5, final_pos[1] - 10))

    def draw_sidebar(self, state: GameState, turn_count: int, elapsed_seconds: int,
                     can_do_actions: bool = False, has_pending: bool = False):
        """Отрисовка правой информационной интерактивной панели"""
        sidebar_rect = pygame.Rect(self.view_cfg.target_size, 0, 300, self.view_cfg.target_size)
        pygame.draw.rect(self.screen, (40, 40, 45), sidebar_rect)
        pygame.draw.line(self.screen, (100, 100, 100), (sidebar_rect.x, 0),
                         (sidebar_rect.x, sidebar_rect.h), 2)

        # 1. Общая информация: ход и время
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        time_str = f"Время: {minutes:02d}:{seconds:02d}"

        info_txt = self.font.render(f"Ход: {turn_count}", True, (255, 215, 0))
        time_txt = self.font.render(time_str, True, (200, 200, 200))
        self.screen.blit(info_txt, (sidebar_rect.x + 20, 20))
        self.screen.blit(time_txt, (sidebar_rect.x + 20, 50))

        # 2. Игроки
        for i, player in enumerate(state.players):
            y_offset = 120 + (i * 260)
            is_active = (state.current_player_idx == i)

            color = self.player_colors[i % len(self.player_colors)]
            bg_color = (60, 60, 70) if is_active else (45, 45, 50)
            player_rect = pygame.Rect(sidebar_rect.x + 10, y_offset, 280, 240)
            pygame.draw.rect(self.screen, bg_color, player_rect, border_radius=10)
            if is_active:
                pygame.draw.rect(self.screen, color, player_rect, 2, border_radius=10)

            name_txt = self.font.render(f"{player.name}", True, color)
            self.screen.blit(name_txt, (player_rect.x + 15, player_rect.y + 12))

            # Монеты — спрайтами
            coin_label = pygame.font.SysFont("Arial", 14).render("Монеты:", True, (180, 180, 180))
            self.screen.blit(coin_label, (player_rect.x + 15, player_rect.y + 42))
            coins_h = self.draw_coins_bar(player_rect.x + 15, player_rect.y + 58, player.coins, max_width=255)

            cards_y = player_rect.y + 60 + coins_h + 4

            if not player.hand:
                empty_txt = pygame.font.SysFont("Arial", 15).render("Нет карт Лавки", True, (120, 120, 120))
                self.screen.blit(empty_txt, (player_rect.x + 15, cards_y))
            else:
                for j, card in enumerate(player.hand):
                    card_btn_rect = pygame.Rect(player_rect.x + 10, cards_y + (j * 34), 260, 28)
                    pygame.draw.rect(self.screen, (30, 30, 35), card_btn_rect, border_radius=5)
                    txt_color = (255, 255, 255) if j not in player.used_cards_indices else (100, 100, 100)
                    card_txt = pygame.font.SysFont("Arial", 15, bold=True).render(card.name.upper(), True, txt_color)
                    self.screen.blit(card_txt, (card_btn_rect.x + 8, card_btn_rect.y + 5))

        # 3. Кнопка завершения хода
        p = state.current_player
        show_button = p.has_moved and not has_pending and can_do_actions
        if show_button:
            btn_rect = pygame.Rect(self.view_cfg.target_size + 50, 850, 200, 60)
            pygame.draw.rect(self.screen, (200, 50, 50), btn_rect, border_radius=10)
            pygame.draw.rect(self.screen, (255, 255, 255), btn_rect, 2, border_radius=10)
            txt = self.font.render("Завершить ход", True, (255, 255, 255))
            self.screen.blit(txt,
                             (btn_rect.centerx - txt.get_width() // 2, btn_rect.centery - txt.get_height() // 2))
            return btn_rect
        return None

    def draw_coins_bar(self, x: int, y: int, coins: int, max_width: int = 255) -> int:
        """Рисует монеты спрайтами. Возвращает высоту занятой области в пикселях."""
        if not self.coin_sprites or coins <= 0:
            txt = pygame.font.SysFont("Arial", 15).render("0", True, (150, 150, 150))
            self.screen.blit(txt, (x, y + 5))
            return 30

        coin_list = []
        remaining = coins
        # Если делится на 5 — последнюю пятёрку заменяем на пять единиц
        if remaining > 0 and remaining % 5 == 0:
            remaining -= 5
            fives = remaining // 5
            coin_list.extend([5] * fives)
            coin_list.extend([1] * 5)
        else:
            fives = remaining // 5
            coin_list.extend([5] * fives)
            remaining -= fives * 5
            coin_list.extend([1] * remaining)

        size, gap = 26, 3
        per_row = max(1, max_width // (size + gap))
        rows = (len(coin_list) + per_row - 1) // per_row

        for i, d in enumerate(coin_list):
            col, row = i % per_row, i // per_row
            sprite = self.coin_sprites.get(d)
            if sprite:
                self.screen.blit(sprite, (x + col * (size + gap), y + row * (size + gap)))

        return rows * (size + gap) + 2

    def draw_large_rule_card(self, sprite_id: int, mouse_pos: tuple):
        """Рисует крупную карту в центре экрана с затемнением фона"""
        # Затемнение
        overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        # Карта
        sprite = self.rule_sprites_large[sprite_id]
        card_rect = sprite.get_rect(center=(self.view_cfg.target_size // 2, self.view_cfg.target_size // 2))
        self.screen.blit(sprite, card_rect)

        # Кнопка "Закрыть" под картой
        btn_rect = pygame.Rect(0, 0, 200, 50)
        btn_rect.center = (card_rect.centerx, card_rect.bottom + 60)
        # Эффект наведения на кнопку
        is_hover = btn_rect.collidepoint(mouse_pos)
        btn_color = (100, 100, 110) if is_hover else (60, 60, 70)
        pygame.draw.rect(self.screen, btn_color, btn_rect, border_radius=10)
        pygame.draw.rect(self.screen, (200, 200, 200), btn_rect, 2, border_radius=10)
        txt = self.font.render("Закрыть", True, (255, 255, 255))
        self.screen.blit(txt, (btn_rect.centerx - txt.get_width() // 2, btn_rect.centery - txt.get_height() // 2))

        return btn_rect

    def draw_active_rules(self, active_rules: list):
        """Рисует правила Та-дам в слотах на доске"""
        for i, rule in enumerate(active_rules):
            slot_key = f'slot_{i}' # Используем ключи из coords.json
            pos = self.view_cfg.get_screen_coords(slot_key)

            sprite = self.rule_sprites_small[rule.sprite_id]
            rect = sprite.get_rect(center=pos)
            self.screen.blit(sprite, rect)

    def draw_card_selector(self, cards: list, title: str, mouse_pos: tuple):
        """
        Универсальный метод отрисовки выбора из нескольких карт.
        Возвращает индекс выбранной карты или -1.
        """
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        title_surf = self.font.render(title, True, (255, 215, 0))
        self.screen.blit(title_surf, (self.view_cfg.target_size // 2 - title_surf.get_width() // 2, 100))

        card_rects = []
        n = len(cards)
        total_w = n * 320
        start_x = (self.view_cfg.target_size - total_w) // 2

        for i, card in enumerate(cards):
            if isinstance(card, ShopCard):
                sprite = self.shop_sprites.get(card.sprite_id)
            else:
                raise Exception("Выбор не из карт Лавка Джо")

            if not sprite: continue

            x = start_x + (i * 320)
            y = 250
            rect = sprite.get_rect(topleft=(x, y))
            card_rects.append(rect)

            # Эффект наведения
            if rect.collidepoint(mouse_pos):
                pygame.draw.rect(self.screen, (255, 255, 255), rect.inflate(15, 15), 5, border_radius=10)

            self.screen.blit(sprite, rect)

        # Кнопка "Пропустить"
        skip_btn = pygame.Rect(self.view_cfg.target_size // 2 - 100, 700, 200, 50)
        is_skip_hover = skip_btn.collidepoint(mouse_pos)
        pygame.draw.rect(self.screen, (150, 50, 50) if is_skip_hover else (100, 30, 30), skip_btn, border_radius=10)
        txt = self.font.render("Пропустить", True, (255, 255, 255))
        self.screen.blit(txt, (skip_btn.centerx - txt.get_width() // 2,
                                    skip_btn.centery - txt.get_height() // 2 - 1))

        card_rects.append(skip_btn)
        return card_rects

    def draw_mines(self, placed_mines: dict):
        """Рисует мины на доске."""
        for cell_id in placed_mines:
            pos = self.view_cfg.get_screen_coords(int(cell_id))
            sprite = self.coin_sprites_board.get(1)
            if sprite:
                self.screen.blit(sprite, (pos[0] - 26, pos[1] - 26))

    def draw_mine_placement_button(self, player_coins: int, mouse_pos: tuple) -> pygame.Rect:
        btn_rect = pygame.Rect(self.view_cfg.target_size + 15, 815, 270, 85)
        is_hover = btn_rect.collidepoint(mouse_pos)
        pygame.draw.rect(self.screen, (140, 90, 0) if is_hover else (100, 65, 0), btn_rect, border_radius=10)
        pygame.draw.rect(self.screen, (255, 215, 0), btn_rect, 2, border_radius=10)

        label = self.font.render("Завершить расстановку", True, (255, 255, 255))
        sub_font = pygame.font.SysFont("Arial", 14)
        sub1 = sub_font.render(f"Монет осталось: {player_coins}", True, (220, 200, 120))
        sub2 = sub_font.render("(клик на клетку = -1 монета)", True, (220, 200, 120))

        self.screen.blit(label, (btn_rect.centerx - label.get_width() // 2, btn_rect.y + 10))
        self.screen.blit(sub1, (btn_rect.centerx - sub1.get_width() // 2, btn_rect.y + 40))
        self.screen.blit(sub2, (btn_rect.centerx - sub2.get_width() // 2, btn_rect.y + 58))
        return btn_rect
