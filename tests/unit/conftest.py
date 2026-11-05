import os
import sys

TOP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(TOP, "src", "apps", "usr", "lib", "veyra", "python"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
