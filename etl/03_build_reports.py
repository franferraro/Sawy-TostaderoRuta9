from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = CASE_DIR / "data" / "clean"
REPORTS_DIR = CASE_DIR / "data" / "reports"


@dataclass
class Alert:
    tipo_alerta: str
    severidad: str
    entidad: str
    metrica: str
    valor: str
    descripcion: str
    accion_sugerida: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
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
    return fmt_decimal(value, "0.0001")


def safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return numerator / denominator


def margin_level(margin_pct: Decimal | None) -> str:
    if margin_pct is None:
        return "SIN_DATOS"
    if margin_pct < 0:
        return "CRITICAL"
    if margin_pct < Decimal("0.10"):
        return "HIGH"
    if margin_pct < Decimal("0.20"):
        return "MEDIUM"
    return ""


def margin_action(
    entity_type: str,
    level: str,
    context: dict[str, str] | None = None,
    metrics: dict[str, Decimal | int] | None = None,
) -> str:
    if not level:
        return ""
    context = context or {}
    if entity_type == "producto":
        if level in {"CRITICAL", "HIGH"}:
            return "Frenar promociones y revisar precio/costo antes de vender mas volumen."
        return "Monitorear precio y descuento; no empujarlo sin revisar margen."
    if entity_type == "canal":
        channel = context.get("condicion_comercial", "")
        if channel == "Distribuidor":
            return "Renegociar descuento, precio minimo y flete absorbido del canal."
        if channel == "Mayorista":
            return "Revisar escala de descuentos y condiciones por volumen."
        return "Revisar condiciones comerciales del canal."
    if entity_type == "cliente":
        channel = context.get("condicion_comercial", "")
        sales = metrics["ventas_netas"] if metrics else Decimal("0")
        credit_notes = metrics["notas_credito"] if metrics else 0
        if channel == "Distribuidor":
            return "Agendar renegociacion: revisar descuento, volumen minimo, lista de precios y flete absorbido."
        if credit_notes:
            return "Revisar devoluciones y rotacion antes de renovar condiciones comerciales."
        if sales >= Decimal("1000000"):
            return "Preparar propuesta con menor descuento o mix de productos de mayor margen."
        if level in {"CRITICAL", "HIGH"}:
            return "Llamar esta semana y revisar descuentos o mix de productos comprados."
        if channel == "Mayorista":
            return "En la proxima reposicion, ofrecer alternativas de mayor margen antes de repetir descuento."
        return "Monitorear margen antes de ofrecer promociones."
    return "Revisar rentabilidad antes de aumentar volumen."


def empty_metrics() -> dict[str, Decimal | int]:
    return {
        "ventas_netas": Decimal("0"),
        "costo_total": Decimal("0"),
        "margen_bruto": Decimal("0"),
        "unidades": Decimal("0"),
        "notas_credito": 0,
        "importe_notas_credito": Decimal("0"),
    }


def add_metrics(bucket: dict[str, Decimal | int], row: dict[str, str]) -> None:
    bucket["ventas_netas"] += decimal_value(row["importe_neto"])
    bucket["costo_total"] += decimal_value(row["costo_total"])
    bucket["margen_bruto"] += decimal_value(row["margen_bruto"])
    bucket["unidades"] += decimal_value(row["cantidad"])
    if row["es_nota_credito"] == "true":
        bucket["notas_credito"] += 1
        bucket["importe_notas_credito"] += decimal_value(row["importe_neto"])


def metrics_to_row(metrics: dict[str, Decimal | int], total_sales: Decimal) -> dict[str, str]:
    ventas = metrics["ventas_netas"]
    margen = metrics["margen_bruto"]
    unidades = metrics["unidades"]
    return {
        "unidades": fmt_decimal(unidades),
        "ventas_netas": fmt_decimal(ventas),
        "costo_total": fmt_decimal(metrics["costo_total"]),
        "margen_bruto": fmt_decimal(margen),
        "margen_bruto_pct": fmt_pct(safe_ratio(margen, ventas)),
        "precio_venta_promedio": fmt_decimal(ventas / unidades) if unidades else "",
        "costo_unitario_promedio": fmt_decimal(metrics["costo_total"] / unidades) if unidades else "",
        "participacion_ventas_pct": fmt_pct(safe_ratio(ventas, total_sales)),
        "notas_credito": str(metrics["notas_credito"]),
        "importe_notas_credito": fmt_decimal(metrics["importe_notas_credito"]),
    }


def build_monthly_report(ventas: list[dict[str, str]], gastos: list[dict[str, str]], alerts: list[Alert]) -> None:
    by_month: defaultdict[str, dict[str, Decimal | int]] = defaultdict(empty_metrics)
    gastos_by_month: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for row in ventas:
        add_metrics(by_month[row["periodo"]], row)
    for row in gastos:
        gastos_by_month[row["periodo"]] += decimal_value(row["importe"])

    rows: list[dict[str, object]] = []
    previous_sales: Decimal | None = None
    previous_margin: Decimal | None = None

    for period in sorted(by_month):
        metrics = by_month[period]
        ventas_netas = metrics["ventas_netas"]
        margen = metrics["margen_bruto"]
        gastos_operativos = gastos_by_month[period]
        resultado_operativo = margen - gastos_operativos
        ventas_mom = None if previous_sales in (None, Decimal("0")) else (ventas_netas / previous_sales) - Decimal("1")
        margen_mom = None if previous_margin in (None, Decimal("0")) else (margen / previous_margin) - Decimal("1")

        if ventas_mom is not None and ventas_mom < Decimal("-0.10"):
            alerts.append(
                Alert(
                    "caida_ventas_mensual",
                    "MEDIUM",
                    period,
                    "ventas_mom_pct",
                    fmt_pct(ventas_mom),
                    "Las ventas netas cayeron mas de 10% contra el mes anterior.",
                    "Revisar mix de productos, descuentos y clientes que redujeron compra.",
                )
            )
        if margen_mom is not None and margen_mom < Decimal("-0.10"):
            alerts.append(
                Alert(
                    "caida_margen_mensual",
                    "HIGH",
                    period,
                    "margen_mom_pct",
                    fmt_pct(margen_mom),
                    "El margen bruto cayo mas de 10% contra el mes anterior.",
                    "Revisar productos/canales con margen bajo y devoluciones del periodo.",
                )
            )

        rows.append(
            {
                "periodo": period,
                "ventas_netas": fmt_decimal(ventas_netas),
                "costo_total": fmt_decimal(metrics["costo_total"]),
                "margen_bruto": fmt_decimal(margen),
                "margen_bruto_pct": fmt_pct(safe_ratio(margen, ventas_netas)),
                "gastos_operativos": fmt_decimal(gastos_operativos),
                "resultado_operativo": fmt_decimal(resultado_operativo),
                "resultado_operativo_pct": fmt_pct(safe_ratio(resultado_operativo, ventas_netas)),
                "ventas_mom_pct": fmt_pct(ventas_mom),
                "margen_mom_pct": fmt_pct(margen_mom),
                "notas_credito": str(metrics["notas_credito"]),
                "importe_notas_credito": fmt_decimal(metrics["importe_notas_credito"]),
            }
        )
        previous_sales = ventas_netas
        previous_margin = margen

    write_csv(
        REPORTS_DIR / "report_resultado_mensual.csv",
        rows,
        [
            "periodo",
            "ventas_netas",
            "costo_total",
            "margen_bruto",
            "margen_bruto_pct",
            "gastos_operativos",
            "resultado_operativo",
            "resultado_operativo_pct",
            "ventas_mom_pct",
            "margen_mom_pct",
            "notas_credito",
            "importe_notas_credito",
        ],
    )


def build_dimension_report(
    ventas: list[dict[str, str]],
    group_fields: list[str],
    output_name: str,
    entity_type: str,
    alerts: list[Alert],
) -> None:
    total_sales = sum(decimal_value(row["importe_neto"]) for row in ventas)
    grouped: defaultdict[tuple[str, ...], dict[str, Decimal | int]] = defaultdict(empty_metrics)

    for row in ventas:
        key = tuple(row[field] for field in group_fields)
        add_metrics(grouped[key], row)

    output_rows: list[dict[str, object]] = []
    for key, metrics in grouped.items():
        base = dict(zip(group_fields, key))
        metric_row = metrics_to_row(metrics, total_sales)
        margin_pct = safe_ratio(metrics["margen_bruto"], metrics["ventas_netas"])
        level = margin_level(margin_pct)
        action = margin_action(entity_type, level, base, metrics)
        metric_row["alerta_margen"] = level
        metric_row["accion_sugerida"] = action
        output_rows.append({**base, **metric_row})

        if level:
            alerts.append(
                Alert(
                    f"margen_bajo_{entity_type}",
                    level,
                    " - ".join(key),
                    "margen_bruto_pct",
                    fmt_pct(margin_pct),
                    f"{entity_type.capitalize()} con margen bruto bajo.",
                    action,
                )
            )

        credit_note_ratio = None
        if metrics["ventas_netas"] > 0:
            credit_note_ratio = abs(metrics["importe_notas_credito"]) / metrics["ventas_netas"]
        if credit_note_ratio is not None and credit_note_ratio > Decimal("0.05"):
            alerts.append(
                Alert(
                    f"notas_credito_altas_{entity_type}",
                    "MEDIUM",
                    " - ".join(key),
                    "notas_credito_pct",
                    fmt_pct(credit_note_ratio),
                    f"{entity_type.capitalize()} con devoluciones mayores al 5% de ventas netas.",
                    "Revisar devoluciones, rotacion de producto y acuerdos comerciales.",
                )
            )

    output_rows.sort(key=lambda r: decimal_value(r["margen_bruto"]), reverse=True)
    fieldnames = group_fields + [
        "unidades",
        "ventas_netas",
        "costo_total",
        "margen_bruto",
        "margen_bruto_pct",
        "precio_venta_promedio",
        "costo_unitario_promedio",
        "participacion_ventas_pct",
        "notas_credito",
        "importe_notas_credito",
        "alerta_margen",
        "accion_sugerida",
    ]
    write_csv(REPORTS_DIR / output_name, output_rows, fieldnames)


def build_alerts_report(alerts: list[Alert]) -> None:
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}
    rows = [
        {
            "tipo_alerta": alert.tipo_alerta,
            "severidad": alert.severidad,
            "entidad": alert.entidad,
            "metrica": alert.metrica,
            "valor": alert.valor,
            "descripcion": alert.descripcion,
            "accion_sugerida": alert.accion_sugerida,
        }
        for alert in sorted(alerts, key=lambda a: (severity_order.get(a.severidad, 9), a.tipo_alerta, a.entidad))
    ]
    write_csv(
        REPORTS_DIR / "report_alertas_negocio.csv",
        rows,
        ["tipo_alerta", "severidad", "entidad", "metrica", "valor", "descripcion", "accion_sugerida"],
    )


def build_executive_summary(ventas: list[dict[str, str]], gastos: list[dict[str, str]]) -> None:
    ventas_netas = sum(decimal_value(row["importe_neto"]) for row in ventas)
    costo_total = sum(decimal_value(row["costo_total"]) for row in ventas)
    margen_bruto = sum(decimal_value(row["margen_bruto"]) for row in ventas)
    gastos_operativos = sum(decimal_value(row["importe"]) for row in gastos)
    resultado_operativo = margen_bruto - gastos_operativos
    rows = [
        {"metrica": "ventas_netas", "valor": fmt_decimal(ventas_netas), "detalle": "Facturacion neta de notas de credito."},
        {"metrica": "margen_bruto", "valor": fmt_decimal(margen_bruto), "detalle": f"Margen bruto total. Margen sobre ventas: {fmt_pct(safe_ratio(margen_bruto, ventas_netas))}."},
        {"metrica": "gastos_operativos", "valor": fmt_decimal(gastos_operativos), "detalle": "Gastos informados por Sofia, sin asignacion a producto."},
        {"metrica": "resultado_operativo", "valor": fmt_decimal(resultado_operativo), "detalle": f"Margen bruto menos gastos operativos. Resultado sobre ventas: {fmt_pct(safe_ratio(resultado_operativo, ventas_netas))}."},
        {"metrica": "costo_total", "valor": fmt_decimal(costo_total), "detalle": "Costo total calculado por producto y periodo."},
    ]
    write_csv(REPORTS_DIR / "report_resumen_ejecutivo.csv", rows, ["metrica", "valor", "detalle"])


def main() -> None:
    ventas = read_csv(CLEAN_DIR / "clean_ventas.csv")
    gastos = read_csv(CLEAN_DIR / "clean_gastos_operativos.csv")
    alerts: list[Alert] = []

    build_monthly_report(ventas, gastos, alerts)
    build_dimension_report(
        ventas,
        ["codigo_producto", "producto", "rubro"],
        "report_margen_por_producto.csv",
        "producto",
        alerts,
    )
    build_dimension_report(
        ventas,
        ["condicion_comercial"],
        "report_margen_por_canal.csv",
        "canal",
        alerts,
    )
    build_dimension_report(
        ventas,
        ["codigo_cliente", "razon_social", "condicion_comercial", "localidad"],
        "report_margen_por_cliente.csv",
        "cliente",
        alerts,
    )
    build_executive_summary(ventas, gastos)
    build_alerts_report(alerts)

    print("Reports generados en:", REPORTS_DIR)
    print("Alertas de negocio:", len(alerts))


if __name__ == "__main__":
    main()
