from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parents[1]
STAGE_DIR = CASE_DIR / "data" / "stage"
CLEAN_DIR = CASE_DIR / "data" / "clean"

PRODUCT_CODE_MAP = {
    "BLEND1K": {
        "codigo_producto": "CAF-BLEND-1K",
        "motivo": "Codigo viejo informado en ventas; corresponde a Blend Casa 1 kg.",
    }
}


@dataclass
class Alert:
    tipo_alerta: str
    severidad: str
    entidad: str
    periodo: str
    descripcion: str
    cantidad_registros: int
    accion_sugerida: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def decimal_value(value: str | None) -> Decimal:
    try:
        return Decimal((value or "0").strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


def fmt_decimal(value: Decimal, places: str = "0.01") -> str:
    return format(value.quantize(Decimal(places), rounding=ROUND_HALF_UP), "f")


def fmt_pct(value: Decimal | None) -> str:
    if value is None:
        return ""
    return fmt_decimal(value)


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def normalize_product_code(code: str) -> tuple[str, bool, str]:
    rule = PRODUCT_CODE_MAP.get(code)
    if rule is None:
        return code, False, ""
    return rule["codigo_producto"], True, rule["motivo"]


def build_clean_ventas(alerts: list[Alert]) -> None:
    ventas = read_csv(STAGE_DIR / "stage_ventas.csv")
    productos = {r["codigo"]: r for r in read_csv(STAGE_DIR / "stage_productos.csv")}
    clientes = {r["codigo_cliente"]: r for r in read_csv(STAGE_DIR / "stage_clientes.csv")}
    costos = {
        (r["codigo_producto"], r["periodo"]): r
        for r in read_csv(STAGE_DIR / "stage_costos.csv")
    }

    output: list[dict[str, object]] = []
    normalized_counter: Counter[str] = Counter()
    missing_product_counter: Counter[str] = Counter()
    missing_client_counter: Counter[str] = Counter()
    missing_cost_counter: Counter[tuple[str, str]] = Counter()

    for row in ventas:
        original_code = row["codigo_producto"]
        product_code, was_normalized, normalization_reason = normalize_product_code(original_code)
        if was_normalized:
            normalized_counter[f"{original_code} -> {product_code}"] += 1

        product = productos.get(product_code)
        client = clientes.get(row["codigo_cliente"])
        cost = costos.get((product_code, row["periodo"]))

        if product is None:
            missing_product_counter[product_code] += 1
        if client is None:
            missing_client_counter[row["codigo_cliente"]] += 1
        if cost is None:
            missing_cost_counter[(product_code, row["periodo"])] += 1

        cantidad = decimal_value(row["cantidad"])
        importe_neto = decimal_value(row["importe"])
        costo_unitario = decimal_value(cost["costo_unitario"]) if cost else Decimal("0")
        costo_total = cantidad * costo_unitario
        margen_bruto = importe_neto - costo_total
        margen_bruto_pct = None
        if importe_neto > 0:
            margen_bruto_pct = margen_bruto / importe_neto

        output.append(
            {
                "fecha": row["fecha"],
                "periodo": row["periodo"],
                "comprobante": row["comprobante"],
                "tipo_comprobante": row["tipo_comprobante"],
                "es_nota_credito": bool_text(row["tipo_comprobante"] == "NC"),
                "codigo_cliente": row["codigo_cliente"],
                "razon_social": row["razon_social"],
                "condicion_comercial": client["condicion_comercial"] if client else "Sin maestro",
                "localidad": client["localidad"] if client else "",
                "codigo_producto_original": original_code,
                "codigo_producto": product_code,
                "codigo_normalizado": bool_text(was_normalized),
                "motivo_normalizacion": normalization_reason,
                "producto": product["descripcion"] if product else "Producto sin maestro",
                "unidad_medida": product["unidad_medida"] if product else "",
                "rubro": product["rubro"] if product else "",
                "producto_activo": product["activo"] if product else "",
                "cantidad": fmt_decimal(cantidad),
                "precio_unitario": row["precio_unitario"],
                "bonificacion_pct": row["bonificacion_pct"],
                "importe_neto": fmt_decimal(importe_neto),
                "costo_unitario": fmt_decimal(costo_unitario),
                "costo_total": fmt_decimal(costo_total),
                "margen_bruto": fmt_decimal(margen_bruto),
                "margen_bruto_pct": fmt_pct(margen_bruto_pct),
                "vendedor": row["vendedor"],
            }
        )

    fieldnames = [
        "fecha",
        "periodo",
        "comprobante",
        "tipo_comprobante",
        "es_nota_credito",
        "codigo_cliente",
        "razon_social",
        "condicion_comercial",
        "localidad",
        "codigo_producto_original",
        "codigo_producto",
        "codigo_normalizado",
        "motivo_normalizacion",
        "producto",
        "unidad_medida",
        "rubro",
        "producto_activo",
        "cantidad",
        "precio_unitario",
        "bonificacion_pct",
        "importe_neto",
        "costo_unitario",
        "costo_total",
        "margen_bruto",
        "margen_bruto_pct",
        "vendedor",
    ]
    write_csv(CLEAN_DIR / "clean_ventas.csv", output, fieldnames)

    for entity, count in normalized_counter.items():
        alerts.append(
            Alert(
                "codigo_producto_normalizado",
                "INFO",
                entity,
                "",
                f"Se normalizaron {count} lineas de venta con codigo viejo.",
                count,
                "Conservar codigo original para auditoria y usar codigo normalizado para margen.",
            )
        )

    for product_code, count in missing_product_counter.items():
        alerts.append(
            Alert(
                "producto_sin_maestro",
                "CRITICAL",
                product_code,
                "",
                "Hay ventas con un producto que no existe en el maestro normalizado.",
                count,
                "Corregir maestro o mapear codigo antes de analizar margen.",
            )
        )

    for client_code, count in missing_client_counter.items():
        alerts.append(
            Alert(
                "cliente_sin_maestro",
                "CRITICAL",
                client_code,
                "",
                "Hay ventas con un cliente que no existe en el maestro.",
                count,
                "Corregir maestro de clientes antes de analizar canales.",
            )
        )

    for (product_code, period), count in missing_cost_counter.items():
        alerts.append(
            Alert(
                "costo_faltante",
                "CRITICAL",
                product_code,
                period,
                "Hay ventas sin costo unitario para producto y periodo.",
                count,
                "Completar costo antes de usar margen bruto.",
            )
        )


def build_clean_gastos() -> None:
    gastos = read_csv(STAGE_DIR / "stage_gastos_operativos.csv")
    write_csv(
        CLEAN_DIR / "clean_gastos_operativos.csv",
        gastos,
        ["periodo", "concepto", "importe", "notas"],
    )


def write_alerts(alerts: list[Alert]) -> None:
    rows = [
        {
            "tipo_alerta": alert.tipo_alerta,
            "severidad": alert.severidad,
            "entidad": alert.entidad,
            "periodo": alert.periodo,
            "descripcion": alert.descripcion,
            "cantidad_registros": alert.cantidad_registros,
            "accion_sugerida": alert.accion_sugerida,
        }
        for alert in alerts
    ]
    write_csv(
        CLEAN_DIR / "clean_alertas_calidad.csv",
        rows,
        [
            "tipo_alerta",
            "severidad",
            "entidad",
            "periodo",
            "descripcion",
            "cantidad_registros",
            "accion_sugerida",
        ],
    )


def main() -> None:
    alerts: list[Alert] = []
    build_clean_ventas(alerts)
    build_clean_gastos()
    write_alerts(alerts)

    print("Clean generado en:", CLEAN_DIR)
    if alerts:
        for alert in alerts:
            print(f"[{alert.severidad}] {alert.tipo_alerta} {alert.entidad} {alert.periodo}: {alert.cantidad_registros}")
    else:
        print("Sin alertas de calidad.")


if __name__ == "__main__":
    main()
