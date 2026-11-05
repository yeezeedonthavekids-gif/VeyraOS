"""veyra-steam-setup — enable Steam Play (Proton Experimental) for all games."""
import sys

from . import steam


def main() -> int:
    try:
        changed = steam.enable_steam_play()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    if not steam.steam_roots():
        print("Steam has not been started yet: start Steam once, sign in, exit, then run this again.")
        return 1
    print("Updated: " + ", ".join(changed) if changed else "Proton Experimental is already the default.")
    return 0
