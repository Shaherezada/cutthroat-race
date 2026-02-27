from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from ui.components import Dialog, SliderDialog
    from game_core.cards import RuleCard, EventCard, ShopCard
    from game_core.state import Player


@dataclass
class UIState:
    # Диалоги
    active_dialog: Optional[Dialog] = None
    active_slider: Optional[SliderDialog] = None

    pending_shop_cards: List[ShopCard] = field(default_factory=list)
    pending_event_card: Optional[EventCard] = None
    pending_event_is_good: bool = True
    pending_selection_rects: list = field(default_factory=list)
    sidebar_card_rects: list = field(default_factory=list)
    pending_card_use_idx: Optional[int] = None
    end_turn_btn_rect: Optional[pygame.Rect] = None
    showing_event_card_sidebar: bool = False
    event_card_ok_rect: Optional[pygame.Rect] = None
    event_card_auto_close_at: Optional[int] = None  # ms, pygame.time.get_ticks()

    # Та-Дам
    pending_tadam_rule: Optional[RuleCard] = None
    viewing_card_sprite_id: Optional[int] = None

    # Специальные механики
    pending_tornado_target: Optional[int] = None
    pending_move_options: List[int] = field(default_factory=list)
    pending_finish_result: Optional[tuple] = None
    duel_defender: Optional[Player] = None

    # Расстановка мин
    mine_placement_mode: bool = False
    mine_placement_player: Optional[Player] = None

    @property
    def is_busy(self) -> bool:
        """Есть ли активное окно/режим, блокирующий основной ввод"""
        return bool(
            self.active_dialog or self.active_slider
            or self.viewing_card_sprite_id or self.mine_placement_mode
            or self.showing_event_card_sidebar
        )

    def clear_dialog(self):
        self.active_dialog = None

    def clear_card_selection(self):
        self.pending_shop_cards = []
        self.pending_selection_rects = []
