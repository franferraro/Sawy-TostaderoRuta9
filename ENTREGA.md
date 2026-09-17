# Entrega - Sawy Tostadero Ruta 9

## Que mirar primero

1. Abrir el dashboard publicado:

```text
https://sawy-tostadero-ruta9.joaco-ferraro2006.chatgpt.site
```

2. Para revision local en macOS, abrir con doble click:

```text
abrir_dashboard.command
```

Ese archivo regenera los datos, levanta el servidor local y abre la herramienta.

Alternativa manual desde terminal:

```bash
./abrir_dashboard.command
```

3. Si se quiere correr paso a paso, regenerar datos y herramienta:

```bash
python3 run_all.py
```

4. Levantar un servidor local:

```bash
python3 -m http.server 8000
```

5. Abrir la herramienta:

```text
http://localhost:8000/app_runtime/index.html
```

Snapshot opcional en macOS, sin servidor local:

```bash
open app/index.html
```

6. Recorrer estas pestañas:

- `Diagnostico`: estado general del negocio.
- `Acciones`: medidas recomendadas y alertas por nivel.
- `Canales y productos`: rentabilidad por canal y producto.
- `Clientes`: clientes prioritarios y otros clientes a monitorear.
- `Metodo`: pipeline, supuestos y glosario.

## Como correrlo

Desde el directorio de la entrega:

```bash
python3 run_all.py
```

Eso genera:

```text
data/stage/
data/clean/
data/reports/
app_runtime/index.html
```

No requiere instalar dependencias externas.

## Enfoque

La solucion sigue este flujo:

```text
RAW -> stage -> clean -> Reports -> app_runtime
```

La idea fue no empezar por graficos. Primero se preservan los datos originales, despues se tipan y validan, luego se aplican reglas de negocio y recien al final se construye una herramienta para que Sofia pueda decidir. La herramienta principal consume `data/reports/*.csv`, no los exports crudos.

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

## Que haria despues

- Agregar una capa de preguntas conversacionales sobre Reports.
- Llevar el pipeline a S3 + Glue/Athena.
- Agregar historico incremental para comparar semanas.
- Permitir cargar nuevos exports y regenerar la herramienta.
- Definir con el cliente drivers para asignar gastos indirectos si hace falta.
