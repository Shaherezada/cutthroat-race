from typing import Optional, Tuple, Dict

# ──────────────────────────────────────────
# Флаг включения анимации.
# Менять здесь или из main.py до старта сессии.
ANIMATION_ENABLED: bool = True

MS_PER_STEP: float = 110   # мс на одну клетку (базовое)
MIN_TOTAL_MS: float = 280  # минимальная длительность всей анимации
MAX_TOTAL_MS: float = 950  # максимальная длительность всей анимации
LAND_PAUSE_RATIO: float = 0.28  # доля шага = «пауза на клетке» (тык)
# ──────────────────────────────────────────


def _ease_out(t: float) -> float:
    return 1.0 - (1.0 - t) ** 2


class _MoveAnim:
    def __init__(self, uid: int, path: list, view_cfg):
        self.uid = uid
        self.path = path          # [cell_id, cell_id, ...]  len >= 2
        self.view_cfg = view_cfg

        n = len(path) - 1
        total = max(MIN_TOTAL_MS, min(MAX_TOTAL_MS, n * MS_PER_STEP))
        self.ms_per_step = total / n
        self.elapsed = 0.0
        self.done = False

    @property
    def total_ms(self) -> float:
        return (len(self.path) - 1) * self.ms_per_step

    def tick(self, dt: float) -> bool:
        """Обновляет таймер. Возвращает True пока анимация активна."""
        if self.done:
            return False
        self.elapsed += dt
        if self.elapsed >= self.total_ms:
            self.done = True
            return False
        return True

    def get_screen_pos(self) -> Tuple[int, int]:
        if self.done:
            return self.view_cfg.get_screen_coords(self.path[-1])

        n_steps = len(self.path) - 1
        step = min(int(self.elapsed // self.ms_per_step), n_steps - 1)
        local = (self.elapsed - step * self.ms_per_step) / self.ms_per_step  # 0..1

        move_phase = 1.0 - LAND_PAUSE_RATIO
        if local < move_phase:
            t = _ease_out(local / move_phase)
        else:
            t = 1.0  # фишка «стоит» на клетке — пауза

        a = self.view_cfg.get_screen_coords(self.path[step])
        b = self.view_cfg.get_screen_coords(self.path[step + 1])
        return (int(a[0] + (b[0] - a[0]) * t),
                int(a[1] + (b[1] - a[1]) * t))


class Animator:
    """Менеджер визуальных анимаций фишек."""

    def __init__(self, view_cfg):
        self._view_cfg = view_cfg
        self._active: Dict[int, _MoveAnim] = {}  # uid -> анимация

    def start_move(self, uid: int, from_pos: int, to_pos: int):
        if not ANIMATION_ENABLED or from_pos == to_pos:
            return
        if to_pos > from_pos:
            path = list(range(from_pos, to_pos + 1))
        else:
            path = list(range(from_pos, to_pos - 1, -1))
        self._active[uid] = _MoveAnim(uid, path, self._view_cfg)

    def tick(self, dt_ms: float):
        finished = [uid for uid, a in self._active.items() if not a.tick(dt_ms)]
        for uid in finished:
            del self._active[uid]

    def get_visual_pos(self, uid: int) -> Optional[Tuple[int, int]]:
        """None — анимации нет, рисовать по обычным координатам."""
        a = self._active.get(uid)
        return a.get_screen_pos() if a else None

    @property
    def is_animating(self) -> bool:
        return bool(self._active)