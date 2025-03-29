import os
import sys

# sys.path.append(os.path.dirname(os.path.realpath(__file__)))

package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if package_dir not in sys.path:
    sys.path.insert(0, package_dir)

from .general_model import StatusModel

from .player_model import PlayerModel
from .match_model import MatchModel, DetailedMatchData
from .heros_model import HeroModel, HeroCollection

from .model_managers import MatchManager, HeroManager, PlayerManager
