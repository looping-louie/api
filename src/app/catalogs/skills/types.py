"""Stable business taxonomy for skill catalog entries."""

from enum import StrEnum


class SkillCategory(StrEnum):
    """Broad company area responsible for applying a skill."""

    SOFTWARE_ENGINEERING = "software_engineering"
    QUALITY_RELIABILITY = "quality_reliability"
    SECURITY_PRIVACY = "security_privacy"
    DATA_AI = "data_ai"
    PRODUCT_DISCOVERY_STRATEGY = "product_discovery_strategy"
    PRODUCT_DESIGN_UX = "product_design_ux"
    DELIVERY_PLANNING = "delivery_planning"
    CONTENT_BRAND = "content_brand"
    GROWTH_ACQUISITION = "growth_acquisition"
    RESEARCH_ANALYTICS = "research_analytics"
    SALES = "sales"
    CUSTOMER_SUCCESS_SUPPORT = "customer_success_support"


class SkillStatus(StrEnum):
    """Workspace availability states accepted by skill listings."""

    ENABLED = "enabled"
    DISABLED = "disabled"


class SkillSort(StrEnum):
    """Supported ordering for skill catalog queries."""

    ALPHABETICAL_ASC = "alphabetical-asc"
    ALPHABETICAL_DESC = "alphabetical-desc"
    NEWEST = "newest"
    OLDEST = "oldest"
