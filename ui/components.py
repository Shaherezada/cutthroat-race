import pygame
from pygame import MOUSEBUTTONUP, MOUSEMOTION


class Button:
    def __init__(self, x, y, w, h, text, color=(70, 70, 70)):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.font = pygame.font.SysFont("Arial", 20, bold=True)

    def draw(self, screen):
        # Рисуем тень и кнопку
        pygame.draw.rect(screen, (0, 0, 0), (self.rect.x + 3, self.rect.y + 3, self.rect.w, self.rect.h),
                         border_radius=5)
        pygame.draw.rect(screen, self.color, self.rect, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), self.rect, 2, border_radius=5)

        txt_surf = self.font.render(self.text, True, (255, 255, 255))
        screen.blit(txt_surf, (self.rect.centerx - txt_surf.get_width() // 2,
                               self.rect.centery - txt_surf.get_height() // 2))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class Dialog:
    """Окно выбора (например, кубика или награды в схватке)"""

    def __init__(self, title, options: list):
        self.width, self.height = 600, 400
        self.rect = pygame.Rect(1300 // 2 - 200, 1000 // 2 - 150, 400, 300)
        self.title = title
        self.buttons = []

        # Создаем кнопки по вертикали
        for i, opt in enumerate(options):
            btn = Button(self.rect.x + 50, self.rect.y + 80 + i * 70, 500, 60, opt)
            self.buttons.append(btn)

    def draw(self, screen):
        # Затемнение заднего фона
        overlay = pygame.Surface((1300, 1000), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Окно
        pygame.draw.rect(screen, (40, 40, 40), self.rect, border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), self.rect, 3, border_radius=10)

        font = pygame.font.SysFont("Arial", 24, bold=True)
        title_surf = font.render(self.title, True, (255, 255, 255))
        screen.blit(title_surf, (self.rect.centerx - title_surf.get_width() // 2, self.rect.y + 20))

        for btn in self.buttons:
            btn.draw(screen)

class SliderDialog:
    """Окно с ползунком для выбора количества монет"""

    def __init__(self, title: str, description: str, max_value: int, multiplier: int = 1):
        """
        :param title: Заголовок окна
        :param description: Описание эффекта
        :param max_value: Максимальное значение (обычно количество монет игрока)
        :param multiplier: Множитель для расчёта результата (например, 2 клетки за монетку)
        """
        self.title = title
        self.description = description
        self.max_value = max_value
        self.multiplier = multiplier
        self.current_value = 0

        # Размеры окна
        self.rect = pygame.Rect(1300 // 2 - 250, 1000 // 2 - 200, 500, 400)

        # Параметры слайдера
        self.slider_rect = pygame.Rect(self.rect.x + 50, self.rect.y + 180, 400, 20)
        self.handle_radius = 15
        self.dragging = False

        # Кнопки
        self.confirm_btn = Button(self.rect.x + 80, self.rect.y + 300, 160, 60, "Подтвердить", (50, 150, 50))
        self.cancel_btn = Button(self.rect.x + 260, self.rect.y + 300, 160, 60, "Отмена", (150, 50, 50))

        # Шрифты
        self.title_font = pygame.font.SysFont("Arial", 26, bold=True)
        self.desc_font = pygame.font.SysFont("Arial", 18)
        self.value_font = pygame.font.SysFont("Arial", 32, bold=True)
        self.result_font = pygame.font.SysFont("Arial", 20)

    def handle_event(self, event, mouse_pos):
        """
        Обрабатывает события, связанные с мышью
        :return: ('confirm', value), ('cancel', 0) или None
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Проверка кликов по кнопкам
            if self.confirm_btn.is_clicked(mouse_pos):
                return 'confirm', self.current_value
            if self.cancel_btn.is_clicked(mouse_pos):
                return 'cancel', 0

            # Проверка клика по слайдеру
            handle_x = self._get_handle_x()
            handle_pos = (handle_x, self.slider_rect.centery)
            dist = ((mouse_pos[0] - handle_pos[0]) ** 2 + (mouse_pos[1] - handle_pos[1]) ** 2) ** 0.5

            if dist <= self.handle_radius + 5:
                self.dragging = True
            # Клик по полоске слайдера
            elif self.slider_rect.collidepoint(mouse_pos):
                self._update_value_from_mouse(mouse_pos[0])

        elif event.type == MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        elif event.type == MOUSEMOTION:
            if self.dragging:
                self._update_value_from_mouse(mouse_pos[0])

        return None

    def _get_handle_x(self):
        """Вычисляет x координату ручки слайдера"""
        if self.max_value == 0:
            return self.slider_rect.x
        ratio = self.current_value / self.max_value
        return int(self.slider_rect.x + ratio * self.slider_rect.width)

    def _update_value_from_mouse(self, mouse_x):
        """Обновляет значение на основе позиции мыши"""
        clamped_x = max(self.slider_rect.x, min(mouse_x, self.slider_rect.x + self.slider_rect.width))
        ratio = (clamped_x - self.slider_rect.x) / self.slider_rect.width
        self.current_value = int(ratio * self.max_value)

    def draw(self, screen, mouse_pos):
        # Затемнение фона
        overlay = pygame.Surface((1300, 1300), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Главное окно
        pygame.draw.rect(screen, (40, 40, 45), self.rect, border_radius=12)
        pygame.draw.rect(screen, (255, 215, 0), self.rect, 4, border_radius=12)

        # Заголовок
        title_surf = self.title_font.render(self.title, True, (255, 215, 0))
        screen.blit(title_surf, (self.rect.centerx - title_surf.get_width() // 2, self.rect.y + 25))

        # Описание (многострочное)
        y_offset = self.rect.y + 70
        for line in self._wrap_text(self.description, 460):
            desc_surf = self.desc_font.render(line, True, (200, 200, 200))
            screen.blit(desc_surf, (self.rect.x + 20, y_offset))
            y_offset += 25

        # Отображение текущего значения
        value_text = f"{self.current_value} монет"
        value_surf = self.value_font.render(value_text, True, (255, 255, 255))
        screen.blit(value_surf, (self.rect.centerx - value_surf.get_width() // 2, self.rect.y + 130))

        # Результат
        result_value = self.current_value * self.multiplier
        result_text = f"→ {result_value} клеток вперёд" if self.multiplier > 0 else f"→ {abs(result_value)} клеток назад"
        result_surf = self.result_font.render(result_text, True,
                                              (100, 255, 100) if self.multiplier > 0 else (255, 100, 100))
        screen.blit(result_surf, (self.rect.centerx - result_surf.get_width() // 2, self.rect.y + 230))

        # Слайдер
        self._draw_slider(screen, mouse_pos)

        # Кнопки
        self.confirm_btn.draw(screen)
        self.cancel_btn.draw(screen)

    def _draw_slider(self, screen, mouse_pos):
        # Полоска слайдера (фон)
        pygame.draw.rect(screen, (60, 60, 70), self.slider_rect, border_radius=10)

        # Заполненная часть
        if self.current_value > 0:
            filled_width = int((self.current_value / self.max_value) * self.slider_rect.width)
            filled_rect = pygame.Rect(self.slider_rect.x, self.slider_rect.y, filled_width, self.slider_rect.height)
            pygame.draw.rect(screen, (100, 200, 100), filled_rect, border_radius=10)

        # Ручка слайдера
        handle_x = self._get_handle_x()
        handle_pos = (handle_x, self.slider_rect.centery)

        # Проверка наведения на ручку
        dist = ((mouse_pos[0] - handle_pos[0]) ** 2 + (mouse_pos[1] - handle_pos[1]) ** 2) ** 0.5
        is_hover = dist <= self.handle_radius + 5 or self.dragging

        # Тень ручки
        pygame.draw.circle(screen, (0, 0, 0), (handle_pos[0] + 2, handle_pos[1] + 2), self.handle_radius)

        # Ручка
        handle_color = (255, 255, 255) if is_hover else (200, 200, 200)
        pygame.draw.circle(screen, handle_color, handle_pos, self.handle_radius)
        pygame.draw.circle(screen, (255, 215, 0), handle_pos, self.handle_radius, 3)

        # Метки min/max
        min_label = self.desc_font.render("0", True, (150, 150, 150))
        max_label = self.desc_font.render(str(self.max_value), True, (150, 150, 150))
        screen.blit(min_label, (self.slider_rect.x - 5, self.slider_rect.bottom + 5))
        screen.blit(max_label, (self.slider_rect.right - 15, self.slider_rect.bottom + 5))

    def _wrap_text(self, text, max_width):
        """Разбивает текст на строки по ширине"""
        words = text.split(' ')
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            test_surf = self.desc_font.render(test_line, True, (255, 255, 255))
            if test_surf.get_width() <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines
