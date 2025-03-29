import os
import sys

# sys.path.append(os.path.dirname(os.path.realpath(__file__)))
package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if package_dir not in sys.path:
    sys.path.insert(0, package_dir)

from .errors import *
