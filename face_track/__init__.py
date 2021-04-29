import sys

if sys.version_info.major < 3:
    msg = 'Dashboard Requires Python 3.7 or greater. You are using {}'.format(sys.version)
    raise ValueError(msg)

__version__ = '1.0.0'

from .mockdjitellopy import Tello, BackgroundFrameRead
from .pid import PID