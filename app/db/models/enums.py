import enum


class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    banned = "banned"


class PantryItemSource(str, enum.Enum):
    manual = "manual"
    ocr_confirmed = "ocr_confirmed"
    ai_assisted = "ai_assisted"


class ExpiryStatus(str, enum.Enum):
    fresh = "fresh"
    warning = "warning"
    expired = "expired"


class AiRequestType(str, enum.Enum):
    recipe_suggestion = "recipe_suggestion"
    meal_plan = "meal_plan"
    ingredient_substitution = "ingredient_substitution"


class AiRequestStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    done = "done"
    failed = "failed"


class NotificationType(str, enum.Enum):
    expiry_reminder = "expiry_reminder"
    ai_tip = "ai_tip"
    system = "system"


class DeliveryChannel(str, enum.Enum):
    in_app = "in_app"
    push = "push"
    email = "email"


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class MealPlanStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class OcrParseStatus(str, enum.Enum):
    uploaded = "uploaded"
    parsed = "parsed"
    failed = "failed"
