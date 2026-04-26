"""Eko 对 vendored ppt_master 工作流的桥接层。"""

from .config import DesignConfig, load_config
from .generator import AipptGenerator
from .models import DeckPagePlan, DeckPlan, DeckRequest
from .template_import import TemplateImportService, ImportedTemplatePack
from .template_pack import TemplatePack
from .templates import TemplateLibrary, validate_svg

__all__ = [
    "AipptGenerator",
    "DeckPagePlan",
    "DeckPlan",
    "DeckRequest",
    "ImportedTemplatePack",
    "DesignConfig",
    "TemplateImportService",
    "TemplatePack",
    "TemplateLibrary",
    "load_config",
    "validate_svg",
]
