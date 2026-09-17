# Sawy - Tostadero Ruta 9

Solucion para el caso practico de Sawy. La idea fue partir de exports simples del ERP y llegar a una herramienta que ayude a responder una pregunta concreta:

> Facturamos cada vez mas, pero en la cuenta nunca hay nada. Quiero saber si estoy ganando plata o no, y con que.

## Dashboard

Link publicado:

```text
https://franferraro.github.io/Sawy-TostaderoRuta9/
```

El dashboard publicado consume los CSV de `site/dist/data/reports/`. No necesita correr Python para visualizarse.

## Que incluye

- Pipeline reproducible en Python.
- Capas `stage`, `clean` y `reports`.
- Reglas de limpieza documentadas.
- Dashboard web que consume los reports.
- Recomendaciones accionables por canal, producto y cliente.

## Como correrlo localmente

Desde la raiz del repo:

```bash
python3 run_all.py
python3 -m http.server 8000
```

Abrir:

```text
http://localhost:8000/app_runtime/index.html
```

En macOS tambien se puede usar:

```bash
./abrir_dashboard.command
```

## Flujo de datos

```text
export_erp/
  datos originales
      |
      v
data/stage/
  datos tipados y auditables
      |
      v
data/clean/
  reglas de negocio aplicadas
      |
      v
data/reports/
  tablas listas para analisis
      |
      v
app_runtime/ y site/dist/
  visualizacion
```

## Decisiones principales

- Los archivos originales no se modifican.
- Las notas de credito se tratan como devoluciones.
- El codigo viejo `BLEND1K` se normaliza a `CAF-BLEND-1K` para calcular costo y margen, conservando el codigo original para auditoria.
- Los gastos operativos se analizan a nivel negocio porque no vienen asignados por producto o cliente.
- El margen por producto, canal y cliente es margen bruto, no resultado final.

## Archivos utiles

- `ENTREGA.md`: resumen ejecutivo de la entrega.
- `docs/limpieza_etl.md`: decisiones de limpieza y supuestos.
- `etl/`: scripts del pipeline.
- `data/reports/`: salida analitica que consume el dashboard.
- `site/dist/`: version estatica publicada por GitHub Pages.
