from streamcontroller_plugin_tools import BackendBase
from tzlocal import get_localzone

class Backend(BackendBase):
    def __init__(self):
        super().__init__()

    def get_local_timezone(self) -> str:
        return str(get_localzone())

backend = Backend()