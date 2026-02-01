import pygame
import json
import os

IMAGE_PATH = "../assets/field_corrected.png"
TARGET_WIDTH = 800


def get_coords():
    pygame.init()
    if not os.path.exists(IMAGE_PATH):
        print(f"Файл {IMAGE_PATH} не найден!")
        return

    original_img = pygame.image.load(IMAGE_PATH)
    orig_w, orig_h = original_img.get_size()

    # Считаем коэффициент масштабирования
    scale = TARGET_WIDTH / orig_w
    new_size = (int(orig_w * scale), int(orig_h * scale))

    # Создаем уменьшенную копию для отрисовки
    display_img = pygame.transform.smoothscale(original_img, new_size)
    screen = pygame.display.set_mode(new_size)
    pygame.display.set_caption(f"Масштаб: {scale:.2f}. Клик - точка, ПКМ - отмена, S - сохранить")

    coords = {}
    current_id = 0
    font = pygame.font.SysFont("Arial", 18)

    running = True
    while running:
        screen.blit(display_img, (0, 0))

        # Рисуем точки на уменьшенной копии
        for cid, pos in coords.items():
            # Рисуем там, где кликнули (в экранных координатах)
            screen_pos = (int(pos[0] * scale), int(pos[1] * scale))
            pygame.draw.circle(screen, (255, 0, 0), screen_pos, 4)
            txt = font.render(str(cid), True, (255, 255, 255))
            screen.blit(txt, (screen_pos[0] + 5, screen_pos[1] - 10))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # ЛКМ
                    # Считаем реальные координаты в
                    real_x = int(event.pos[0] / scale)
                    real_y = int(event.pos[1] / scale)
                    coords[current_id] = (real_x, real_y)
                    current_id += 1
                elif event.button == 3:  # ПКМ - отмена
                    if current_id > 0:
                        current_id -= 1
                        del coords[current_id]

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    with open('coords.json', 'w') as f:
                        json.dump(coords, f)
                    print(f"Готово! Сохранено {len(coords)} точек в оригинальном разрешении.")
                    running = False

        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    get_coords()
