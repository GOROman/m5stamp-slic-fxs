import skidl
from skidl import Pin
# SKiDL 3.0 moved pin-type constants under Pin.types; the design file
# (written for the 1.x-style API) references Pin.PASSIVE directly.
if not hasattr(Pin, "PASSIVE"):
    Pin.PASSIVE = Pin.types.PASSIVE
import runpy, sys
sys.argv = ["m5stamp_slic2port.py"]
runpy.run_path("m5stamp_slic2port.py", run_name="__main__")
