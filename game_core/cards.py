import random
from typing import List, Union
from dataclasses import dataclass
from game_core.config import CardType

class Card:
    """Базовый класс для любой карты"""
    def __init__(self, uid: str, name: str, c_type: CardType):
        self.uid = uid
        self.name = name
        self.type = c_type

    def __repr__(self):
        return f"[{self.type.name}] {self.name}"

class ShopCard(Card):
    """Карта из Лавки Джо"""
    def __init__(self, uid: str, name: str, use_cost: int = 0, description: str = '', effect_id: str = None,
             is_passive: bool = False, value: int = 0, sprite_id: int = 0):
        super().__init__(uid, name, CardType.SHOP_ITEM)
        self.use_cost = use_cost
        self.description = description
        self.effect_id = effect_id
        self.is_passive = is_passive
        self.value = value
        self.sprite_id = sprite_id

class RuleCard(Card):
    """Карта Та-Дам"""
    def __init__(self, uid: str, name: str, description: str, effect_id: str, sprite_id: int, value: int = 0):
        super().__init__(uid, name, CardType.RULE_GLOBAL)
        self.description = description
        self.sprite_id = sprite_id # от 1 до 16
        self.effect_id = effect_id
        self.value = value

@dataclass
class EventSide:
    """Описание одной стороны карты сундучка"""
    name: str
    description: str
    effect_id: str
    value: int = 0

class EventCard(Card):
    """Двусторонняя карта (Хорошо/Плохо)"""
    def __init__(self, uid: str, good: EventSide, bad: EventSide):
        # Имя карты — комбинация сторон
        super().__init__(uid, f"{good.name} / {bad.name}", CardType.EVENT_INSTANT)
        self.good_side = good
        self.bad_side = bad

class Deck:
    def __init__(self, cards: List[Card], name: str = "Deck"):
        self.name = name
        self.draw_pile: List[Card] = cards[:]
        self.discard_pile: List[Card] = []
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.draw_pile)

    def draw(self, count: int = 1) -> List[Card]:
        drawn = []
        for _ in range(count):
            if not self.draw_pile:
                self._reshuffle()
            drawn.append(self.draw_pile.pop())
        return drawn

    def discard(self, card: Card):
        self.discard_pile.append(card)

    def _reshuffle(self):
        if not self.discard_pile:
            return
        self.draw_pile.extend(self.discard_pile)
        self.discard_pile = []
        self.shuffle()

class CardLibrary:
    @staticmethod
    def create_shop_deck() -> Deck:
        """Колода Лавки Джо"""
        cards = [
            # Активные
            ShopCard("shop_voodoo", "вуду", use_cost=3,
                 description="Можешь сбросить 3 монеты, чтобы игрок перед тобой взял карту Плохо.",
                 effect_id="attack_voodoo", sprite_id=9),

            ShopCard("shop_grenade", "граната", use_cost=3, value=6,
                 description="Можешь сбросить 3 монеты, чтобы игрок перед тобой передвинулся на 6 клеток назад.",
                 effect_id="attack_grenade", sprite_id=5),

            ShopCard("shop_hook", "крюк", use_cost=3, value=10,
                 description="Можешь сбросить 3 монеты, чтобы передвинуться на клетку "
                                "с другим игроком, если он в пределах 10 клеток перед тобой.",
                 effect_id="attack_hook", sprite_id=10),

            ShopCard("shop_harpoon", "гарпун", use_cost=3, value=10,
                 description="Можешь сбросить 3 монеты, чтобы передвинуть на свою клетку "
                                "другого игрока, если он в пределах 10 клеток перед тобой",
                 effect_id="move_harpoon", sprite_id=8),

            ShopCard("shop_rocket", "ракета", use_cost=3, value=5,
                 description="Можешь сбросить 3 монеты, чтобы передвинуться на 5 клеток вперёд.",
                 effect_id="move_rocket", sprite_id=2),

            ShopCard("shop_hand_fate", "рука судьбы", use_cost=0, value=2,
                 description="Можешь выбрать другого игрока. Он передвигается на 2 клетки назад "
                                "(при игре вдвоём или втроём на 1 клетку назад).",
                 effect_id="attack_hand_fate", sprite_id=3),

            # Пассивные
            ShopCard("shop_magic_cube", "волшебный куб", is_passive=True, value=1,
                 description="Прибавляй 1 к результату своего броска кубиков.",
                 effect_id="passive_roll_plus_1", sprite_id=4),

            ShopCard("shop_magnet", "денежный магнит", is_passive=True, value=5,
                 description="Если остановился на красной клетке, получи 5 монет.",
                 effect_id="passive_red_income", sprite_id=7),

            ShopCard("shop_travelator", "траволатор", is_passive=True, value=4,
                 description="Если остановился на пустой клетке передвинься на 4 клетки вперёд.",
                 effect_id="passive_empty_move", sprite_id=1),

            ShopCard("shop_clover", "четырёхлистный клевер", is_passive=True, value=4,
                 description="Если остановился на пустой клетке, получи 4 монеты.",
                 effect_id="passive_empty_income", sprite_id=6),
        ]
        # Для баланса множим карты (в реальной колоде их по несколько штук)
        full_deck = []
        for c in cards:
            full_deck.extend([c] * 2)
        return Deck(full_deck, name="Лавка Джо")

    @staticmethod
    def create_tadam_deck() -> Deck:
        """Колода Та-Дам (Глобальные правила)"""
        cards = [
            RuleCard("rule_red_penalty", "красная западня",
                 description="Если остановился на красной клетке, выбери одно: потеряй 3 монеты или "
                                "передвинься на 3 клетки назад.",
                 effect_id="rule_red_choice", sprite_id=5),

            RuleCard("rule_green_bonus", "зелёный бонус", value=5,
                 description="Если остановился на зелёной клетке, получи 5 монет.",
                 effect_id="rule_green_income", sprite_id=6),

            RuleCard("rule_green_reroll", "зелёный разгон",
                 description="Если остановился на зелёной клетке, походи еще раз.",
                 effect_id="rule_green_extra_turn", sprite_id=4),

            RuleCard("rule_green_turbo", "зелёный турбо", value=7,
                 description="Если остановился на зелёной клетке, передвинься на 7 вперёд.",
                 effect_id="rule_green_move", sprite_id=3),

            RuleCard("rule_last_aid", "помощь отстающим",
                 description="Последний игрок в начале хода тащит бесплатную "
                                "карту Лавка Джо, если у него их меньше трёх.",
                 effect_id="rule_last_aid", sprite_id=7),

            RuleCard("rule_double_move", "дубль-ход",
                 description="Если выпал дубль, походи еще раз.",
                 effect_id="rule_double_reroll", sprite_id=8),

            RuleCard("rule_aggro", "агрессия",
                 description="Если закончил ход на клетке с игроком, начни с ним схватку!",
                 effect_id="rule_collision_duel", sprite_id=1),

            RuleCard("rule_last_pity", "утешение", value=3,
                 description="Последний игрок в начале хода получает 3 монеты",
                 effect_id="rule_last_player_income", sprite_id=2),

            RuleCard("rule_last_dice_coins", "зарплата отстающего",
                 description="Последний игрок в конце своего хода бросает 1 кубик и получает "
                                "столько монет, сколько на нём выпало.",
                 effect_id="rule_last_dice_coins", sprite_id=13),

            RuleCard("rule_six_skip", "проклятие шестерки",
                 description="Если хотя бы на одном кубике выпала шестёрка, пропусти ход. "
                                "Если ты на клетке «Жвачка», то игнорируй эту карту.)",
                 effect_id="rule_six_skip", sprite_id=14),

            RuleCard("rule_red_bad", "красная неудача",
                 description="Если остановился на красной клетке, тащи карту Плохо.",
                 effect_id="rule_red_bad", sprite_id=15),

            RuleCard("rule_last_draw_good", "удача отстающего",
                 description="Последний игрок в начале своего хода тащит карту Хорошо.",
                 effect_id="rule_last_draw_good", sprite_id=16),

            RuleCard("rule_green_good", "зелёный подарок",
                 description="Если остановился на зелёной клетке, тащи карту Хорошо.",
                 effect_id="rule_green_good", sprite_id=12),

            RuleCard("rule_red_tax_all", "красный налог", value=2,
                 description="Если остановился на красной клетке, отдай всем по 2 монеты "
                                "(4 монеты при игре вдвоём).",
                 effect_id="rule_red_tax_all", sprite_id=11),

            RuleCard("rule_overtake_steal", "карманник", value=3,
                 description="Если обгоняешь кого-то, забираешь у него 3 монеты.",
                 effect_id="rule_overtake_steal", sprite_id=9),

            RuleCard("rule_last_move_5", "прыжок отстающего", value=5,
                 description="Последний игрок передвигается "
                                "на 5 дополнительных клеток вперёд "
                                    "в конце своего хода. "
                                        "Если он остановился на клетке "
                                            "с эффектом, то она будет действовать на него по обычным правилам.",
                 effect_id="rule_last_move_5", sprite_id=10),
        ]
        return Deck(cards, name="Та-Дам")

    @staticmethod
    def create_event_deck() -> Deck:
        """Создает колоду двусторонних карт событий"""

        # Данные пар (Good Side / Bad Side)
        pairs_data = [
            (
                EventSide("зелёный свет", "Передвинься вперёд до ближайшей зелёной клетки. Если перед тобой нет зелёной "
                            "клетки, то передвинься на 3 клетки вперёд.", "move_nearest_green"),
                EventSide("угощение", "Все игроки, кроме тебя, получают по 3 монеты.", "pay_all_others_bank", 3)
            ),
            (
                EventSide("дополнительный ход", "Сбрось 2 монеты, чтобы сделать ещё один ход. "
                            "Если у тебя меньше 2 монет, то ничего не происходит.", "extra_turn_pay_coins", 2),
                EventSide("счастливчик", "Ты счастливчик! Ничего не происходит.", "no_effect")
            ),
            (
                EventSide("мародёрство", "Забери любую карту Лавка Джо у игрока, который тебя опережает.",
                            "steal_shop_card_leader"),
                EventSide("общий грабёж", "Все игроки теряют по 5 монет.", "all_lose_coins_global", 5)
            ),
            (
                EventSide("ускорение за монеты", "Можешь сбросить до 5 монет. "
                            "За каждую сброшенную монету передвинься на 2 клетки вперёд.",
                                "pay_coins_move_flexible", 2),
                EventSide("невезение", "Кинь кубик: "
                                       "1, 2, 3 — потеряй 5 монет; "
                                       "4, 5, 6 — передвинься на 10 клеток назад.", "roll_lose_coins_or_move_back")
            ),
            (
                EventSide("вымогательство", "Выбери другого игрока, возьми у него 3 монеты.", "steal_coins_target", 3),
                EventSide("налог на имущество", "Заплати за каждую свою карту Лавка Джо по 3 монеты. "
                            "Сбрось все карты, за которые не смог или не захотел платить.", "tax_shop_cards", 3)
            ),
            (
                EventSide("утилизация", "Сбрось любую карту Лавка Джо другого игрока.", "discard_enemy_shop_card"),
                EventSide("благородство", "Выбери другого игрока. В свою очередь он делает два хода подряд.",
                            "give_double_turn_enemy")
            ),
            (
                EventSide("подстава", "Выбери другого игрока, он тащит карту Плохо.", "force_enemy_draw_bad"),
                EventSide("потеря", "Потеряй 5 монет.", "lose_coins", 5)
            ),
            (
                EventSide("штраф сопернику", "Выбери другого игрока, он теряет 5 монет.", "force_enemy_lose_coins", 5),
                EventSide("преимущество врагов", "Все остальные игроки передвигаются на 5 клеток вперёд.",
                            "others_move_forward", 5)
            ),
            (
                EventSide("азартная игра", "Кинь кубик: 1, 2, 3 — получи 10 монет; "
                                           "4, 5, 6 — передвинься на 5 клеток вперед.", "roll_gamble_money_move"),
                EventSide("провал", "Передвинься на 5 клеток назад.", "move_self_back", 5)
            ),
            (
                EventSide("находка", "Получи 5 монет.", "gain_coins", 5),
                EventSide("фора остальным", "Все игроки, кроме тебя, получают по 3 монеты "
                                            "и передвигаются на 3 клетки вперёд.", "others_gain_coins_move", 3)
            ),
            (
                EventSide("ловушка", "Можешь положить по 1 своей монете на любые клетки. "
                                        "Когда любой игрок останавливается на клетке с монетой, "
                                        "он пропускает следующий ход, а эта монета сбрасывается. "
                                     "Эффект клетки, где лежит монета, не действует", "place_mines", 1),
                EventSide("инвентаризация", "Все игроки сбрасывают все свои карты Лавка Джо, кроме одной.",
                            "all_discard_to_one_shop_card")
            ),
            (
                EventSide("лёгкий путь", "Передвинься на 3 клетки вперёд, получи 3 монеты.", "move_forward_gain_coins", 3),
                EventSide("общая задержка", "Выбери другого игрока. Вы оба пропускаете следующий ход "
                                                "(при игре вдвоём ход пропускаешь только ты).", "skip_turn_mutual")
            ),
            (
                EventSide("поборы", "Забери у каждого игрока по 2 монеты.", "steal_2_from_all", 2),
                EventSide("толчок вперёд", "Выбери другого игрока, брось 1 кубик "
                            "и передвинь его вперед на выпавшее значение.", "roll_push_enemy")
            ),
            (
                EventSide("награда", "Получи 10 монет.", "gain_coins", 10),
                EventSide("милостыня", "Выбери другого игрока, отдай ему 5 монет.", "give_5_to_target", 5)
            ),
            (
                EventSide("марш-бросок", "Передвинься на 5 клеток вперёд.", "move_self_forward", 5),
                EventSide("потеря снаряжения", "Сбрось карту Лавка Джо. Если у тебя её нет, "
                            "то передвинься назад до ближайшей красной клетки.", "discard_shop_or_red")
            ),
            (
                EventSide("форсаж", "Сбрось сколько угодно монет, передвинься на столько же клеток вперёд.",
                            "pay_coins_move_flexible"),
                EventSide("чужая удача", "Выбери другого игрока, он получает 10 монет.", "give_10_to_target", 10)
            ),
            (
                EventSide("подарок от Джо", "Тащи 2 карты Лавка Джо. Выбери одну и положи перед собой ничего не тратя. "
                            "Сбрось оставшиеся карты.", "draw_2_keep_1_free"),
                EventSide("красный откат", "Передвинься назад до ближайшей красной клетки. "
                    "Если позади тебя нет красной клетки, то передвинься на 3 клетки назад.", "move_back_to_red_or_3")
            ),
            (
                EventSide("cаботаж", "Можешь сбросить любое количество монет. "
                        "Остальные игроки передвигаются на столько же клеток назад.", "pay_coins_move_others_back"),
                EventSide("двойная неудача", "Тащи две карты Плохо.", "draw_2_bad")
            ),
        ]

        pairs_data = [
            (
                EventSide("ловушка", "Можешь положить по 1 своей монете на любые клетки. "
                                     "Когда любой игрок останавливается на клетке с монетой, "
                                     "он пропускает следующий ход, а эта монета сбрасывается. "
                                     "Эффект клетки, где лежит монета, не действует", "place_mines", 1),
                EventSide("инвентаризация", "Все игроки сбрасывают все свои карты Лавка Джо, кроме одной.",
                          "all_discard_to_one_shop_card")
            )
        ]

        deck_cards = []
        for i, (good, bad) in enumerate(pairs_data):
            deck_cards.append(EventCard(f"event_{i}", good, bad))
        return Deck(deck_cards, name="События")
