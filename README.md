# Zebra Simple AMV 1.0.3

Impresion de etiquetas ZPL para Zebra 203 dpi por red.

- Extraer ZIP completo y ejecutar `INICIAR.bat`.
- Actualizaciones automáticas al iniciar desde GitHub Releases públicos, verificadas con SHA256.
- Si falla la conexión o no hay versiones publicadas, el programa abre igual.
- Configuración de impresoras persistente en `%LOCALAPPDATA%\ZebraSimpleAMV\impresoras.json`.
- Zebra 4 predeterminada: `192.168.98.161` para instalaciones nuevas.
- Se guarda respaldo de archivos anteriores en `respaldo_anterior`.

**Importante:** las actualizaciones automáticas solo funcionarán cuando se publique un GitHub Release con los archivos `zebra-simple-amv.zip` y `zebra-simple-amv.zip.sha256`.

Versión 1.1.1: vista previa por PDF y por página en el modo tandas.
