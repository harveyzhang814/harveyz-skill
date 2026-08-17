import json, os, subprocess, sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
import config

_SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'


def test_get_config_raises_when_missing(tmp_path):
    with patch.object(config, 'CONFIG_PATH', tmp_path / 'nonexistent.json'):
        with pytest.raises(FileNotFoundError, match='配置文件不存在'):
            config.get_config()


def test_get_data_dir_returns_value(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'DATA_DIR': '/my/data'}))
    with patch.object(config, 'CONFIG_PATH', cfg):
        assert config.get_data_dir() == '/my/data'


def test_get_data_dir_raises_when_key_missing(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({}))
    with patch.object(config, 'CONFIG_PATH', cfg):
        with pytest.raises(KeyError, match='DATA_DIR'):
            config.get_data_dir()


def test_set_config_creates_file_and_parent_dir(tmp_path):
    cfg = tmp_path / 'sub' / 'config.json'
    with patch.object(config, 'CONFIG_PATH', cfg):
        config.set_config('DATA_DIR', '/d')
        assert cfg.exists()
        assert json.loads(cfg.read_text())['DATA_DIR'] == '/d'


def test_set_config_preserves_existing_keys(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'OTHER_KEY': 'x'}))
    with patch.object(config, 'CONFIG_PATH', cfg):
        config.set_config('DATA_DIR', '/d')
        data = json.loads(cfg.read_text())
        assert data['OTHER_KEY'] == 'x'
        assert data['DATA_DIR'] == '/d'


def test_config_path_env_override(tmp_path):
    cfg = tmp_path / 'custom.json'
    cfg.write_text(json.dumps({'DATA_DIR': '/env/data'}))
    result = subprocess.run(
        ['python3', '-c', 'import config; print(config.get_data_dir())'],
        env={**os.environ, 'HSKILL_SYNC_XTIMELINE_CONFIG': str(cfg)},
        capture_output=True, text=True,
        cwd=str(_SCRIPTS_DIR)
    )
    assert result.returncode == 0, result.stderr
    assert '/env/data' in result.stdout.strip()
