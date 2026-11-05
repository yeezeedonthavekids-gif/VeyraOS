from veyra.software import backend
from veyra.software.catalog import CATEGORIES, catalog
from veyra.update import app as upd

PACMAN_SS = """extra/firefox 144.0-1 [installed]
    Fast, Private & Safe Web Browser
extra/firefox-i18n-de 144.0-1
    German language pack for Firefox
world/discord 1:0.0.110-1 [installed: 1:0.0.109-1]
    All-in-one voice and text chat
"""


def test_pacman_search():
    apps = backend.parse_pacman_search(PACMAN_SS)
    assert [a.id for a in apps] == ["firefox", "firefox-i18n-de", "discord"]
    assert apps[0].installed and not apps[1].installed and apps[2].installed
    assert apps[0].summary.startswith("Fast")
    assert apps[2].repo == "world" and apps[2].version == "1:0.0.110-1"


def test_flatpak_search():
    out = "Spotify\tOnline music streaming service\tcom.spotify.Client\t1.2.60\tflathub\n" \
          "No matches found\n"
    apps = backend.parse_flatpak_search(out)
    assert len(apps) == 1 and apps[0].id == "com.spotify.Client" and apps[0].source == "flatpak"


def test_flatpak_list_and_explicit():
    assert backend.parse_flatpak_list("Spotify\tcom.spotify.Client\t1.2\n")[0].installed
    ex = backend.parse_pacman_explicit("firefox 144.0-1\nsteam 1.0.0.81-1\n")
    assert [a.id for a in ex] == ["firefox", "steam"]


def test_install_argv_uses_helper_for_repo(monkeypatch):
    monkeypatch.delenv("VEYRA_HELPER_DRYRUN", raising=False)
    a = backend.App("firefox", "Firefox", "", "repo")
    assert backend.install_argv(a)[:2] == ["pkexec", "/usr/lib/veyra/veyra-helper"]
    f = backend.App("com.spotify.Client", "Spotify", "", "flatpak")
    assert backend.install_argv(f)[0] == "flatpak" and "flathub" in backend.install_argv(f)


def test_catalog_is_sane():
    cats = {c[0] for c in CATEGORIES}
    ids = set()
    for a in catalog():
        assert a.category in cats
        assert a.source in ("repo", "flatpak")
        if a.source == "flatpak":
            assert a.id.count(".") >= 2, a.id
        else:
            assert a.id == a.id.lower() and " " not in a.id
        assert a.id not in ids, "duplicate " + a.id
        ids.add(a.id)


def test_checkupdates_parse():
    ups = upd.parse_checkupdates("linux 6.17.1.arch1-1 -> 6.17.2.arch1-1\nmesa 1:25.2.1-1 -> 1:25.2.2-1\nbad line\n")
    assert [(u.name, u.new) for u in ups] == [("linux", "6.17.2.arch1-1"), ("mesa", "1:25.2.2-1")]
    fl = upd.parse_flatpak_updates("com.spotify.Client\t1.2.61\n")
    assert fl[0].source == "flatpak"


def test_news_parse():
    import email.utils
    import time
    now = email.utils.formatdate(time.time())
    old = email.utils.formatdate(time.time() - 400 * 86400)
    xml = f"""<?xml version="1.0"?><rss><channel>
      <item><title>Manual intervention needed</title><link>https://archlinux.org/news/x/</link><pubDate>{now}</pubDate></item>
      <item><title>Old</title><link>https://archlinux.org/news/y/</link><pubDate>{old}</pubDate></item>
    </channel></rss>"""
    items = upd.parse_news(xml, "Arch Linux")
    assert len(items) == 1 and items[0][2] == "Manual intervention needed"
    assert upd.parse_news("<<not xml", "x") == []
