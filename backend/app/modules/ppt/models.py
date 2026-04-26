from dataclasses import dataclass, field


@dataclass(frozen=True)
class DeckRequest:
    raw_prompt: str
    chat_history: str
    generation_mode: str
    template_preference: str = "auto"


@dataclass(frozen=True)
class DeckPagePlan:
    index: int
    title: str
    page_type: str
    page_rhythm: str
    brief: str


@dataclass(frozen=True)
class DeckPlan:
    project_name: str
    template_id: str | None
    pages: tuple[DeckPagePlan, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "pages", tuple(self.pages))
