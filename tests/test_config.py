import json


class TestConfigDefaults:
    def test_uses_defaults_when_no_path(self):
        from core.config_manager import ConfigManager

        cm = ConfigManager(path=":memory:")
        assert cm.collection_enabled is True
        assert cm.watchers_enabled == ["foreground", "afk"]
        assert cm.log_level == "INFO"
        assert cm.get_interval("foreground", 30.0) == 30.0

    def test_uses_defaults_when_file_missing(self):
        from core.config_manager import ConfigManager

        cm = ConfigManager(path="/nonexistent/path/config.json")
        cm.load()
        assert cm.collection_enabled is True

    def test_uses_defaults_on_corrupt_json(self, tmp_path):
        from core.config_manager import ConfigManager

        p = tmp_path / "config.json"
        p.write_text("not valid json", encoding="utf-8")
        cm = ConfigManager(path=str(p))
        cm.load()
        assert cm.collection_enabled is True


class TestConfigLoad:
    def test_loads_from_file(self, tmp_path):
        from core.config_manager import ConfigManager

        p = tmp_path / "config.json"
        p.write_text(
            json.dumps({"collection_enabled": False, "watchers_enabled": ["afk"]}),
            encoding="utf-8",
        )
        cm = ConfigManager(path=str(p))
        cm.load()
        assert cm.collection_enabled is False
        assert cm.watchers_enabled == ["afk"]

    def test_load_merges_with_defaults(self, tmp_path):
        from core.config_manager import ConfigManager

        p = tmp_path / "config.json"
        p.write_text(json.dumps({"log_level": "DEBUG"}), encoding="utf-8")
        cm = ConfigManager(path=str(p))
        cm.load()
        assert cm.collection_enabled is True
        assert cm.log_level == "DEBUG"

    def test_load_with_Path_object(self, tmp_path):
        from core.config_manager import ConfigManager

        p = tmp_path / "config.json"
        p.write_text(json.dumps({"collection_enabled": False}), encoding="utf-8")
        cm = ConfigManager(path=p)
        cm.load()
        assert cm.collection_enabled is False

    def test_load_with_string_path(self, tmp_path):
        from core.config_manager import ConfigManager

        p = tmp_path / "config.json"
        p.write_text(json.dumps({"collection_enabled": False}), encoding="utf-8")
        cm = ConfigManager(path=str(p))
        cm.load()
        assert cm.collection_enabled is False


class TestConfigSave:
    def test_save_and_reload(self, tmp_path):
        from core.config_manager import ConfigManager

        p = tmp_path / "config.json"
        cm = ConfigManager(path=str(p))
        cm.collection_enabled = False
        cm.save()

        cm2 = ConfigManager(path=str(p))
        cm2.load()
        assert cm2.collection_enabled is False

    def test_save_creates_file(self, tmp_path):
        from core.config_manager import ConfigManager

        p = tmp_path / "nested" / "dir" / "config.json"
        cm = ConfigManager(path=str(p))
        cm.save()
        assert p.exists()
        assert json.loads(p.read_text(encoding="utf-8"))["collection_enabled"] is True


class TestConfigProperties:
    def test_get_interval_returns_override(self, tmp_path):
        from core.config_manager import ConfigManager

        p = tmp_path / "config.json"
        p.write_text(
            json.dumps({"tick_interval_overrides": {"foreground": 10.0}}),
            encoding="utf-8",
        )
        cm = ConfigManager(path=str(p))
        cm.load()
        assert cm.get_interval("foreground", 30.0) == 10.0

    def test_set_interval_adds_and_replaces_override(self, tmp_path):
        from core.config_manager import ConfigManager

        cm = ConfigManager(path=str(tmp_path / "config.json"))
        cm.set_interval("foreground", 7.5)
        assert cm.get_interval("foreground", 2.0) == 7.5

        cm.set_interval("foreground", 3.0)
        assert cm.get_interval("foreground", 2.0) == 3.0
        cm.save()

        cm2 = ConfigManager(path=str(tmp_path / "config.json"))
        cm2.load()
        assert cm2.get_interval("foreground", 2.0) == 3.0

    def test_set_interval_with_non_positive_removes_override(self, tmp_path):
        from core.config_manager import ConfigManager

        cm = ConfigManager(path=str(tmp_path / "config.json"))
        cm.set_interval("afk", 5.0)
        cm.set_interval("afk", 0)
        assert cm.get_interval("afk", 5.0) == 5.0

    def test_watchers_enabled_setter_roundtrip(self, tmp_path):
        from core.config_manager import ConfigManager

        cm = ConfigManager(path=str(tmp_path / "config.json"))
        cm.watchers_enabled = ["afk", "power"]
        assert cm.watchers_enabled == ["afk", "power"]
        cm.save()

        cm2 = ConfigManager(path=str(tmp_path / "config.json"))
        cm2.load()
        assert cm2.watchers_enabled == ["afk", "power"]

    def test_log_level_setter_uppercases(self, tmp_path):
        from core.config_manager import ConfigManager

        cm = ConfigManager(path=str(tmp_path / "config.json"))
        cm.log_level = "debug"
        assert cm.log_level == "DEBUG"

    def test_theme_mode_default_and_roundtrip(self, tmp_path):
        from core.config_manager import ConfigManager

        cm = ConfigManager(path=str(tmp_path / "config.json"))
        assert cm.theme_mode == "system"
        cm.theme_mode = "dark"
        assert cm.theme_mode == "dark"
        cm.save()

        cm2 = ConfigManager(path=str(tmp_path / "config.json"))
        cm2.load()
        assert cm2.theme_mode == "dark"

    def test_auto_update_and_start_maximized_defaults(self, tmp_path):
        from core.config_manager import ConfigManager

        cm = ConfigManager(path=str(tmp_path / "config.json"))
        assert cm.auto_update_enabled is True
        assert cm.start_maximized is True
        cm.auto_update_enabled = False
        cm.start_maximized = False
        assert cm.auto_update_enabled is False
        assert cm.start_maximized is False

    def test_afk_thresholds_defaults_and_clamping(self, tmp_path):
        from core.config_manager import ConfigManager

        cm = ConfigManager(path=str(tmp_path / "config.json"))
        assert cm.afk_idle_threshold_s == 60.0
        assert cm.afk_away_threshold_s == 300.0

        cm.afk_idle_threshold_s = 15
        cm.afk_away_threshold_s = -5
        assert cm.afk_idle_threshold_s == 15.0
        assert cm.afk_away_threshold_s == 0.0
        cm.save()

        cm2 = ConfigManager(path=str(tmp_path / "config.json"))
        cm2.load()
        assert cm2.afk_idle_threshold_s == 15.0
        assert cm2.afk_away_threshold_s == 0.0

    def test_get_interval_falls_back_to_default(self, tmp_path):
        from core.config_manager import ConfigManager

        cm = ConfigManager(path=str(tmp_path / "missing.json"))
        cm.load()
        assert cm.get_interval("foreground", 30.0) == 30.0

    def test_watchers_enabled_from_file(self, tmp_path):
        from core.config_manager import ConfigManager

        p = tmp_path / "config.json"
        p.write_text(json.dumps({"watchers_enabled": ["afk"]}), encoding="utf-8")
        cm = ConfigManager(path=str(p))
        cm.load()
        assert cm.watchers_enabled == ["afk"]

    def test_save_preserves_data(self, tmp_path):
        from core.config_manager import ConfigManager

        cm = ConfigManager(path=str(tmp_path / "config.json"))
        cm.collection_enabled = False
        cm.save()

        cm2 = ConfigManager(path=str(tmp_path / "config.json"))
        cm2.load()
        assert cm2.collection_enabled is False
        assert cm2.watchers_enabled == ["foreground", "afk"]
        assert cm2.log_level == "INFO"
