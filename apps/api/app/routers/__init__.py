"""路由模块初始化"""

from app.routers.health import router as health_router
from app.routers.streams import router as streams_router
from app.routers.events import router as events_router
from app.routers.reviews import router as reviews_router
from app.routers.clips import router as clips_router
from app.routers.training import router as training_router
from app.routers.metrics import router as metrics_router
from app.routers.system import router as system_router

__all__ = [
    "health_router",
    "streams_router",
    "events_router",
    "reviews_router",
    "clips_router",
    "training_router",
    "metrics_router",
    "system_router"
]
