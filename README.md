# Sawy-TostaderoRuta9

Herramienta de visibilidad de negocio para **Tostadero Ruta 9**, construida a partir de exports del ERP.

El objetivo del caso es responder una pregunta concreta de Sofia, la dueña:

> "Facturamos cada vez mas y en la cuenta nunca hay nada. Quiero saber si estoy ganando plata o no, y con que."

La solucion busca transformar archivos operativos desordenados en informacion accionable para decidir mejor durante la semana.

## Herramienta de visibilidad

Link publicado:

```text
https://sawy-tostadero-ruta9.joaco-ferraro2006.chatgpt.site
```

Forma mas simple en macOS:

```text
doble click en abrir_dashboard.command
```

Ese archivo regenera los datos, levanta el servidor local y abre la herramienta.

Link local de la herramienta:

```text
http://localhost:8000/app_runtime/index.html
```

La herramienta recomendada consume los CSV de Reports en tiempo de ejecucion:

```text
app_runtime/index.html
data/reports/*.csv
```

Tambien queda generado `app/index.html` como snapshot embebido de respaldo.

En una primera version, la herramienta va a poder ejecutarse localmente y mostrar:

- estado general del negocio;
- ventas, costos, margen bruto y gastos operativos;
- rentabilidad por canal, producto y cliente;
- alertas de datos y de negocio;
- acciones recomendadas para la semana;
- una seccion para hacer preguntas guiadas sobre los datos.

## Enfoque

El trabajo esta pensado en cuatro momentos:

1. **Recoleccion de datos**
2. **Transformacion de datos en informacion**
3. **Analisis para entender la informacion**
4. **Visualizacion para que el cliente entienda y pueda actuar**

La idea principal es no empezar por el dashboard. Primero se preservan los datos originales, se limpian de forma trazable, se documentan supuestos y recien despues se construyen metricas de negocio.

## Datos disponibles

Los archivos originales estan en:

```text
export_erp/
  LEEME.txt
  ventas.csv
  productos.csv
  clientes.csv
  costos.csv
  gastos_operativos.csv
```

Los CSV representan 6 meses de historia, de enero a junio de 2025.

El archivo `LEEME.txt` se toma como contexto de negocio porque contiene aclaraciones importantes de Sofia:

- existen codigos viejos de producto en algunas facturas;
- las notas de credito son devoluciones;
- los gastos no vienen asignados por producto;
- el flete lo paga el negocio y no se cobra al cliente;
- los precios de lista son actuales, no historicos;
- el objetivo es entender si el negocio gana plata y con que.

## Stack propuesto

Para la entrega principal use:

```text
Python + HTML/CSS/JavaScript
```

### Por que este stack

**Python** permite construir el ETL, las validaciones y el analisis de forma simple y reproducible.

**HTML/CSS/JavaScript** permite entregar una herramienta visual liviana. La version principal consulta `data/reports/*.csv`, por eso necesita abrirse desde un servidor local o desde el link publicado.

Este stack prioriza claridad, trazabilidad y facilidad de revision. Para un challenge, evita que la evaluacion dependa de credenciales, infraestructura o paquetes externos.

## Como ejecutar

Opcion automatica en macOS:

```bash
./abrir_dashboard.command
```

O paso a paso:

Desde esta carpeta:

```bash
python3 run_all.py
```

Eso genera las capas `data/stage/`, `data/clean/`, `data/reports/` y la herramienta:

```text
app_runtime/index.html
```

Para verla desde un navegador con servidor local:

```bash
python3 -m http.server 8000
```

Luego abrir:

```text
http://localhost:8000/app_runtime/index.html
```

Si se esta parado en la raiz donde se recibio la entrega, primero entrar a la carpeta:

```bash
cd Entrega
```

Tambien se puede ejecutar paso a paso:

```bash
python3 etl/01_build_stage.py
python3 etl/02_build_clean.py
python3 etl/03_build_reports.py
python3 app/build_visibility.py
```

## Arquitectura local

```text
export_erp/
    datos crudos del ERP
        |
        v
data/stage/
    datos tipados, estandarizados y auditables
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
app/
    snapshot HTML embebido

app_runtime/
    dashboard de negocio que consulta data/reports/*.csv
```

La separacion importante es:

- **raw**: datos originales, sin modificar;
- **stage**: datos tipados y estandarizados, todavia cercanos al ERP;
- **clean**: datos con reglas de negocio aplicadas;
- **reports**: tablas agregadas listas para analisis, dashboard y preguntas.

El directorio `stage` es importante porque permite revisar el dato ya usable sin mezclarlo todavia con decisiones de negocio. Por ejemplo: fechas parseadas, importes numericos y periodos normalizados, pero sin ocultar el codigo original que vino del ERP.

## Proceso de limpieza y modelado

El ETL tiene que dejar por escrito cada decision. Algunos puntos esperados:

El contrato detallado de la primera capa esta en:

```text
docs/contrato_stage.md
```

El contrato de la capa con reglas de negocio esta en:

```text
docs/contrato_clean.md
```

El contrato de la capa de reportes esta en:

```text
docs/contrato_reports.md
```

### 1. Preservar datos originales

Los CSV originales no se editan. Son la evidencia del ERP.

### 2. Tipar datos

Convertir:

- fechas a tipo fecha;
- importes, cantidades, precios y costos a numericos;
- periodos a un formato consistente;
- porcentajes de bonificacion a numericos.

### 3. Normalizar claves

Detectar codigos viejos o inconsistentes y mapearlos explicitamente.

Ejemplo esperado:

```text
BLEND1K -> CAF-BLEND-1K
```

Esta regla no debe quedar escondida en el codigo: tiene que estar documentada junto con su motivo e impacto.

### 4. Tratar notas de credito

Las notas de credito representan devoluciones. Por eso deben restar:

- ventas;
- cantidades;
- costo asociado;
- margen.

### 5. Unir ventas con maestros y costos

Cruces principales:

- ventas con productos;
- ventas con clientes;
- ventas con costos por producto y periodo;
- ventas con gastos operativos por periodo para resultado mensual.

### 6. Validar calidad de datos

Controles esperados:

- productos vendidos que no existen en maestro;
- clientes vendidos que no existen en maestro;
- costos faltantes por producto y mes;
- productos inactivos con ventas;
- importes que no coinciden con cantidad, precio y bonificacion;
- notas de credito relevantes;
- canales o condiciones comerciales faltantes.

## Modelo analitico

Tablas o vistas esperadas:

```text
stage_ventas
stage_productos
stage_clientes
stage_costos
stage_gastos_operativos

clean_ventas

report_resultado_mensual
report_margen_por_producto
report_margen_por_cliente
report_margen_por_canal
report_alertas_negocio
```

El dashboard consume los reports, no los CSV crudos directamente.

## Preguntas que deberia responder

Para Sofia:

- Estoy ganando plata o perdiendo?
- Que productos me dejan margen?
- Que productos vendo mucho pero me dejan poco?
- Que clientes o canales deberia revisar?
- Cuanto pesan los gastos operativos?
- Que paso en los meses donde facture mas pero no vi plata?
- Que acciones concretas deberia tomar esta semana?

Para Sawy:

- Que datos vinieron bien?
- Que datos vinieron incompletos?
- Que reglas de limpieza se aplicaron?
- Que partes se podrian reutilizar con otro cliente?
- Que partes dependen del rubro o del ERP?

## Posible evolucion AWS

La entrega actual corre localmente para que pueda revisarse sin infraestructura. Como evolucion productiva, el mismo modelo puede llevarse a AWS:

```text
ERP / Excel / CSV
      |
      v
S3 raw
      |
      v
Glue Catalog / Athena external tables
      |
      v
Athena views: stage, clean, reports
      |
      v
Dashboard + capa de preguntas
```

La idea no es que Sofia tenga que entrar a AWS. AWS seria la capa tecnica para que Sawy procese datos de forma escalable y trazable.

## Capa de preguntas

Ademas del dashboard, se puede sumar una capa simple de preguntas guiadas.

Primera version:

```text
pregunta de Sofia
    |
    v
intencion conocida
    |
    v
query SQL validada
    |
    v
respuesta + tabla + explicacion
```

Ejemplos:

- "Estoy ganando plata?"
- "Que canal me conviene empujar?"
- "Que clientes deberia revisar?"
- "Que productos tienen margen bajo?"
- "Por que vendo mas pero no veo plata?"

Esto evita prometer un chatbot magico. Primero se priorizan preguntas importantes y respuestas trazables. En una version productiva, esta capa podria evolucionar a Text-to-SQL con guardrails.

## Que se reutiliza con otro cliente

Sirve tal cual:

- estructura raw -> stage -> clean -> reports;
- validaciones generales de calidad de datos;
- calculo de ventas netas, costos, margen y gastos;
- dashboard base;
- capa de preguntas guiadas;
- arquitectura S3/Athena.

Habria que adaptar:

- nombres y estructura de archivos del ERP;
- reglas de negocio del rubro;
- tratamiento de impuestos, descuentos y devoluciones;
- mapeo de productos, clientes y canales;
- criterios para asignar gastos indirectos;
- recomendaciones accionables para el negocio.

## Criterio de exito

La entrega es buena si Sofia puede entender:

1. si gana o pierde plata;
2. con que productos, canales y clientes gana o pierde;
3. que supuestos se usaron;
4. que datos son confiables y cuales requieren revision;
5. que acciones concretas deberia tomar esta semana.

Y si Sawy puede ver:

1. criterio para trabajar datos reales y desordenados;
2. trazabilidad de decisiones;
3. separacion entre pipeline, modelo analitico y visualizacion;
4. potencial para escalarlo a AWS;
5. foco en producto y negocio, no solo en graficos.
