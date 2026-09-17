# Contrato de datos - Reports

La capa `Reports` contiene tablas agregadas y listas para consumir desde la herramienta de visibilidad.

Esta capa ya no esta pensada para auditar linea por linea, sino para responder preguntas de negocio en lenguaje simple.

## Entradas

```text
data/clean/clean_ventas.csv
data/clean/clean_gastos_operativos.csv
data/clean/clean_alertas_calidad.csv
```

## Salidas

```text
data/reports/report_resultado_mensual.csv
data/reports/report_margen_por_producto.csv
data/reports/report_margen_por_canal.csv
data/reports/report_margen_por_cliente.csv
data/reports/report_alertas_negocio.csv
data/reports/report_resumen_ejecutivo.csv
```

## Metricas comunes

| Metrica | Formula |
| --- | --- |
| ventas_netas | Suma de `importe_neto`. |
| costo_total | Suma de `costo_total`. |
| margen_bruto | Suma de `margen_bruto`. |
| margen_bruto_pct | `sum(margen_bruto) / sum(ventas_netas)`. |
| unidades | Suma de `cantidad`. |
| notas_credito | Cantidad de lineas con `es_nota_credito = true`. |
| importe_notas_credito | Suma de importes de notas de credito. |

Notas:

- El porcentaje de margen se calcula siempre sobre agregados, no como promedio simple de lineas.
- Las notas de credito ya vienen negativas.
- El resultado operativo se calcula solo a nivel negocio o mensual, no por producto/cliente.

## report_resultado_mensual

Una fila por mes.

Columnas principales:

```text
periodo
ventas_netas
costo_total
margen_bruto
margen_bruto_pct
gastos_operativos
resultado_operativo
resultado_operativo_pct
ventas_mom_pct
margen_mom_pct
notas_credito
importe_notas_credito
```

## report_margen_por_producto

Una fila por producto normalizado.

Columnas principales:

```text
codigo_producto
producto
rubro
unidades
ventas_netas
costo_total
margen_bruto
margen_bruto_pct
participacion_ventas_pct
notas_credito
alerta_margen
accion_sugerida
```

## report_margen_por_canal

Una fila por condicion comercial/canal.

Columnas principales:

```text
condicion_comercial
unidades
ventas_netas
costo_total
margen_bruto
margen_bruto_pct
participacion_ventas_pct
notas_credito
alerta_margen
accion_sugerida
```

## report_margen_por_cliente

Una fila por cliente.

Columnas principales:

```text
codigo_cliente
razon_social
condicion_comercial
localidad
unidades
ventas_netas
costo_total
margen_bruto
margen_bruto_pct
participacion_ventas_pct
notas_credito
alerta_margen
accion_sugerida
```

## report_alertas_negocio

Alertas accionables para la semana.

Columnas:

```text
tipo_alerta
severidad
entidad
metrica
valor
descripcion
accion_sugerida
```

## report_resumen_ejecutivo

Tabla chica de indicadores globales.

Columnas:

```text
metrica
valor
detalle
```

## Reglas de alertas de negocio

Margen:

- margen bruto negativo: `CRITICAL`;
- margen bruto entre 0% y 10%: `HIGH`;
- margen bruto entre 10% y 20%: `MEDIUM`;
- margen mayor o igual a 20%: sin alerta de margen.

Tendencia mensual:

- caida de ventas mayor a 10% contra mes anterior: `MEDIUM`;
- caida de margen bruto mayor a 10% contra mes anterior: `HIGH`.

Notas de credito:

- si las notas de credito superan el 5% de las ventas netas del segmento: `MEDIUM`.

Acciones:

- margen bajo en producto: revisar precio, costo o promocion;
- margen bajo en canal: revisar descuento, flete o condiciones comerciales;
- margen bajo en cliente: revisar condiciones comerciales;
- buen margen y baja participacion: evaluar empujar comercialmente;
- caida mensual: revisar mix, precios, descuentos y devoluciones del periodo.
