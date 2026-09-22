# snake-v2 / Snakerson

Nueva version del juego Snake en proceso.

Juego Snake portable para Windows.

## Ejecutar como aplicacion

La aplicacion compilada se encuentra en `dist/Snakerson.exe`. Copia ese archivo a otro computador Windows y ejecútalo sin instalar Python.

## Crear una nueva version

Desde PowerShell, en esta carpeta, ejecuta:

```powershell
.\build_app.ps1
```

El ejecutable actualizado aparecerá en `dist/Snakerson.exe`.

La base de datos de desempeño se guarda en la carpeta del usuario como `.snakerson_stats.db`.
