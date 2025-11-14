from app.utils import log
from app.services.steam.main import main

from app.utils import ctrl

if __name__ == '__main__':
    ctrl.main_with_parses(None, main)
