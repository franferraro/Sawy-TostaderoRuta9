# Entrega - Sawy Tostadero Ruta 9

## Conclusion

El negocio vende y genera margen bruto, pero en el semestre analizado el resultado operativo queda levemente negativo. El problema no parece ser solamente vender mas, sino vender mejor: revisar descuentos, flete absorbido, mix de productos y condiciones comerciales en los segmentos donde el margen queda mas ajustado.

La oportunidad principal esta en ordenar la conversacion de negocio: entender que canales, productos y clientes sostienen el margen, y cuales conviene revisar antes de seguir empujando volumen.

## Enfoque

La solucion sigue este flujo:

```text
RAW -> stage -> clean -> Reports -> app_runtime
```

La idea fue no empezar por graficos. Primero se preservan los datos originales, despues se tipan y validan, luego se aplican reglas de negocio y recien al final se construye una herramienta para decidir.

La visualizacion principal consume `data/reports/*.csv`, no los exports crudos. Eso separa la limpieza/modelado de la capa de visualizacion y deja una salida analitica reutilizable.

## Que se reutiliza y que se adapta

Si el mes que viene entra otro cliente, de otro rubro y con otro sistema de gestion, reutilizaria la forma de trabajo mas que las reglas puntuales.

Sirve tal cual:

- Separar el proceso en `raw/stage/clean/reports`.
- Preservar los archivos originales como evidencia.
- Tipar y estandarizar fechas, importes, cantidades y claves.
- Dejar controles de calidad de datos.
- Documentar supuestos y decisiones de limpieza.
- Construir una capa de `reports` que la visualizacion pueda consumir.
- Separar pipeline de datos y dashboard.

Habria que rehacer o adaptar:

- El mapeo de archivos del nuevo sistema de gestion.
- Las claves de negocio: productos, clientes, canales, comprobantes.
- Las reglas propias del rubro.
- El tratamiento de costos, devoluciones, descuentos e impuestos.
- Los umbrales de alerta.
- Las recomendaciones accionables.
- El lenguaje del dashboard para que tenga sentido para ese cliente.

En resumen: la arquitectura y el criterio de trabajo son reutilizables; las reglas de negocio no deberian copiarse sin validarlas con el cliente.

## Hallazgos principales

- El negocio vende y genera margen bruto.
- El resultado operativo del semestre queda levemente negativo.
- El problema no parece ser solo volumen, sino mix, descuentos, flete absorbido y productos/canales con margen ajustado.
- Distribuidor y Granos del Sur concentran mucho volumen, pero quedan en alerta alta por margen bruto bajo.
- La caja x6 de Blend Casa requiere revisar arquitectura de precios contra vender 6 unidades de 1 kg.
- Ecommerce y mostrador/local aparecen como canales mas sanos para empujar.

## Decisiones y supuestos

### Codigo viejo de producto

Se normaliza:

```text
BLEND1K -> CAF-BLEND-1K
```

Motivo:

- Sofia aviso que hay codigos viejos.
- `BLEND1K` aparece vendido pero esta inactivo.
- No tiene costos mensuales.
- Representa Blend Casa 1 kg.

No se excluye el producto porque eso subestimaria ventas y unidades. Se conserva el codigo original para auditoria y se usa el codigo normalizado para costo y margen.

### Notas de credito

Las notas de credito se tratan como devoluciones. En el ERP ya vienen con cantidad e importe negativos, por eso no se invierte el signo.

### Importe de venta

El importe del ERP se usa como fuente principal. Se valida contra:

```text
cantidad * precio_unitario * (1 - bonificacion_pct / 100)
```

### Gastos operativos

Los gastos se calculan a nivel negocio. No se asignan por producto o cliente porque el ERP no trae una apertura confiable.

### Margen por producto, canal y cliente

Es margen bruto. No representa rentabilidad final despues de todos los gastos.

## Recomendaciones

Las recomendaciones actuales salen de reglas de negocio codificadas sobre los reportes.

Esto es intencional: primero se prioriza trazabilidad. Con una capa de IA integrada, estas recomendaciones podrian redactarse dinamicamente o responder repreguntas, manteniendo los calculos como base confiable.

Acciones sugeridas desde el analisis:

- Revisar condiciones de Granos del Sur y del canal distribuidor.
- Revisar la arquitectura de precios del Blend Casa, especialmente caja x6 contra unidades de 1 kg.
- Empujar canales y productos con mejor margen bruto.
- Usar las alertas por cliente para priorizar conversaciones comerciales.

## Como replicarlo localmente

Desde la raiz del repo:

```bash
python3 run_all.py
python3 -m http.server 8000
```

Abrir:

```text
http://localhost:8000/app_runtime/index.html
```

El comando `run_all.py` regenera:

```text
data/stage/
data/clean/
data/reports/
site/dist/
```

No requiere instalar dependencias externas.
