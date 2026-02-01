from enum import Enum, auto

# === КОНСТАНТЫ ===
START_MONEY = 10
MAX_HAND_SIZE = 3
WINNING_ROLL = 6
TA_DAM_QUEUE_SIZE = 3

# === ТИПЫ ДАННЫХ ===

class CellType(Enum):
    EMPTY = auto()
    START = auto()

    # Цветные клетки
    RED = auto()
    GREEN = auto()

    # Активные клетки
    SHOP = auto()
    CHEST_GOOD = auto()
    CHEST_BAD = auto()
    TA_DAM = auto()

    # Специальные механики
    PORTAL = auto()
    MINE = auto()
    TORNADO = auto()
    DUEL = auto()
    BICYCLE = auto()
    FORTUNE_CUBE = auto()
    FORTUNATE_SETUP = auto()
    TRIBUTE = auto()
    OH_NO = auto()

    # Финал
    FINISH_SAFE = auto()

class CardType(Enum):
    SHOP_ITEM = auto()
    EVENT_INSTANT = auto()
    RULE_GLOBAL = auto()
