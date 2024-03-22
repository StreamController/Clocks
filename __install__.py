import urllib.request
from os.path import join, abspath, dirname

toplevel = dirname(abspath(__file__))

urllib.request.urlretrieve("https://raw.githubusercontent.com/Core447/analog-clock/main/analog_clock/AnalogClockGenerator.py", join(toplevel, "AnalogClockGenerator.py"))