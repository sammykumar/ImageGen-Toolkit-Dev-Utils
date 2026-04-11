from . import workflow_import_bridge as _workflow_import_bridge
from .load_video_url_node import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

WEB_DIRECTORY = "./js"
REGISTERED_ROUTE_MODULES = (_workflow_import_bridge,)

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

