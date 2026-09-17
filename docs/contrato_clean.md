# Contrato de datos - Clean

La capa `clean` aplica reglas de negocio sobre `stage`.

En esta etapa los datos dejan de ser solo datos tipados y pasan a ser informacion preparada para analisis de margen, calidad y acciones.

## Entradas

```text
data/stage/stage_ventas.csv
data/stage/stage_productos.csv
data/stage/stage_clientes.csv
data/stage/stage_costos.csv
data/stage/stage_gastos_operativos.csv
```

## Salidas

```text
data/clean/clean_ventas.csv
data/clean/clean_gastos_operativos.csv
data/clean/clean_alertas_calidad.csv
```

## clean_ventas

Tabla principal a nivel linea de comprobante.

| Columna | Descripcion |
| --- | --- |
| fecha | Fecha del comprobante. |
| periodo | Periodo analitico `YYYY-MM`. |
| comprobante | Numero de comprobante. |
| tipo_comprobante | `FAC` o `NC`. |
| es_nota_credito | Indica si es devolucion. |
| codigo_cliente | Codigo de cliente. |
| razon_social | Razon social de la venta. |
| condicion_comercial | Canal/condicion comercial desde maestro de clientes. |
| localidad | Localidad del cliente. |
| codigo_producto_original | Codigo de producto como vino en ventas. |
| codigo_producto | Codigo normalizado para analisis. |
| codigo_normalizado | `true` si se aplico una normalizacion. |
| motivo_normalizacion | Motivo de la normalizacion. |
| producto | Descripcion del producto normalizado. |
| unidad_medida | Unidad de medida del maestro. |
| rubro | Rubro del producto. |
| producto_activo | Estado del producto normalizado. |
| cantidad | Cantidad de la linea. En NC viene negativa. |
| precio_unitario | Precio unitario informado por ERP. |
| bonificacion_pct | Bonificacion de la linea. |
| importe_neto | Importe final del ERP. En NC viene negativo. |
| costo_unitario | Costo unitario por producto y periodo. |
| costo_total | `cantidad * costo_unitario`. |
| margen_bruto | `importe_neto - costo_total`. |
| margen_bruto_pct | `margen_bruto / importe_neto`, cuando aplica. |
| vendedor | Vendedor informado. |

## clean_alertas_calidad

Alertas generadas por reglas de negocio y calidad.

| Columna | Descripcion |
| --- | --- |
| tipo_alerta | Categoria de alerta. |
| severidad | `INFO`, `WARNING` o `CRITICAL`. |
| entidad | Producto, cliente, comprobante u otra entidad. |
| periodo | Periodo asociado, si aplica. |
| descripcion | Explicacion en lenguaje natural. |
| cantidad_registros | Cantidad de registros afectados. |
| accion_sugerida | Proxima accion recomendada. |

## Reglas aplicadas

1. Normalizar `BLEND1K -> CAF-BLEND-1K`.
2. Preservar codigo original para auditoria.
3. Unir ventas con productos por codigo normalizado.
4. Unir ventas con clientes por codigo de cliente.
5. Unir ventas con costos por producto normalizado y periodo.
6. Calcular costo total, margen bruto y margen bruto porcentual.
7. Generar alertas si falta producto, cliente o costo.
8. Generar alerta informativa por codigos normalizados.
9. No asignar gastos indirectos a producto o cliente.
