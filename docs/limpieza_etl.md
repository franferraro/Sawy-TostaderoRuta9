# Definicion de limpieza y ETL

Este documento define como convertir los exports del ERP de Tostadero Ruta 9 en datos confiables para analisis.

La idea es que ninguna decision importante quede escondida en el codigo. Cada regla tiene que tener evidencia, motivo e impacto.

## Principios

1. **No modificar los archivos originales.**
   Los CSV de `export_erp/` son la evidencia cruda del ERP.

2. **Separar limpieza tecnica de reglas de negocio.**
   Parsear una fecha es una limpieza tecnica. Decidir que un codigo viejo representa a otro producto es una regla de negocio.

3. **No inventar datos sin dejarlo escrito.**
   Si falta informacion, se marca como alerta o se aplica un supuesto documentado.

4. **Priorizar trazabilidad antes que visualizacion.**
   El dashboard tiene que consumir datos ya limpiados y validados.

## Flujo propuesto

```text
raw CSV
  -> stage
  -> clean
  -> reports
  -> dashboard / preguntas
```

### Raw

Archivos originales, sin cambios:

```text
export_erp/ventas.csv
export_erp/productos.csv
export_erp/clientes.csv
export_erp/costos.csv
export_erp/gastos_operativos.csv
```

### Stage

Tablas con tipos corregidos y nombres estandarizados.

Ejemplos:

- `fecha` como fecha;
- `periodo` como `YYYY-MM`;
- `cantidad`, `precio_unitario`, `bonificacion_pct`, `importe` como numericos;
- codigos y textos sin espacios sobrantes;
- moneda normalizada.

La capa `stage` no deberia aplicar decisiones fuertes de negocio. Su funcion es dejar el dato en condiciones de ser consultado y validado.

Salidas esperadas:

```text
data/stage/stage_ventas.csv
data/stage/stage_productos.csv
data/stage/stage_clientes.csv
data/stage/stage_costos.csv
data/stage/stage_gastos_operativos.csv
```

### Clean

Tablas con reglas de negocio aplicadas:

- codigos viejos normalizados;
- notas de credito tratadas como devoluciones;
- ventas unidas a productos, clientes y costos;
- alertas de calidad generadas.

Salidas esperadas:

```text
data/clean/clean_ventas.csv
data/clean/clean_alertas_calidad.csv
```

### Reports

Tablas finales para consumir desde dashboard o preguntas:

- resultado mensual;
- margen por producto;
- margen por canal;
- margen por cliente;
- alertas de negocio;
- alertas de calidad de datos.

Salidas esperadas:

```text
data/reports/report_resultado_mensual.csv
data/reports/report_margen_por_producto.csv
data/reports/report_margen_por_canal.csv
data/reports/report_margen_por_cliente.csv
data/reports/report_alertas_negocio.csv
```

## Reglas de limpieza

### R01 - Parsear fechas y periodo

**Fuente:** `ventas.fecha`, `costos.periodo`, `gastos_operativos.periodo`.

**Regla:**

- `ventas.fecha` se parsea desde `DD/MM/YYYY`.
- El periodo analitico se calcula desde la fecha de venta.
- El formato interno recomendado es `YYYY-MM`.

**Motivo:** permite unir ventas con costos y gastos mensuales.

**Evidencia:** las ventas van del 1 de enero de 2025 al 28 de junio de 2025.

**Tipo:** automatica.

### R02 - Convertir importes y cantidades a numericos

**Fuente:** ventas, costos, gastos y maestros.

**Regla:**

- `cantidad`, `precio_unitario`, `bonificacion_pct`, `importe`, `costo_unitario`, `precio_lista_actual` e `importe` de gastos se convierten a numericos.

**Motivo:** evitar calculos sobre texto y permitir validaciones.

**Tipo:** automatica.

### R03 - Validar formula de importe

**Fuente:** `ventas.csv`.

**Regla:**

El importe de cada linea debe reconciliar contra:

```text
cantidad * precio_unitario * (1 - bonificacion_pct / 100)
```

Se acepta una tolerancia chica por redondeo.

**Evidencia:** con esta formula, todas las lineas quedan reconciliadas con diferencias menores a 0,10 ARS.

**Decision:** para ventas historicas se usa `importe` como fuente principal, y la formula queda como control de calidad.

**Motivo:** el ERP ya trae el importe final facturado. Recalcularlo podria introducir diferencias de redondeo.

**Tipo:** control.

### R04 - Tratar notas de credito como devoluciones

**Fuente:** `ventas.tipo_comprobante`.

**Regla:**

Las filas con `tipo_comprobante = NC` restan:

- ventas;
- unidades;
- costo asociado;
- margen.

**Evidencia:** hay 44 notas de credito y ya vienen con `cantidad` e `importe` negativos.

**Decision:** no invertir el signo si ya viene negativo. Se preserva el signo original y se valida que sea consistente.

**Motivo:** Sofia aclara que las notas de credito son devoluciones.

**Tipo:** regla de negocio automatica.

### R05 - Normalizar codigos viejos de producto

**Fuente:** `ventas.codigo_producto`, `productos.csv`, `costos.csv`, `LEEME.txt`.

**Regla inicial:**

```text
BLEND1K -> CAF-BLEND-1K
```

**Evidencia:**

- Sofia aviso que hay codigos viejos de producto en facturas.
- `BLEND1K` aparece en 28 lineas de venta.
- `BLEND1K` figura en maestro como inactivo.
- `BLEND1K` tiene `precio_lista_actual = 0`.
- `BLEND1K` no tiene costos mensuales.
- `CAF-BLEND-1K` representa el mismo producto: Blend Casa 1 kg.

**Impacto:** si no se normaliza, esas ventas quedan sin costo y el margen se infla artificialmente.

**Decision:** considerar esas ventas dentro del analisis, pero bajo el codigo correcto. No se descarta `BLEND1K`: se normaliza a `CAF-BLEND-1K` para calcular costo y margen de forma consistente, conservando tambien el codigo original para auditoria.

**Por que no excluirlo:** excluirlo subestimaria ventas, unidades y devoluciones del Blend Casa 1 kg. Mantenerlo sin normalizar tambien seria incorrecto, porque quedaria sin costo y mostraria una rentabilidad falsa. La opcion mas trazable es incluirlo con codigo normalizado y dejar la regla documentada.

**Campos recomendados:**

```text
codigo_producto_original
codigo_producto_normalizado
codigo_normalizado_flag
motivo_normalizacion
```

**Tipo:** regla de negocio automatica, documentada.

### R06 - Unir costos por producto normalizado y periodo

**Fuente:** `costos.csv`.

**Regla:**

El costo unitario se asigna por:

```text
codigo_producto_normalizado + periodo
```

**Motivo:** los costos cambian mes a mes.

**Decision:** si falta costo despues de normalizar, la venta no debe calcular margen como si el costo fuera cero. Debe quedar marcada como alerta.

**Tipo:** automatica con alerta.

### R07 - Preservar canal desde maestro de clientes

**Fuente:** `clientes.condicion_comercial`.

**Regla:**

El canal se toma de la condicion comercial del cliente.

Ejemplos:

- Distribuidor;
- Mayorista;
- Local;
- Ecommerce.

**Motivo:** permite analizar rentabilidad por canal sin inferirlo desde el nombre del cliente.

**Decision:** si un cliente no existe en maestro, la venta queda en canal `Sin maestro` y genera alerta.

**Evidencia:** en los datos actuales todos los clientes de ventas existen en maestro.

**Tipo:** automatica con alerta.

### R08 - No asignar gastos operativos por producto en la primera version

**Fuente:** `gastos_operativos.csv`, `LEEME.txt`.

**Regla:**

Los gastos operativos se usan para calcular resultado operativo mensual y total del negocio.

No se asignan automaticamente a producto o cliente en la primera version.

**Motivo:** Sofia aclara que los gastos no salen por producto. Asignarlos sin criterio puede dar una precision falsa.

**Decision:** el dashboard puede mostrar margen bruto por producto/canal/cliente y resultado operativo a nivel negocio.

**Posible mejora:** agregar una simulacion de asignacion por driver, por ejemplo ventas, unidades o canal. Debe mostrarse como aproximacion.

**Tipo:** decision metodologica.

### R09 - Detectar productos inactivos vendidos

**Fuente:** `productos.activo`, ventas.

**Regla:**

Si un producto con `activo = N` aparece en ventas, generar alerta.

**Evidencia:** `BLEND1K` aparece vendido estando inactivo. Esa alerta queda resuelta por la normalizacion R05.

**Tipo:** control.

### R10 - Mantener precios de lista como referencia, no como verdad historica

**Fuente:** `productos.precio_lista_actual`, `LEEME.txt`.

**Regla:**

Los precios de lista actuales no se usan para recalcular ventas historicas.

**Motivo:** Sofia aclara que los precios de lista son los de hoy, no los historicos.

**Decision:** para ventas se usa el precio unitario e importe de cada comprobante.

**Tipo:** decision metodologica.

## Alertas de calidad esperadas

El ETL deberia generar una tabla de alertas con al menos:

```text
tipo_alerta
severidad
entidad
periodo
descripcion
cantidad_registros
accion_sugerida
```

Alertas iniciales:

- codigo viejo normalizado;
- costo faltante por producto y periodo;
- producto inactivo con ventas;
- cliente sin maestro;
- producto sin maestro;
- importe no reconciliado;
- nota de credito con signo inconsistente.

## Metricas derivadas

Campos recomendados en `clean_ventas`:

```text
fecha
periodo
comprobante
tipo_comprobante
codigo_cliente
razon_social
canal
codigo_producto_original
codigo_producto
producto
cantidad
precio_unitario
bonificacion_pct
importe_neto
costo_unitario
costo_total
margen_bruto
margen_bruto_pct
es_nota_credito
codigo_normalizado_flag
```

Formulas:

```text
importe_neto = importe del ERP
costo_total = cantidad * costo_unitario
margen_bruto = importe_neto - costo_total
margen_bruto_pct = margen_bruto / importe_neto
```

Notas:

- En notas de credito, cantidad e importe ya vienen negativos.
- Si el importe neto es cero o negativo, el porcentaje de margen debe tratarse con cuidado en vistas agregadas.
- Para margenes porcentuales agregados, calcular `sum(margen_bruto) / sum(importe_neto)`, no promedio simple de porcentajes.

## Decisiones pendientes

Estas decisiones quedan definidas para la primera version:

1. **Asignacion de gastos indirectos.**
   El dashboard principal va a mostrar resultado operativo a nivel negocio. No se asignan gastos indirectos a producto o cliente como si fuera una verdad exacta.

   Se puede agregar una vista secundaria de simulacion por canal, aclarando que es una aproximacion. Si se incluye, el criterio inicial recomendado es asignar gastos por proporcion de ventas netas, porque es simple de explicar. No se usa para afirmar rentabilidad exacta por canal.

2. **Umbrales de alerta.**
   Se usaran umbrales simples y explicables:

   - margen bruto negativo: alerta critica;
   - margen bruto entre 0% y 10%: alerta alta;
   - margen bruto entre 10% y 20%: alerta media;
   - caida mensual de ventas mayor a 10%: alerta de tendencia;
   - caida mensual de margen bruto mayor a 10%: alerta de rentabilidad;
   - notas de credito mayores al 5% de ventas del periodo o segmento: alerta de devoluciones;
   - costos faltantes o productos sin maestro: alerta critica de calidad de datos.

3. **Acciones recomendadas.**
   Las acciones recomendadas salen de reglas simples, para que sean trazables y defendibles.

   Ejemplos:

   - si un canal vende mucho y tiene margen bajo, recomendar revisar descuentos, precio o flete;
   - si un producto tiene margen menor a 10%, recomendar pausar promociones o revisar precio/costo;
   - si un cliente tiene margen negativo, recomendar revisar condiciones comerciales;
   - si un canal tiene buen margen pero baja participacion, recomendar empujarlo comercialmente;
   - si hay notas de credito altas, recomendar revisar devoluciones y calidad/rotacion.

4. **Nivel de detalle para Sofia.**
   El dashboard debe estar escrito en lenguaje natural. La explicacion tecnica queda en README y documentacion del ETL.

   Para Sofia, cada insight deberia responder:

   - que esta pasando;
   - por que importa;
   - que accion concreta podria tomar esta semana.
