import os

import pytest

from engine import assets


def _point_to(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setattr(assets, "ROOT", str(tmp_path))
    monkeypatch.setattr(assets, "DATA", str(data))
    monkeypatch.setattr(assets, "FONT_DIR", str(data / "fonts"))
    monkeypatch.setattr(assets, "COUNTIES", str(data / "counties.json"))


def test_font_paths_under_data():
    for key in assets.FONTS:
        assert assets.font_path(key).startswith(assets.FONT_DIR)


def test_ensure_moves_old_layout(tmp_path, monkeypatch):
    _point_to(tmp_path, monkeypatch)
    (tmp_path / "fonts").mkdir()
    (tmp_path / "counties.json").write_bytes(b"x" * 2000)
    for key in assets.FONTS:
        (tmp_path / "fonts" / os.path.basename(assets.FONTS[key])).write_bytes(b"y" * 2000)

    def no_download(*args, **kwargs):
        raise AssertionError("indirme yapılmamalıydı")

    monkeypatch.setattr(assets.urllib.request, "urlretrieve", no_download)
    assets.ensure(log=lambda m: None)
    assert assets.missing() == []
    assert not (tmp_path / "counties.json").exists()


def test_ensure_reports_download_failure(tmp_path, monkeypatch):
    _point_to(tmp_path, monkeypatch)

    def broken(*args, **kwargs):
        raise OSError("ağ yok")

    monkeypatch.setattr(assets.urllib.request, "urlretrieve", broken)
    with pytest.raises(assets.AssetError, match="counties.json"):
        assets.ensure(log=lambda m: None)


def test_real_data_and_fonts_load():
    assets.ensure(log=lambda m: None)  # eski kökteki dosyaları data/ altına taşır
    assert assets.missing() == []
    assert set(assets.fonts()) == {"bebas", "regular", "semibold", "bold"}
