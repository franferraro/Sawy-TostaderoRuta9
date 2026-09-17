from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = CASE_DIR / "export_erp"
STAGE_DIR = CASE_DIR / "data" / "stage"

MONEY_TOLERANCE = Decimal("0.10")


@dataclass
class QualityCheck:
    check_name: str
    status: str
    table_name: str
    records_affected: int
    details: str


def read_csv(name: str) -> list[dict[str, str]]:
    with (RAW_DIR / name).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def write_csv(name: str, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    with (STAGE_DIR / name).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clean_text(value: str | None) -> str:
    return (value or "").strip()


def parse_decimal(value: str, context: str, errors: list[str]) -> Decimal:
    raw = clean_text(value)
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        errors.append(f"{context}: valor numerico invalido '{raw}'")
        return Decimal("0")


def parse_date(value: str, context: str, errors: list[str]) -> datetime:
    raw = clean_text(value)
    try:
        return datetime.strptime(raw, "%d/%m/%Y")
    except ValueError:
        errors.append(f"{context}: fecha invalida '{raw}'")
        return datetime(1900, 1, 1)


def parse_period(value: str, context: str, errors: list[str]) -> str:
    raw = clean_text(value)
    try:
        return datetime.strptime(raw, "%m/%Y").strftime("%Y-%m")
    except ValueError:
        errors.append(f"{context}: periodo invalido '{raw}'")
        return "1900-01"


def fmt_decimal(value: Decimal) -> str:
    normalized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(normalized, "f")


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def status_from_count(count: int, warning: bool = True) -> str:
    if count == 0:
        return "OK"
    return "WARNING" if warning else "ERROR"


def build_stage_ventas(checks: list[QualityCheck]) -> None:
    rows = read_csv("ventas.csv")
    output: list[dict[str, object]] = []
    errors: list[str] = []
    invalid_types = 0
    unreconciled = 0
    expected_types = {"FAC", "NC"}

    for idx, row in enumerate(rows, start=2):
        context = f"ventas.csv linea {idx}"
        fecha = parse_date(row["fecha"], context, errors)
        cantidad = parse_decimal(row["cantidad"], context, errors)
        precio_unitario = parse_decimal(row["precio_unitario"], context, errors)
        bonificacion_pct = parse_decimal(row["bonificacion_pct"], context, errors)
        importe = parse_decimal(row["importe"], context, errors)
        tipo_comprobante = clean_text(row["tipo_comprobante"]).upper()

        if tipo_comprobante not in expected_types:
            invalid_types += 1

        importe_recalculado = cantidad * precio_unitario * (Decimal("1") - bonificacion_pct / Decimal("100"))
        diferencia_importe = importe - importe_recalculado
        importe_reconciliado = abs(diferencia_importe) <= MONEY_TOLERANCE
        if not importe_reconciliado:
            unreconciled += 1

        output.append(
            {
                "fecha": fecha.strftime("%Y-%m-%d"),
                "periodo": fecha.strftime("%Y-%m"),
                "comprobante": clean_text(row["comprobante"]),
                "tipo_comprobante": tipo_comprobante,
                "codigo_cliente": clean_text(row["codigo_cliente"]),
                "razon_social": clean_text(row["razon_social"]),
                "codigo_producto": clean_text(row["codigo_producto"]),
                "cantidad": fmt_decimal(cantidad),
                "precio_unitario": fmt_decimal(precio_unitario),
                "bonificacion_pct": fmt_decimal(bonificacion_pct),
                "importe": fmt_decimal(importe),
                "vendedor": clean_text(row["vendedor"]),
                "importe_recalculado": fmt_decimal(importe_recalculado),
                "diferencia_importe": fmt_decimal(diferencia_importe),
                "importe_reconciliado": bool_text(importe_reconciliado),
            }
        )

    fieldnames = [
        "fecha",
        "periodo",
        "comprobante",
        "tipo_comprobante",
        "codigo_cliente",
        "razon_social",
        "codigo_producto",
        "cantidad",
        "precio_unitario",
        "bonificacion_pct",
        "importe",
        "vendedor",
        "importe_recalculado",
        "diferencia_importe",
        "importe_reconciliado",
    ]
    write_csv("stage_ventas.csv", output, fieldnames)

    checks.extend(
        [
            QualityCheck("parse_ventas", status_from_count(len(errors), warning=False), "stage_ventas", len(errors), "; ".join(errors[:5]) or "Fechas y numericos parseados correctamente."),
            QualityCheck("tipo_comprobante_valido", status_from_count(invalid_types, warning=False), "stage_ventas", invalid_types, "Solo se esperan FAC y NC."),
            QualityCheck("importe_reconciliado", status_from_count(unreconciled), "stage_ventas", unreconciled, f"Tolerancia usada: {MONEY_TOLERANCE} ARS."),
        ]
    )


def build_stage_productos(checks: list[QualityCheck]) -> None:
    rows = read_csv("productos.csv")
    output: list[dict[str, object]] = []
    errors: list[str] = []
    invalid_active = 0

    for idx, row in enumerate(rows, start=2):
        context = f"productos.csv linea {idx}"
        activo = clean_text(row["activo"]).upper()
        if activo not in {"S", "N"}:
            invalid_active += 1
        output.append(
            {
                "codigo": clean_text(row["codigo"]),
                "descripcion": clean_text(row["descripcion"]),
                "unidad_medida": clean_text(row["unidad_medida"]),
                "rubro": clean_text(row["rubro"]),
                "precio_lista_actual": fmt_decimal(parse_decimal(row["precio_lista_actual"], context, errors)),
                "activo": activo,
            }
        )

    write_csv(
        "stage_productos.csv",
        output,
        ["codigo", "descripcion", "unidad_medida", "rubro", "precio_lista_actual", "activo"],
    )
    checks.extend(
        [
            QualityCheck("parse_productos", status_from_count(len(errors), warning=False), "stage_productos", len(errors), "; ".join(errors[:5]) or "Numericos parseados correctamente."),
            QualityCheck("activo_valido", status_from_count(invalid_active, warning=False), "stage_productos", invalid_active, "Solo se esperan S o N."),
        ]
    )


def build_stage_clientes(checks: list[QualityCheck]) -> None:
    rows = read_csv("clientes.csv")
    output: list[dict[str, object]] = []
    errors: list[str] = []

    for idx, row in enumerate(rows, start=2):
        context = f"clientes.csv linea {idx}"
        output.append(
            {
                "codigo_cliente": clean_text(row["codigo_cliente"]),
                "razon_social": clean_text(row["razon_social"]),
                "condicion_comercial": clean_text(row["condicion_comercial"]),
                "bonificacion_pct": fmt_decimal(parse_decimal(row["bonificacion_pct"], context, errors)),
                "cuit": clean_text(row["cuit"]),
                "localidad": clean_text(row["localidad"]),
            }
        )

    write_csv(
        "stage_clientes.csv",
        output,
        ["codigo_cliente", "razon_social", "condicion_comercial", "bonificacion_pct", "cuit", "localidad"],
    )
    checks.append(
        QualityCheck("parse_clientes", status_from_count(len(errors), warning=False), "stage_clientes", len(errors), "; ".join(errors[:5]) or "Numericos parseados correctamente.")
    )


def build_stage_costos(checks: list[QualityCheck]) -> None:
    rows = read_csv("costos.csv")
    output: list[dict[str, object]] = []
    errors: list[str] = []
    invalid_currency = 0

    for idx, row in enumerate(rows, start=2):
        context = f"costos.csv linea {idx}"
        moneda = clean_text(row["moneda"]).upper()
        if moneda != "ARS":
            invalid_currency += 1
        output.append(
            {
                "codigo_producto": clean_text(row["codigo_producto"]),
                "periodo": parse_period(row["periodo"], context, errors),
                "costo_unitario": fmt_decimal(parse_decimal(row["costo_unitario"], context, errors)),
                "moneda": moneda,
            }
        )

    write_csv("stage_costos.csv", output, ["codigo_producto", "periodo", "costo_unitario", "moneda"])
    checks.extend(
        [
            QualityCheck("parse_costos", status_from_count(len(errors), warning=False), "stage_costos", len(errors), "; ".join(errors[:5]) or "Periodos y numericos parseados correctamente."),
            QualityCheck("moneda_costos", status_from_count(invalid_currency, warning=False), "stage_costos", invalid_currency, "Se espera ARS."),
        ]
    )


def build_stage_gastos(checks: list[QualityCheck]) -> None:
    rows = read_csv("gastos_operativos.csv")
    output: list[dict[str, object]] = []
    errors: list[str] = []

    for idx, row in enumerate(rows, start=2):
        context = f"gastos_operativos.csv linea {idx}"
        output.append(
            {
                "periodo": parse_period(row["periodo"], context, errors),
                "concepto": clean_text(row["concepto"]),
                "importe": fmt_decimal(parse_decimal(row["importe"], context, errors)),
                "notas": clean_text(row["notas"]),
            }
        )

    write_csv("stage_gastos_operativos.csv", output, ["periodo", "concepto", "importe", "notas"])
    checks.append(
        QualityCheck("parse_gastos_operativos", status_from_count(len(errors), warning=False), "stage_gastos_operativos", len(errors), "; ".join(errors[:5]) or "Periodos y numericos parseados correctamente.")
    )


def write_quality_checks(checks: list[QualityCheck]) -> None:
    rows = [
        {
            "check_name": c.check_name,
            "status": c.status,
            "table_name": c.table_name,
            "records_affected": c.records_affected,
            "details": c.details,
        }
        for c in checks
    ]
    write_csv(
        "stage_quality_checks.csv",
        rows,
        ["check_name", "status", "table_name", "records_affected", "details"],
    )


def main() -> None:
    checks: list[QualityCheck] = []
    build_stage_ventas(checks)
    build_stage_productos(checks)
    build_stage_clientes(checks)
    build_stage_costos(checks)
    build_stage_gastos(checks)
    write_quality_checks(checks)

    print("Stage generado en:", STAGE_DIR)
    for check in checks:
        print(f"[{check.status}] {check.check_name}: {check.records_affected}")


if __name__ == "__main__":
    main()
