from app.models.user import User
from app.models.cv import CV
from app.models.job import Job
from app.models.interaction import UserInteraction, InteractionAction
from app.models.model_version import ModelVersion
from app.models.recommendation import Recommendation
from app.models.analytics_log import AnalyticsLog
from app.models.crawl_log import CrawlLog

__all__ = [
    "User", "CV", "Job", "UserInteraction", "InteractionAction",
    "ModelVersion", "Recommendation", "AnalyticsLog", "CrawlLog",
]

