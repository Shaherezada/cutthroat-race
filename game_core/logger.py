import json
import os
from datetime import datetime

class GameLogger:
    def __init__(self):
        self.log_data = {
            "timestamp": datetime.now().isoformat(),
            "history": []
        }
        self._current_turn = 1
        # Создаем папку, если её нет
        if not os.path.exists("match_logs"):
            os.makedirs("match_logs")

    @property
    def current_turn(self):
        return self._current_turn

    def inc_turn(self):
        """Вызывается только в state.py при смене хода"""
        self._current_turn += 1

    def log_event(self, player_id: int, event_type: str, details: dict):
        entry = {
            "turn": self._current_turn,
            "player": player_id,
            "type": event_type,
            **details
        }
        self.log_data["history"].append(entry)
        # Сразу дублируем в консоль
        print(f"[Turn {self.current_turn}] Player {player_id+1}: {event_type} | {details}")

    def save(self, filename="match_logs/match.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.log_data, f, ensure_ascii=False, indent=2)
        print(f"Лог сохранен в {filename}")
