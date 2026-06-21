import json, pytest
from unittest.mock import patch
import config

def test_get_config_raises_when_missing(tmp_path):
    with patch.object(config, 'CONFIG_PATH', tmp_path / 'nonexistent.json'):
        with pytest.raises(FileNotFoundError, match='配置文件不存在'):
            config.get_config()

def test_get_vault_path_returns_value(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'VAULT_PATH': '/my/vault', 'CHROME_PROFILE': '/p'}))
    with patch.object(config, 'CONFIG_PATH', cfg):
        assert config.get_vault_path() == '/my/vault'

def test_get_chrome_profile_returns_value(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'VAULT_PATH': '/v', 'CHROME_PROFILE': '/my/profile'}))
    with patch.object(config, 'CONFIG_PATH', cfg):
        assert config.get_chrome_profile() == '/my/profile'

def test_get_vault_path_raises_when_key_missing(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'CHROME_PROFILE': '/p'}))
    with patch.object(config, 'CONFIG_PATH', cfg):
        with pytest.raises(KeyError, match='VAULT_PATH'):
            config.get_vault_path()

def test_get_chrome_profile_raises_when_key_missing(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'VAULT_PATH': '/v'}))
    with patch.object(config, 'CONFIG_PATH', cfg):
        with pytest.raises(KeyError, match='CHROME_PROFILE'):
            config.get_chrome_profile()

def test_set_config_creates_file_and_parent_dir(tmp_path):
    cfg = tmp_path / 'sub' / 'config.json'
    with patch.object(config, 'CONFIG_PATH', cfg):
        config.set_config('VAULT_PATH', '/v')
        assert cfg.exists()
        assert json.loads(cfg.read_text())['VAULT_PATH'] == '/v'

def test_set_config_preserves_existing_keys(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'CHROME_PROFILE': '/p'}))
    with patch.object(config, 'CONFIG_PATH', cfg):
        config.set_config('VAULT_PATH', '/v')
        data = json.loads(cfg.read_text())
        assert data['CHROME_PROFILE'] == '/p'
        assert data['VAULT_PATH'] == '/v'
