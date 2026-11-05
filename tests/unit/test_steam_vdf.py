import os

from veyra.gaming import steam

SAMPLE = '''"InstallConfigStore"
{
	"Software"
	{
		"valve"
		{
			"Steam"
			{
				"AutoUpdateWindowEnabled"		"0"
				"CompatToolMapping"
				{
					"570"
					{
						"name"		""
						"config"		""
						"priority"		"250"
					}
				}
				"Path \\"quoted\\""		"C:\\\\x"
			}
		}
	}
	"Music"
	{
		"CrawlSteamInstallFolders"		"1"
	}
}
'''


def test_roundtrip_preserves_data():
    d = steam.loads(SAMPLE)
    assert steam.loads(steam.dumps(d)) == d
    assert d["InstallConfigStore"]["Software"]["valve"]["Steam"]['Path "quoted"'] == "C:\\x"


def test_set_default_tool_keeps_other_entries(tmp_path):
    cfg = tmp_path / "config.vdf"
    cfg.write_text(SAMPLE)
    steam.set_default_compat_tool(str(cfg), backup=True)
    d = steam.loads(cfg.read_text())
    m = d["InstallConfigStore"]["Software"]["valve"]["Steam"]["CompatToolMapping"]
    assert m["0"]["name"] == "proton_experimental"
    assert m["570"]["priority"] == "250"          # per-game override untouched
    assert d["InstallConfigStore"]["Music"]["CrawlSteamInstallFolders"] == "1"
    # case-insensitive path: must not create a second "Valve" node
    assert "Valve" not in d["InstallConfigStore"]["Software"]
    assert steam.get_default_compat_tool(str(cfg)) == "proton_experimental"
    assert any(p.name.startswith("config.vdf.veyra-backup-") for p in tmp_path.iterdir())


def test_create_when_missing(tmp_path):
    cfg = tmp_path / "config" / "config.vdf"
    steam.set_default_compat_tool(str(cfg))
    assert steam.get_default_compat_tool(str(cfg)) == "proton_experimental"


def test_enable_steam_play_no_steam(tmp_path, monkeypatch):
    monkeypatch.setattr(steam, "steam_running", lambda: False)
    assert steam.enable_steam_play(home=str(tmp_path)) == []


def test_enable_steam_play_refuses_when_running(tmp_path, monkeypatch):
    monkeypatch.setattr(steam, "steam_running", lambda: True)
    try:
        steam.enable_steam_play(home=str(tmp_path))
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError")


def test_enable_steam_play_existing_install(tmp_path, monkeypatch):
    monkeypatch.setattr(steam, "steam_running", lambda: False)
    root = tmp_path / ".local/share/Steam/config"
    root.mkdir(parents=True)
    (root / "config.vdf").write_text(SAMPLE)
    os.symlink(tmp_path / ".local/share/Steam", tmp_path / "steamlink")
    changed = steam.enable_steam_play(home=str(tmp_path))
    assert len(changed) == 1
    assert steam.enable_steam_play(home=str(tmp_path)) == []   # idempotent


def test_bad_vdf_raises():
    for bad in ('"a" { "b" "c"', '"a" }', '"unterminated'):
        try:
            steam.loads(bad)
        except steam.VdfError:
            continue
        raise AssertionError(bad)
