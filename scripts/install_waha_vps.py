#!/usr/bin/env python3
"""Instalación localizada para el VPS de NeuroDiario, sin checkout ni merge.

El payload conserva el scheduler y MediaAsset del commit 313a193 del VPS.
Verifica hashes antes de modificar, respalda fuentes e imagen y añade una tabla.
No imprime credenciales ni publica mensajes durante el chequeo.
"""
import argparse
import base64
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zlib

PAYLOAD = "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"
ROOT = Path('/opt/apps/NeuroDiario')
ENV = Path('/opt/apps/.NeuroDiario-waha.env')
APP = 'neurodiario_app'
ASSISTANT = 'universidad-asistente-asistente-1'


def payload():
    return json.loads(zlib.decompress(base64.b64decode(PAYLOAD)))


def run(args, data=None, visible=False):
    result = subprocess.run(args, input=data, text=True,
                            stdout=None if visible else subprocess.PIPE,
                            stderr=None if visible else subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('Falló el paso: ' + ' '.join(args[:4]))
    return result.stdout or ''


def inspect(name):
    return json.loads(run(['docker', 'inspect', name]))[0]


def check_sources(root, package):
    for name, expected in package['expected'].items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Versión diferente en ' + name + '; no se ha aplicado ningún cambio.')
    for name in package['files'].keys() - package['expected'].keys():
        if (root / name).exists():
            raise RuntimeError('Ya existe ' + name + '; revisar la instalación antes de continuar.')


def env_text(key, channel, start, enabled):
    if any('\n' in value or '\r' in value or "'" in value for value in (key, channel, start)):
        raise RuntimeError('Valor de configuración inválido.')
    return (
        'WHATSAPP_ENABLED=' + ('true' if enabled else 'false') + '\n'
        'WAHA_URL=http://universidad-waha-1:3000\n'
        "WAHA_API_KEY='" + key + "'\n"
        'WAHA_SESSION=default\n'
        'WHATSAPP_CHANNEL_ID=' + channel + '\n'
        'WHATSAPP_START_AT=' + start + '\n'
    )


def write_private(path, content):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(content)
    path.chmod(0o600)


CHECK_CHANNEL = r'''
import json,sys,urllib.request,urllib.error
from urllib.parse import quote
c=json.load(sys.stdin)
def get(path):
    request=urllib.request.Request('http://universidad-waha-1:3000'+path,headers={'X-Api-Key':c['key']})
    try:
        with urllib.request.urlopen(request,timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        print('WAHA rechazó la comprobación: HTTP '+str(error.code));sys.exit(2)
    except Exception:
        print('No se pudo comprobar WAHA por la red interna.');sys.exit(2)
session=get('/api/sessions/default')
if session.get('status')!='WORKING':
    print('La sesión default de WAHA no está en WORKING.');sys.exit(2)
channel=get('/api/default/channels/'+quote(c['channel'],safe=''))
if channel.get('id')!=c['channel'] or channel.get('role') not in ('OWNER','ADMIN'):
    print('Añade el número conectado a WAHA como administrador del canal y acepta la invitación en WhatsApp.');sys.exit(2)
print('CORRECTO: sesión activa y permiso de administrador del canal.')
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', default='120363412361118712@newsletter')
    parser.add_argument('--check-only', action='store_true', help='Comprobar sin cambiar archivos ni publicar.')
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise RuntimeError('Ejecuta este instalador como root en el VPS.')
    import re
    if not re.fullmatch(r'\d+@newsletter', args.channel):
        raise RuntimeError('El canal debe tener un ID numérico terminado en @newsletter.')
    package = payload()
    check_sources(ROOT, package)
    if ENV.exists():
        raise RuntimeError('Ya existe la configuración WAHA de NeuroDiario; revisar antes de reinstalar.')
    app = inspect(APP)
    labels = app['Config'].get('Labels') or {}
    if labels.get('com.docker.compose.service') != 'neurodiario' or app['Config']['WorkingDir'] != '/app':
        raise RuntimeError('El contenedor no coincide con la instalación revisada.')
    # Evita reemplazar cambios que solo existan dentro del contenedor activo.
    python_files = [name for name in package['expected'] if name.endswith('.py')]
    hash_code = 'import hashlib,json;from pathlib import Path;print(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ' + repr(python_files) + '}))'
    live_hashes = json.loads(run(['docker', 'exec', '-w', '/app', APP, 'python', '-c', hash_code]))
    if any(live_hashes.get(name) != package['expected'][name] for name in python_files):
        raise RuntimeError('El código activo difiere de las fuentes del VPS; no se ha modificado nada.')
    try:
        entries = inspect(ASSISTANT)['Config']['Env']
        key = next((item.split('=', 1)[1] for item in entries if item.startswith('WAHA_API_KEY=')), '')
    except Exception:
        key = ''
    if not key:
        key = getpass.getpass('Clave original de WAHA (no se mostrará): ')
    if not key or key.startswith('sha512:'):
        raise RuntimeError('Se requiere la clave original de WAHA, no su hash.')
    probe = subprocess.run(['docker', 'exec', '-i', APP, 'python', '-c', CHECK_CHANNEL],
                           input=json.dumps({'key': key, 'channel': args.channel}),
                           text=True, capture_output=True)
    if probe.returncode:
        print(probe.stdout.strip() or 'No se pudo verificar el canal de WAHA.')
        raise RuntimeError('Instalación detenida antes de cambiar archivos. Corrige la comprobación y vuelve a ejecutar.')
    print(probe.stdout.strip(), flush=True)
    if args.check_only:
        print('Comprobación completada; no se ha cambiado ni publicado nada.')
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    start = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    backup = ROOT.parent / ('NeuroDiario-backup-waha-' + stamp)
    backup.mkdir(mode=0o700)
    for name in package['expected']:
        target = backup / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    old_tag = 'neurodiario-antes-waha:' + stamp.lower()
    run(['docker', 'image', 'tag', app['Image'], old_tag])
    compose = ['docker', 'compose', '--project-directory', str(ROOT), '-f', str(ROOT / 'docker-compose.yml')]
    restart_started = False
    try:
        for name, content in package['files'].items():
            target = ROOT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        write_private(ENV, env_text(key, args.channel, start, False))
        run(compose + ['config', '--quiet'])
        print('Respaldo: ' + str(backup), flush=True)
        print('Construyendo NeuroDiario; el contenedor actual sigue funcionando...', flush=True)
        run(compose + ['build', 'neurodiario'], visible=True)
        run(compose + ['run', '--rm', '--no-deps', 'neurodiario', 'python', 'migrate_whatsapp_publications.py'], visible=True)
        run(compose + ['run', '--rm', '--no-deps', 'neurodiario', 'python', '-m', 'neurodiario.tools.check_waha'], visible=True)
        # Solo las noticias con fecha de publicación desde este momento entran a WhatsApp.
        write_private(ENV, env_text(key, args.channel, start, True))
        restart_started = True
        run(compose + ['up', '-d', '--no-deps', 'neurodiario'], visible=True)
        verify = "from neurodiario.config.settings import settings;from neurodiario.publisher.whatsapp_publisher import get_whatsapp_config;assert get_whatsapp_config(settings) is not None;print('CORRECTO: WhatsApp habilitado en NeuroDiario')"
        run(['docker', 'exec', APP, 'python', '-c', verify], visible=True)
    except Exception:
        # La tabla nueva se conserva; las tablas existentes nunca se alteran.
        for name in package['expected']:
            shutil.copy2(backup / name, ROOT / name)
        for name in package['files'].keys() - package['expected'].keys():
            (ROOT / name).unlink(missing_ok=True)
        ENV.unlink(missing_ok=True)
        run(['docker', 'image', 'tag', app['Image'], app['Config']['Image']])
        if restart_started:
            run(compose + ['up', '-d', '--no-deps', 'neurodiario'], visible=True)
        raise RuntimeError('La instalación no se completó. Se restauraron las fuentes y la imagen anteriores. Respaldo: ' + str(backup)) from None
    (backup / 'installation.json').write_text(json.dumps({'channel': args.channel, 'start_at': start, 'previous_image': old_tag}, indent=2))
    print('LISTO: WAHA habilitado en el mismo ciclo de Telegram, cada 12 minutos.')
    print('Inicio de distribución: ' + start + '; no se enviará el histórico anterior.')
    print('No se ha enviado una noticia de prueba. La primera entrega real debe comprobarse en el canal.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        sys.exit(1)
