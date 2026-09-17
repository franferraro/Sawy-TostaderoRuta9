# Contrato de datos - Stage

La capa `stage` convierte los CSV originales del ERP en archivos tipados y estandarizados.

Todavia no aplica reglas fuertes de negocio. Su objetivo es dejar los datos listos para validar, cruzar y limpiar en la siguiente capa.

## Principios de stage

- No modifica el significado del dato original.
- No descarta registros.
- Conserva codigos originales.
- Estandariza nombres, tipos y formatos.
- Agrega campos tecnicos utiles, como `periodo`.
- Genera controles basicos de parseo.

## Archivos de entrada

```text
export_erp/ventas.csv
export_erp/productos.csv
export_erp/clientes.csv
export_erp/costos.csv
export_erp/gastos_operativos.csv
```

## Archivos de salida esperados

```text
data/stage/stage_ventas.csv
data/stage/stage_productos.csv
data/stage/stage_clientes.csv
data/stage/stage_costos.csv
data/stage/stage_gastos_operativos.csv
data/stage/stage_quality_checks.csv
```

## stage_ventas

Fuente: `export_erp/ventas.csv`

| Columna | Tipo | Descripcion |
| --- | --- | --- |
| fecha | date | Fecha del comprobante en formato `YYYY-MM-DD`. |
| periodo | string | Periodo analitico derivado de `fecha`, formato `YYYY-MM`. |
| comprobante | string | Numero de comprobante original. |
| tipo_comprobante | string | Tipo de comprobante: `FAC` o `NC`. |
| codigo_cliente | string | Codigo de cliente original. |
| razon_social | string | Razon social informada en ventas. |
| codigo_producto | string | Codigo de producto original informado en ventas. |
| cantidad | decimal | Cantidad informada por el ERP. Puede venir negativa en NC. |
| precio_unitario | decimal | Precio unitario informado por el ERP. |
| bonificacion_pct | decimal | Bonificacion porcentual informada por el ERP. |
| importe | decimal | Importe final informado por el ERP. Puede venir negativo en NC. |
| vendedor | string | Vendedor informado, si existe. |
| importe_recalculado | decimal | Control: `cantidad * precio_unitario * (1 - bonificacion_pct / 100)`. |
| diferencia_importe | decimal | Diferencia entre `importe` e `importe_recalculado`. |
| importe_reconciliado | boolean | `true` si la diferencia esta dentro de tolerancia. |

## stage_productos

Fuente: `export_erp/productos.csv`

| Columna | Tipo | Descripcion |
| --- | --- | --- |
| codigo | string | Codigo de producto original. |
| descripcion | string | Descripcion del producto. |
| unidad_medida | string | Unidad informada por el ERP. |
| rubro | string | Rubro del producto. |
| precio_lista_actual | decimal | Precio de lista actual. No representa necesariamente precio historico. |
| activo | string | Estado del producto: `S` o `N`. |

## stage_clientes

Fuente: `export_erp/clientes.csv`

| Columna | Tipo | Descripcion |
| --- | --- | --- |
| codigo_cliente | string | Codigo de cliente. |
| razon_social | string | Razon social del cliente. |
| condicion_comercial | string | Canal o condicion comercial. |
| bonificacion_pct | decimal | Bonificacion habitual del cliente. |
| cuit | string | CUIT informado, si existe. |
| localidad | string | Localidad informada, si existe. |

## stage_costos

Fuente: `export_erp/costos.csv`

| Columna | Tipo | Descripcion |
| --- | --- | --- |
| codigo_producto | string | Codigo de producto. |
| periodo | string | Periodo del costo en formato `YYYY-MM`. |
| costo_unitario | decimal | Costo unitario del producto para el periodo. |
| moneda | string | Moneda informada. |

## stage_gastos_operativos

Fuente: `export_erp/gastos_operativos.csv`

| Columna | Tipo | Descripcion |
| --- | --- | --- |
| periodo | string | Periodo del gasto en formato `YYYY-MM`. |
| concepto | string | Concepto de gasto. |
| importe | decimal | Importe del gasto. |
| notas | string | Nota original, si existe. |

## stage_quality_checks

Archivo de controles basicos de stage.

| Columna | Tipo | Descripcion |
| --- | --- | --- |
| check_name | string | Nombre del control. |
| status | string | `OK`, `WARNING` o `ERROR`. |
| table_name | string | Tabla afectada. |
| records_affected | integer | Cantidad de registros afectados. |
| details | string | Explicacion breve. |

## Controles minimos de stage

1. Fechas de ventas parseables.
2. Periodos de costos y gastos parseables.
3. Numericos parseables en importes, cantidades, precios, costos y bonificaciones.
4. Tipos de comprobante esperados: `FAC` y `NC`.
5. Reconciliacion de importe contra cantidad, precio y bonificacion.
6. Moneda esperada en costos.

## Que NO hace stage

- No normaliza `BLEND1K`.
- No une ventas con costos.
- No calcula margen.
- No asigna gastos.
- No genera recomendaciones.

Esas decisiones empiezan en `clean` y `reports`.
