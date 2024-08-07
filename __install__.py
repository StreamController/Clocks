import urllib.request
from os.path import join, abspath, dirname
from streamcontroller_plugin_tools.installation_helpers import create_venv

toplevel = dirname(abspath(__file__))

urllib.request.urlretrieve("https://raw.githubusercontent.com/Core447/analog-clock/main/analog_clock/AnalogClockGenerator.py", join(toplevel, "AnalogClockGenerator.py"))

toplevel = dirname(abspath(__file__))
create_venv(join(toplevel, "backend", ".venv"), join(toplevel, "backend", "requirements.txt"))