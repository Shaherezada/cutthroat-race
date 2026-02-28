import pygame
import sys
from game_core.ai import RandomAIPlayer
from game_core.logger import GameLogger
from game_core.state import Player
from ui.game_session import GameSession, WINDOW_SIZE

# ------------------------------------------------------------------
# Конфигурация игроков: "human" или "ai"
# Порядок = порядок ходов. Минимум 2 игрока.
# ------------------------------------------------------------------
PLAYER_CONFIG = [
    "ai",
    "human",
]


def create_players(config: list) -> list:
    players = []
    for i, kind in enumerate(config):
        name = f"Игрок {i + 1}"
        if kind == "ai":
            name += " (AI)"
            players.append(RandomAIPlayer(i, name))
        else:
            players.append(Player(i, name))
    return players


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_SIZE + 300, WINDOW_SIZE))
    pygame.display.set_caption("Cutthroat Race")
    clock = pygame.time.Clock()
    start_ticks = pygame.time.get_ticks()

    logger = GameLogger()
    players = create_players(PLAYER_CONFIG)
    session = GameSession(screen, logger, players=players)
    turn_count = 1
    running = True

    while running:
        mouse_pos = pygame.mouse.get_pos()
        elapsed = (pygame.time.get_ticks() - start_ticks) // 1000
        events = pygame.event.get()

        for e in events:
            if e.type == pygame.QUIT:
                logger.save()
                running = False

        session.tick(events, mouse_pos, elapsed, turn_count)

        if session.engine.is_game_over and session.engine.winner:
            _draw_winner(screen, session.engine.winner)
            pygame.time.wait(3000)
            running = False

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


def _draw_winner(screen, winner):
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))
    font = pygame.font.SysFont("Arial", 64, bold=True)
    txt = font.render(f"{winner.name} ПОБЕДИЛ!", True, (255, 215, 0))
    screen.blit(txt, (screen.get_width() // 2 - txt.get_width() // 2,
                      screen.get_height() // 2 - txt.get_height() // 2))
    pygame.display.flip()


if __name__ == "__main__":
    main()
