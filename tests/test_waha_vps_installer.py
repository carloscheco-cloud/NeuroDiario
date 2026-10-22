"""Ejercita fallos de instalación sin tocar Docker ni enviar mensajes."""
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def installation(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('installer', Path(__file__).parents[1] / 'scripts/install_waha_vps.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = tmp_path / 'NeuroDiario'
    root.mkdir()
    originals = {'scheduler/a.py': 'old scheduler\n', 'docker-compose.yml': 'old compose\n'}
    for name, content in originals.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    package = {'expected': {name: hashlib.sha256(content.encode()).hexdigest() for name, content in originals.items()},
               'files': {'scheduler/a.py': 'new scheduler\n', 'docker-compose.yml': 'new compose\n', 'publisher/new.py': 'new transport\n'}}
    calls = []
    def run(args, data=None, visible=False):
        calls.append(args)
        if args[:3] == ['docker', 'exec', '-w']:
            return json.dumps({'scheduler/a.py': package['expected']['scheduler/a.py']})
        return ''
    app = {'Config': {'Labels': {'com.docker.compose.service': 'neurodiario'}, 'WorkingDir': '/app', 'Image': 'neurodiario:old'}, 'Image': 'sha256:old'}
    monkeypatch.setattr(module, 'ROOT', root)
    monkeypatch.setattr(module, 'ENV', tmp_path / '.NeuroDiario-waha.env')
    monkeypatch.setattr(module, 'payload', lambda: package)
    monkeypatch.setattr(module, 'inspect', lambda name: app if name == module.APP else {'Config': {'Env': ['WAHA_API_KEY=test-secret']}})
    monkeypatch.setattr(module.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(module.sys, 'argv', ['install_waha_vps.py'])
    monkeypatch.setattr(module, 'run', run)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=0, stdout='Canal verificado', stderr=''))
    return module, originals, calls, run


def test_rejects_changed_source_before_docker(installation):
    module, originals, calls, run = installation
    (module.ROOT / 'scheduler/a.py').write_text('local customization')
    with pytest.raises(RuntimeError, match='Versión diferente'):
        module.main()
    assert calls == []
    assert not module.ENV.exists()


def test_permission_failure_leaves_sources_untouched(installation, monkeypatch):
    module, originals, calls, run = installation
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **kw: SimpleNamespace(returncode=2, stdout='Falta permiso de administrador', stderr=''))
    with pytest.raises(RuntimeError, match='antes de cambiar archivos'):
        module.main()
    assert all((module.ROOT / p).read_text() == content for p, content in originals.items())
    assert not module.ENV.exists()
    assert not (module.ROOT / 'publisher/new.py').exists()


@pytest.mark.parametrize('failed_stage', ['build', 'migration', 'restart'])
def test_failed_install_restores_files_and_image(installation, monkeypatch, failed_stage):
    module, originals, calls, run = installation
    failed = False
    def failing_run(args, **kw):
        nonlocal failed
        result = run(args, **kw)
        trigger = ((failed_stage == 'build' and 'build' in args)
                   or (failed_stage == 'migration' and 'migrate_whatsapp_publications.py' in args)
                   or (failed_stage == 'restart' and 'up' in args))
        if trigger and not failed:
            failed = True
            raise RuntimeError('simulated failure')
        return result
    monkeypatch.setattr(module, 'run', failing_run)
    with pytest.raises(RuntimeError, match='Se restauraron'):
        module.main()
    assert all((module.ROOT / p).read_text() == content for p, content in originals.items())
    assert not (module.ROOT / 'publisher/new.py').exists()
    assert not module.ENV.exists()
    assert ['docker', 'image', 'tag', 'sha256:old', 'neurodiario:old'] in calls
    assert sum('up' in args for args in calls) == (2 if failed_stage == 'restart' else 0)


def test_check_only_never_builds_or_restarts(installation, monkeypatch):
    module, originals, calls, run = installation
    monkeypatch.setattr(module.sys, 'argv', ['install_waha_vps.py', '--check-only'])
    module.main()
    assert not any('build' in args or 'up' in args for args in calls)
    assert not module.ENV.exists()


def test_success_stores_private_config_and_enables_after_checks(installation):
    module, originals, calls, run = installation
    module.main()
    assert module.ENV.stat().st_mode & 0o777 == 0o600
    assert 'WHATSAPP_ENABLED=true' in module.ENV.read_text()
    assert 'test-secret' not in (module.ROOT / 'docker-compose.yml').read_text()
    assert next(i for i, args in enumerate(calls) if 'migrate_whatsapp_publications.py' in args) < next(i for i, args in enumerate(calls) if 'up' in args)
