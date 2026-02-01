import pygame


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
