from .blueprint import bp

# Import submodules so decorators register endpoints on shared blueprint.
from .publish_routes import *  # noqa: F401,F403
from .review_routes import *  # noqa: F401,F403
from .stats_routes import *  # noqa: F401,F403

