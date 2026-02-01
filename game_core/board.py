from typing import Dict, Optional
from game_core.config import CellType

class Cell:
    def __init__(self, cell_id: int, c_type: CellType, name: str = "", portal_target: Optional[int] = None):
        self.id = cell_id
        self.type = c_type
        self.name = name
        self.portal_target = portal_target

class Board:
    def __init__(self):
        self.cells: Dict[int, Cell] = {}
        self.max_cell_id = 0
        self._fill_map()

    def _fill_map(self):
        # Кинь один кубик.
        self.add_cell(0, CellType.START, "Cтарт")
        self.add_cell(1, CellType.BICYCLE, "Велосипед")
        self.add_cell(2, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(3, CellType.SHOP, "Лавка Джо")
        self.add_cell(4, CellType.TA_DAM, "Та-дам!")
        self.add_cell(5, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(6, CellType.SHOP, "Лавка Джо")
        self.add_cell(7, CellType.RED, "Красная клетка")
        self.add_cell(8, CellType.EMPTY, "Пустая клетка")
        self.add_cell(9, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(10, CellType.PORTAL, "Синий телепорт #1", 23)
        self.add_cell(11, CellType.TA_DAM, "Та-дам!")
        self.add_cell(12, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(13, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(14, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(15, CellType.GREEN, "Зелёная клетка")
        self.add_cell(16, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(17, CellType.PORTAL, "Розовый телепорт #1", 28)
        self.add_cell(18, CellType.TA_DAM, "Та-дам!")
        self.add_cell(19, CellType.SHOP, "Лавка Джо")
        self.add_cell(20, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(21, CellType.SHOP, "Лавка Джо")
        self.add_cell(22, CellType.CHEST_BAD, "Сундучок Плохо")
        self.add_cell(23, CellType.PORTAL, "Синий телепорт #2", 10)

        # Кинь два кубика, выбери нужный тебе.
        self.add_cell(24, CellType.EMPTY, "Пустая клетка")
        self.add_cell(25, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(26, CellType.GREEN, "Зелёная клетка")
        self.add_cell(27, CellType.RED, "Красная клетка")
        self.add_cell(28, CellType.PORTAL, "Розовый телепорт #2", 17)
        self.add_cell(29, CellType.RED, "Красная клетка")
        self.add_cell(30, CellType.RED, "Красная клетка")
        self.add_cell(31, CellType.CHEST_BAD, "Сундучок Плохо")
        self.add_cell(32, CellType.RED, "Красная клетка")
        self.add_cell(33, CellType.EMPTY, "Пустая клетка")
        self.add_cell(34, CellType.SHOP, "Лавка Джо")
        self.add_cell(35, CellType.EMPTY, "Пустая клетка")
        self.add_cell(36, CellType.PORTAL, "Жёлтый телепорт #1", 47)
        self.add_cell(37, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(38, CellType.GREEN, "Зелёная клетка")
        self.add_cell(39, CellType.EMPTY, "Пустая клетка")
        self.add_cell(40, CellType.FORTUNE_CUBE, "Кубик удачи")
        self.add_cell(41, CellType.GREEN, "Зелёная клетка")
        self.add_cell(42, CellType.CHEST_BAD, "Сундучок Плохо")
        self.add_cell(43, CellType.SHOP, "Лавка Джо")
        self.add_cell(44, CellType.EMPTY, "Пустая клетка")
        self.add_cell(45, CellType.TA_DAM, "Та-дам!")
        self.add_cell(46, CellType.GREEN, "Зелёная клетка")
        self.add_cell(47, CellType.PORTAL, "Жёлтый телепорт #2", 36)
        self.add_cell(48, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(49, CellType.SHOP, "Лавка Джо")
        self.add_cell(50, CellType.RED, "Красная клетка")
        self.add_cell(51, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(52, CellType.PORTAL, "Зелёный телепорт #1", 64)
        self.add_cell(53, CellType.GREEN, "Зелёная клетка")
        self.add_cell(54, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(55, CellType.RED, "Красная клетка")
        self.add_cell(56, CellType.EMPTY, "Пустая клетка")
        self.add_cell(57, CellType.FORTUNATE_SETUP, "Удачный расклад")
        self.add_cell(58, CellType.GREEN, "Зелёная клетка")
        self.add_cell(59, CellType.TA_DAM, "Та-дам!")
        self.add_cell(60, CellType.TORNADO, "Cмерч")
        self.add_cell(61, CellType.SHOP, "Лавка Джо")
        self.add_cell(62, CellType.EMPTY, "Пустая клетка")
        self.add_cell(63, CellType.GREEN, "Зелёная клетка")
        self.add_cell(64, CellType.PORTAL, "Зелёный телепорт #2", 52)
        self.add_cell(65, CellType.GREEN, "Зелёная клетка")
        self.add_cell(66, CellType.TRIBUTE, "Дань")
        self.add_cell(67, CellType.EMPTY, "Пустая клетка")

        # Кинь два кубика, передвинься на выпавшуюю сумму.
        self.add_cell(68, CellType.SHOP, "Лавка Джо")
        self.add_cell(69, CellType.EMPTY, "Пустая клетка")
        self.add_cell(70, CellType.DUEL, "Схватка")
        self.add_cell(71, CellType.EMPTY, "Пустая клетка")
        self.add_cell(72, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(73, CellType.GREEN, "Зелёная клетка")
        self.add_cell(74, CellType.RED, "Красная клетка")
        self.add_cell(75, CellType.EMPTY, "Пустая клетка")
        self.add_cell(76, CellType.SHOP, "Лавка Джо")
        self.add_cell(77, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(78, CellType.CHEST_GOOD, "Сундучок Хорошо")
        self.add_cell(79, CellType.EMPTY, "Пустая клетка")
        self.add_cell(80, CellType.EMPTY, "Пустая клетка")
        self.add_cell(81, CellType.SHOP, "Лавка Джо")
        self.add_cell(82, CellType.EMPTY, "Пустая клетка")
        self.add_cell(83, CellType.MINE, "Шахта")
        self.add_cell(84, CellType.CHEST_BAD, "Сундучок Плохо")
        self.add_cell(85, CellType.CHEST_BAD, "Сундучок Плохо")
        self.add_cell(86, CellType.CHEST_BAD, "Сундучок Плохо")
        self.add_cell(87, CellType.OH_NO, "Нееет!")
        self.add_cell(88, CellType.RED, "Красная клетка")
        self.add_cell(89, CellType.RED, "Красная клетка")
        self.add_cell(90, CellType.RED, "Красная клетка")
        self.add_cell(91, CellType.RED, "Красная клетка")
        self.add_cell(92, CellType.RED, "Красная клетка")
        self.add_cell(93, CellType.CHEST_BAD, "Сундучок Плохо")
        self.add_cell(94, CellType.CHEST_BAD, "Сундучок Плохо")
        self.add_cell(95, CellType.CHEST_BAD, "Сундучок Плохо")
        self.add_cell(96, CellType.CHEST_BAD, "Сундучок Плохо")
        self.add_cell(97, CellType.FINISH_SAFE, "Жвачка / Финиш-сейф")

    def add_cell(self, cell_id: int, c_type: CellType, name: str = "", portal_target: Optional[int] = None):
        self.cells[cell_id] = Cell(cell_id, c_type, name, portal_target)
        if cell_id > self.max_cell_id:
            self.max_cell_id = cell_id

    def resolve_move(self, start_pos: int, steps: int) -> int:
        """
        Вычисляет конечную клетку при движении.
        - steps > 0: движение вперед (к финишу)
        - steps < 0: движение назад (к старту)
        """
        target = start_pos + steps

        # Правило: Нельзя уйти дальше Старта назад
        if target < 0:
            return 0

        # Правило: Если дошли до Финиша или дальше -> останавливаемся на Финише
        if target >= self.max_cell_id:
            return self.max_cell_id

        return target

    def get_cell(self, cell_id: int) -> Cell:
        return self.cells.get(cell_id)
