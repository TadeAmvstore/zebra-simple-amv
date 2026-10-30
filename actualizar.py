"""Zebra Simple AMV updater. Called before app startup; public GitHub Releases."""
import hashlib, json, os, shutil, sys, tempfile, urllib.request, zipfile
from pathlib import Path
from urllib.error import HTTPError
BASE=Path(__file__).resolve().parent
REPO='TadeAmvstore/zebra-simple-amv'
API=f'https://api.github.com/repos/{REPO}/releases/latest'
HEADERS={'User-Agent':'ZebraSimpleAMV/1.0.3','Accept':'application/vnd.github+json'}
PROTECTED={'impresoras.json','servidor.json'}
ALLOWED={'app.py','index.html','amv_logo.png','VERSION','actualizar.py','INICIAR.bat','ACTUALIZAR.bat','README.md','LEEME.txt'}

def get(url):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=15) as r:return r.read()

def ver(s):
    try:return tuple(int(v) for v in s.lstrip('v').split('.'))
    except (ValueError,AttributeError):return (0,)

def main():
    current=(BASE/'VERSION').read_text(encoding='utf-8').strip()
    print('Zebra Simple AMV - buscando actualizaciones...',flush=True)
    try:
        rel=json.loads(get(API))
    except HTTPError as e:
        if e.code==404: print('Todavia no hay versiones publicadas. Abriendo version instalada.');return 0
        print('GitHub no disponible:',e);return 0
    except Exception as e:
        print('Sin conexion para actualizar:',e);return 0
    target=rel.get('tag_name','').lstrip('v')
    if ver(target)<=ver(current):print('Version actual:',current);return 0
    assets={a['name']:a['browser_download_url'] for a in rel.get('assets',[])}
    if not {'zebra-simple-amv.zip','zebra-simple-amv.zip.sha256'}<=assets.keys():
        print('La nueva version no tiene los archivos de actualizacion requeridos.');return 0
    print('Descargando version',target,flush=True)
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        payload=get(assets['zebra-simple-amv.zip'])
        expected=get(assets['zebra-simple-amv.zip.sha256']).decode().split()[0].lower()
        if hashlib.sha256(payload).hexdigest()!=expected:raise ValueError('Checksum invalido')
        zp=td/'update.zip';zp.write_bytes(payload)
        staged=td/'staged';staged.mkdir()
        with zipfile.ZipFile(zp) as z:
            for item in z.infolist():
                if item.is_dir():continue
                parts=Path(item.filename).parts
                if not parts or '..' in parts or len(parts)>2:raise ValueError('Ruta ZIP insegura')
                name=parts[-1]
                if name in PROTECTED:continue
                if name not in ALLOWED:raise ValueError('Archivo inesperado en version: '+name)
                (staged/name).write_bytes(z.read(item))
        if not {'app.py','index.html','VERSION','actualizar.py'} <= {p.name for p in staged.iterdir()}:
            raise ValueError('Version incompleta')
        if (staged/'VERSION').read_text(encoding='utf-8').strip()!=target:
            raise ValueError('Version no coincide con release')
        backup=BASE/'respaldo_anterior'
        backup.mkdir(exist_ok=True)
        # Back up before any change; never touch saved printer settings in LOCALAPPDATA.
        for src in staged.iterdir():
            dest=BASE/src.name
            if dest.exists():shutil.copy2(dest,backup/src.name)
        updated=[]
        try:
            for src in staged.iterdir():
                dest=BASE/src.name
                temp=BASE/(src.name+'.nueva')
                shutil.copy2(src,temp)
                os.replace(temp,dest)
                updated.append(src.name)
        except Exception:
            for name in updated:
                prev=backup/name
                if prev.exists():shutil.copy2(prev,BASE/name)
            raise
        print('Actualizado a',target)
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:
        print('No se pudo actualizar. Se intentara abrir la version instalada:',e)
        sys.exit(0)
