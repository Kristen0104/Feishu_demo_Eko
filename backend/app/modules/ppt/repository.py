from __future__ import annotations

from app.modules.ppt.schemas import PptDeckSchema


class PptRepository:
    def __init__(self) -> None:
        self._decks: dict[str, PptDeckSchema] = {}

    def save(self, deck: PptDeckSchema) -> PptDeckSchema:
        self._decks[deck.deck_id] = deck
        return deck

    def get(self, deck_id: str) -> PptDeckSchema:
        try:
            return self._decks[deck_id]
        except KeyError as exc:
            raise KeyError(f"deck {deck_id} not found") from exc
