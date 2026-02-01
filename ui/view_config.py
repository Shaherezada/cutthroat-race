import json


class ViewConfig:
    def __init__(self, coords_path: str, target_size: int, original_size: int = 4800):
        with open(coords_path, 'r') as f:
            data = json.load(f)
            self.raw_coords = data

        self.scale = target_size / original_size
        self.target_size = target_size

    def get_screen_coords(self, cell_id: int) -> tuple:
        key = str(cell_id)
        if key not in self.raw_coords:return 0, 0
        x, y = self.raw_coords[key]
        return int(x * self.scale), int(y * self.scale)

    def get_cell_under_mouse(self, mouse_pos: tuple, radius: int = 40) -> int:
        """Возвращает ID клетки под мышкой для эффекта Hover"""
        mx, my = mouse_pos
        for cid, (x, y) in self.raw_coords.items():
            sx, sy = x * self.scale, y * self.scale
            if ((mx - sx) ** 2 + (my - sy) ** 2) ** 0.5 < radius:
                return cid
        return -1
