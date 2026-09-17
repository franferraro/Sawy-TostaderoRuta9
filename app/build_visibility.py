from __future__ import annotations

import csv
import html
from decimal import Decimal, InvalidOperation
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = CASE_DIR / "data" / "reports"
OUTPUT_PATH = Path(__file__).resolve().parent / "index.html"


def read_csv(name: str) -> list[dict[str, str]]:
    with (REPORTS_DIR / name).open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def dec(value: str | None) -> Decimal:
    try:
        return Decimal((value or "0").strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


def esc(value: object) -> str:
    return html.escape(str(value))


def money(value: Decimal | str) -> str:
    amount = dec(value) if isinstance(value, str) else value
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    return f"{sign}$ {amount:,.0f}".replace(",", ".")


def pct(value: Decimal | str | None) -> str:
    if value in (None, ""):
        return "-"
    number = dec(value) if isinstance(value, str) else value
    return f"{number * Decimal('100'):.1f}%".replace(".", ",")


def severity_class(severity: str) -> str:
    return {
        "CRITICAL": "critical",
        "HIGH": "high",
        "MEDIUM": "medium",
        "INFO": "info",
    }.get(severity, "info")


def severity_label(severity: str) -> str:
    return {
        "CRITICAL": "Critica",
        "HIGH": "Alta",
        "MEDIUM": "Media",
        "INFO": "Info",
        "": "OK",
    }.get(severity, severity or "OK")


def metric_label(metric: str) -> str:
    return {
        "margen_bruto_pct": "Margen bruto",
        "notas_credito_pct": "Devoluciones",
        "ventas_mom_pct": "Cambio de ventas",
        "margen_mom_pct": "Cambio de margen",
    }.get(metric, metric.replace("_", " "))


def pretty_value(metric: str, value: str) -> str:
    if value == "":
        return "-"
    if metric.endswith("_pct"):
        return pct(value)
    return esc(value)


def required_lift_for_target_margin(row: dict[str, str], target_margin: Decimal = Decimal("0.20")) -> tuple[Decimal, Decimal, Decimal]:
    sales = dec(row["ventas_netas"])
    cost = dec(row["costo_total"])
    units = dec(row.get("unidades", "0"))
    if sales <= 0 or cost <= 0 or units <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0")
    required_sales = cost / (Decimal("1") - target_margin)
    lift = required_sales / sales - Decimal("1")
    required_avg_price = required_sales / units
    return required_sales, lift, required_avg_price


def high_alert_recommendation(alert: dict[str, str], lookups: dict[str, dict[str, dict[str, str]]]) -> str:
    if alert["severidad"] != "HIGH":
        return ""

    row = None
    title = ""
    if alert["tipo_alerta"] == "margen_bajo_canal":
        row = lookups["channel"].get(alert["entidad"])
        title = "Recomendacion de canal"
    elif alert["tipo_alerta"] == "margen_bajo_cliente":
        client_name = alert["entidad"].split(" - ")[1] if " - " in alert["entidad"] else alert["entidad"]
        row = lookups["client"].get(client_name)
        title = "Recomendacion de cliente"
    elif alert["tipo_alerta"] == "margen_bajo_producto":
        product_name = alert["entidad"].split(" - ")[1] if " - " in alert["entidad"] else alert["entidad"]
        row = lookups["product"].get(product_name)
        title = "Recomendacion de producto"

    if not row:
        return ""

    required_sales, lift, required_avg_price = required_lift_for_target_margin(row)
    current_avg_price = dec(row["ventas_netas"]) / dec(row["unidades"]) if dec(row.get("unidades", "0")) else Decimal("0")
    base_numbers = [
        f"Objetivo sugerido: llevar el margen bruto a 20%.",
        f"Brecha estimada: el ingreso neto deberia subir aproximadamente {pct(lift)} si el costo no cambia.",
        f"Precio neto promedio actual: {money(current_avg_price)}. Precio neto promedio objetivo: {money(required_avg_price)}.",
    ]

    if alert["tipo_alerta"] == "margen_bajo_canal":
        bullets = [
            *base_numbers,
            "Politica de canal: bajar descuento distribuidor de 40% a cerca de 31%, o mantener descuento solo cobrando flete aparte.",
            "Definir pedido minimo para sostener condicion especial: no renovar descuento si el volumen baja o suben devoluciones.",
            "Medir el canal separado del resto: volumen, margen bruto y devoluciones en la proxima semana.",
        ]
    elif alert["tipo_alerta"] == "margen_bajo_cliente":
        bullets = [
            *base_numbers,
            "Negociacion cliente: llevar a la reunion una propuesta con dos opciones: menor descuento o mismo descuento con flete/pedido minimo.",
            "No discutir solo precio: revisar mix comprado y proponer productos de mayor margen para compensar.",
            "Condicionar la excepcion comercial a menos devoluciones y reposicion mas planificada.",
        ]
    elif alert["tipo_alerta"] == "margen_bajo_producto":
        bullets = [
            *base_numbers,
            "No mirar la caja sola: compararla contra vender 6 unidades de Blend Casa 1 kg por separado.",
            "Hoy la caja x6 queda cerca de $10.770 netos por kilo, por debajo del 1 kg individual, que promedia cerca de $12.373.",
            "Recomendacion: revisar el descuento del pack. Mantener caja solo si simplifica operacion o asegura volumen, pero no usarla como promocion principal.",
            "Si se quiere sostener el pack, compensarlo con menor descuento, flete aparte o combo con productos de mejor margen.",
        ]
    else:
        bullets = base_numbers

    bullet_html = "".join(f"<li>{esc(item)}</li>" for item in bullets)
    return f"""
      <details class="specific-rec">
        <summary>{esc(title)}</summary>
        <ul>{bullet_html}</ul>
      </details>
    """


def alert_category(alert_type: str) -> tuple[str, str]:
    if alert_type == "margen_bajo_canal":
        return "Canales con margen bajo", "Canales donde el margen bruto queda por debajo del umbral esperado."
    if alert_type == "margen_bajo_producto":
        return "Productos con margen bajo", "Productos que conviene revisar antes de empujar mas volumen."
    if alert_type == "margen_bajo_cliente":
        return "Clientes con margen bajo", "Clientes donde las condiciones comerciales pueden estar dejando poco margen."
    if alert_type.startswith("notas_credito_altas"):
        return "Devoluciones a revisar", "Segmentos donde las notas de credito pesan mas de lo esperado."
    if alert_type.startswith("caida_"):
        return "Cambios mensuales", "Meses con cambios relevantes frente al periodo anterior."
    return "Otras alertas", "Alertas adicionales detectadas por las reglas del reporte."


def alert_scope(alert_type: str) -> str:
    if "canal" in alert_type:
        return "Canal"
    if "producto" in alert_type:
        return "Producto"
    if "cliente" in alert_type:
        return "Cliente"
    if "notas_credito" in alert_type:
        return "Devoluciones"
    if "mensual" in alert_type or alert_type.startswith("caida_"):
        return "Tendencia"
    return "Alerta"


def get_metric(summary: list[dict[str, str]], key: str) -> dict[str, str]:
    for row in summary:
        if row["metrica"] == key:
            return row
    return {"metrica": key, "valor": "0", "detalle": ""}


def rows_for_table(rows: list[dict[str, str]], columns: list[tuple[str, str]], limit: int | None = None) -> str:
    visible = rows[:limit] if limit else rows
    body = []
    for row in visible:
        cells = []
        for key, kind in columns:
            value = row.get(key, "")
            if kind == "money":
                rendered = money(value)
                cls = "num"
            elif kind == "pct":
                rendered = pct(value)
                cls = "num"
            elif kind == "alert":
                rendered = f"<span class='pill {severity_class(value)}'>{esc(severity_label(value))}</span>"
                cls = ""
            else:
                rendered = esc(value)
                cls = ""
            cells.append(f"<td class='{cls}'>{rendered}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(body)


def monthly_chart(monthly: list[dict[str, str]]) -> str:
    max_sales = max((dec(row["ventas_netas"]) for row in monthly), default=Decimal("1"))
    output = []
    for row in monthly:
        sales = dec(row["ventas_netas"])
        result = dec(row["resultado_operativo"])
        width = max(4, int((sales / max_sales) * Decimal("100"))) if max_sales else 4
        cls = "good-text" if result >= 0 else "bad-text"
        output.append(
            f"""
            <div class="month-row">
              <div class="month-label">{esc(row['periodo'])}</div>
              <div class="bar-track"><div class="bar" style="width:{width}%"></div></div>
              <div class="month-values">
                <span>{money(row['ventas_netas'])}</span>
                <span>Margen {pct(row['margen_bruto_pct'])}</span>
                <span class="{cls}">Op. {money(row['resultado_operativo'])}</span>
              </div>
            </div>
            """
        )
    return "\n".join(output)


def alert_cards(
    alerts: list[dict[str, str]],
    by_channel: list[dict[str, str]],
    by_product: list[dict[str, str]],
    by_client: list[dict[str, str]],
) -> str:
    lookups = {
        "channel": {row["condicion_comercial"]: row for row in by_channel},
        "product": {row["producto"]: row for row in by_product},
        "client": {row["razon_social"]: row for row in by_client},
    }
    groups = [
        ("CRITICAL", "Alertas criticas", "Margen bruto negativo. Requieren accion inmediata antes de seguir empujando volumen."),
        ("HIGH", "Alertas altas", "Margen bruto entre 0% y 10%. Aca deberia estar el foco de la semana."),
        ("MEDIUM", "Alertas medias", "Margen bruto entre 10% y 20%. Conviene monitorear y corregir condiciones."),
        ("", "OK", "Margen bruto igual o mayor a 20%. No requiere alerta de margen."),
    ]
    output = []
    for severity, title, description in groups:
        group_alerts = [alert for alert in alerts if alert["severidad"] == severity]
        cards = []
        for alert in group_alerts:
            cls = severity_class(alert["severidad"])
            cards.append(
                f"""
                <article class="alert-card {cls}">
                  <div class="alert-top">
                    <span class="pill {cls}">{esc(alert_scope(alert['tipo_alerta']))}</span>
                    <span>{esc(metric_label(alert['metrica']))}: {pretty_value(alert['metrica'], alert['valor'])}</span>
                  </div>
                  <h3>{esc(alert['entidad'])}</h3>
                  <p>{esc(alert['descripcion'])}</p>
                  <strong>{esc(alert['accion_sugerida'])}</strong>
                  {high_alert_recommendation(alert, lookups)}
                </article>
                """
            )
        if not cards:
            cards.append(
                f"""
                <article class="empty-alert">
                  <h3>Sin alertas en este nivel</h3>
                  <p>{esc(description)}</p>
                </article>
                """
            )
        open_attr = "open" if severity == "HIGH" else ""
        output.append(
            f"""
            <details class="alert-group" {open_attr}>
              <summary>
                <span>
                  <strong>{esc(title)}</strong>
                  <small>{esc(description)}</small>
                </span>
                <span class="group-meta">
                  <span class="pill {severity_class(severity)}">{esc(severity_label(severity))}</span>
                  <span>{len(group_alerts)} alertas</span>
                </span>
              </summary>
              <div class="alert-list">{''.join(cards)}</div>
            </details>
            """
        )
    return "\n".join(output)


def client_reason(row: dict[str, str]) -> str:
    channel = row["condicion_comercial"]
    margin = dec(row["margen_bruto_pct"])
    sales = dec(row["ventas_netas"])
    credit_notes = int(row.get("notas_credito", "0") or "0")
    if channel == "Distribuidor":
        return "Concentra mucho volumen y el margen bruto queda bajo."
    if credit_notes > 0:
        return "Tiene devoluciones y margen ajustado; conviene revisar rotacion."
    if sales >= Decimal("1000000"):
        return "Compra volumen relevante, pero el margen queda por debajo del objetivo."
    if margin < Decimal("0.17"):
        return "Margen bajo para sostener descuentos comerciales."
    return "Margen en zona media; revisar antes de ofrecer mas descuento."


def client_cards(rows: list[dict[str, str]], limit: int = 6) -> str:
    cards = []
    for index, row in enumerate(rows[:limit], start=1):
        cards.append(
            f"""
            <article class="client-card">
              <div class="client-rank">{index}</div>
              <div>
                <div class="client-head">
                  <h3>{esc(row['razon_social'])}</h3>
                  <span class="pill {severity_class(row['alerta_margen'])}">{esc(severity_label(row['alerta_margen']))}</span>
                </div>
                <div class="client-metrics">
                  <span>Canal: <strong>{esc(row['condicion_comercial'])}</strong></span>
                  <span>Ventas: <strong>{money(row['ventas_netas'])}</strong></span>
                  <span>Margen: <strong>{pct(row['margen_bruto_pct'])}</strong></span>
                </div>
                <p>{esc(client_reason(row))}</p>
                <strong class="next-step">{esc(row['accion_sugerida'])}</strong>
              </div>
            </article>
            """
        )
    return "\n".join(cards)


def client_detail_rows(rows: list[dict[str, str]], skip: int = 6, limit: int = 12) -> str:
    output = []
    for row in rows[skip : skip + limit]:
        reason = client_reason(row)
        output.append(
            f"""
            <article class="client-line">
              <div>
                <h3>{esc(row['razon_social'])}</h3>
                <div class="client-metrics">
                  <span>{esc(row['condicion_comercial'])}</span>
                  <span>Ventas: <strong>{money(row['ventas_netas'])}</strong></span>
                  <span>Margen: <strong>{pct(row['margen_bruto_pct'])}</strong></span>
                </div>
              </div>
              <div>
                <span class="reason-chip">{esc(reason)}</span>
                <p>{esc(row['accion_sugerida'])}</p>
              </div>
            </article>
            """
        )
    return "\n".join(output)


def questions() -> str:
    data = [
        (
            "Estoy ganando plata?",
            "En el semestre completo, todavia no del todo. Hay margen bruto, pero no alcanza de forma consistente para cubrir los gastos operativos.",
        ),
        (
            "Que canal deberia revisar primero?",
            "Distribuidor. Tiene mucho peso en ventas, pero el margen bruto queda bajo para sostener el negocio.",
        ),
        (
            "Que conviene empujar?",
            "Ecommerce y mostrador/local. Tienen mejor margen bruto y pueden ayudar a compensar los canales de menor rentabilidad.",
        ),
        (
            "Que hago esta semana?",
            "Revisar Granos del Sur, entender el precio real de la caja x6 frente al 1 kg individual, y empujar productos/canales con mejor margen.",
        ),
    ]
    return "\n".join(
        f"""
        <details>
          <summary>{esc(question)}</summary>
          <p>{esc(answer)}</p>
        </details>
        """
        for question, answer in data
    )


def count_alerts(alerts: list[dict[str, str]], severity: str) -> int:
    return sum(1 for alert in alerts if alert["severidad"] == severity)


def main() -> None:
    summary = read_csv("report_resumen_ejecutivo.csv")
    monthly = read_csv("report_resultado_mensual.csv")
    by_channel = read_csv("report_margen_por_canal.csv")
    by_product = read_csv("report_margen_por_producto.csv")
    by_client = read_csv("report_margen_por_cliente.csv")
    alerts = read_csv("report_alertas_negocio.csv")

    sales = get_metric(summary, "ventas_netas")
    gross_margin = get_metric(summary, "margen_bruto")
    expenses = get_metric(summary, "gastos_operativos")
    operating = get_metric(summary, "resultado_operativo")

    product_risk = sorted(by_product, key=lambda r: dec(r["margen_bruto_pct"]))
    client_risk = sorted(by_client, key=lambda r: dec(r["margen_bruto_pct"]))

    html_doc = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sawy - Tostadero Ruta 9</title>
  <style>
    :root {{
      --bg: #f4f1ea;
      --panel: #fffdf8;
      --ink: #181b1f;
      --muted: #66706b;
      --line: #ded8cb;
      --green: #0d7c66;
      --red: #b42318;
      --amber: #b54708;
      --dark: #151715;
      --soft-green: #e7f4ef;
      --soft-red: #fdecec;
      --soft-amber: #fff4e5;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    header {{
      background: var(--dark);
      color: #fffdf8;
      padding: 24px 28px 28px;
    }}
    main {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 18px 28px 44px;
    }}
    h1 {{ margin: 0; font-size: 42px; letter-spacing: 0; max-width: 880px; }}
    h2 {{ margin: 0 0 14px; font-size: 20px; }}
    h3 {{ margin: 0 0 8px; font-size: 15px; }}
    p {{ margin: 0; color: var(--muted); }}
    header p {{ color: #d9ded8; }}
    .topbar {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 34px; }}
    .brand {{ font-weight: 900; font-size: 20px; }}
    .eyebrow {{ color: #9ee0ca; font-size: 12px; font-weight: 800; text-transform: uppercase; }}
    .subtitle {{ margin-top: 10px; max-width: 880px; font-size: 16px; }}
    .hero-actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }}
    .hero-chip {{ border: 1px solid rgba(255,255,255,.22); border-radius: 999px; padding: 8px 12px; color: #f4f1ea; font-size: 13px; }}
    .tabs {{ display: flex; gap: 8px; flex-wrap: wrap; position: sticky; top: 0; z-index: 5; background: rgba(244,241,234,.96); border-bottom: 1px solid var(--line); padding: 12px 0; margin-bottom: 8px; }}
    .tab-button {{ appearance: none; border: 1px solid var(--line); background: var(--panel); color: var(--ink); border-radius: 999px; padding: 9px 13px; font: inherit; font-size: 14px; font-weight: 800; cursor: pointer; }}
    .tab-button.active {{ background: var(--dark); color: #fffdf8; border-color: var(--dark); }}
    .tab-panel {{ display: none; }}
    .tab-panel.active {{ display: block; }}
    .grid {{ display: grid; gap: 16px; }}
    .kpis {{ grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 0; align-items: stretch; }}
    .two {{ grid-template-columns: minmax(0, 1.15fr) minmax(360px, .85fr); }}
    section, .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }}
    .card {{ min-height: 132px; }}
    section {{ margin-top: 16px; }}
    .kpi-label {{ color: var(--muted); font-size: 13px; }}
    .kpi-value {{ display: block; margin-top: 6px; font-size: 28px; font-weight: 800; }}
    .kpi-note {{ display: block; margin-top: 5px; color: var(--muted); font-size: 12px; }}
    .bad-text {{ color: var(--red); font-weight: 800; }}
    .good-text {{ color: var(--green); font-weight: 800; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .table-scroll {{ max-height: 430px; overflow: auto; border: 1px solid #edf0f2; border-radius: 8px; }}
    .table-scroll table {{ border: 0; }}
    .table-scroll thead th {{ position: sticky; top: 0; z-index: 1; }}
    th, td {{ border-bottom: 1px solid #edf0f2; padding: 9px 8px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 700; background: #fafafa; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
    .month-row {{ display: grid; grid-template-columns: 82px minmax(140px, 1fr) 330px; gap: 12px; align-items: center; padding: 10px 0; border-bottom: 1px solid #edf0f2; }}
    .month-row:last-child {{ border-bottom: 0; }}
    .month-label {{ font-weight: 800; }}
    .bar-track {{ height: 14px; background: #e7ecf2; border-radius: 999px; overflow: hidden; }}
    .bar {{ height: 100%; background: var(--green); border-radius: 999px; }}
    .month-values {{ display: grid; grid-template-columns: 1fr 90px 120px; gap: 8px; color: var(--muted); font-size: 12px; }}
    .pill {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 3px 8px; font-size: 12px; font-weight: 800; background: #eef2f6; color: #344054; }}
    .pill.critical, .pill.high {{ background: var(--soft-red); color: var(--red); }}
    .pill.medium {{ background: var(--soft-amber); color: var(--amber); }}
    .pill.info {{ background: var(--soft-green); color: var(--green); }}
    .alert-list {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .alert-group {{ border: 1px solid var(--line); border-radius: 8px; background: #fff; margin-top: 12px; overflow: hidden; }}
    .alert-group > summary {{ list-style: none; cursor: pointer; display: flex; justify-content: space-between; gap: 16px; align-items: center; padding: 14px 16px; border-bottom: 1px solid transparent; }}
    .alert-group > summary::-webkit-details-marker {{ display: none; }}
    .alert-group[open] > summary {{ border-bottom-color: #edf0f2; }}
    .alert-group small {{ display: block; color: var(--muted); font-weight: 500; margin-top: 3px; }}
    .alert-group .alert-list {{ padding: 14px; }}
    .group-meta {{ display: flex; gap: 8px; align-items: center; color: var(--muted); font-size: 12px; white-space: nowrap; }}
    .alert-card {{ border: 1px solid var(--line); border-left: 5px solid var(--line); border-radius: 8px; padding: 14px; background: #fff; }}
    .alert-card.high, .alert-card.critical {{ border-left-color: var(--red); }}
    .alert-card.medium {{ border-left-color: var(--amber); }}
    .alert-card.info {{ border-left-color: var(--green); }}
    .empty-alert {{ border: 1px dashed var(--line); border-radius: 8px; padding: 14px; background: #fff; }}
    .alert-top {{ display: flex; justify-content: space-between; gap: 8px; color: var(--muted); font-size: 12px; margin-bottom: 10px; }}
    .alert-card strong {{ display: block; margin-top: 8px; font-size: 13px; }}
    .specific-rec {{ margin-top: 10px; border: 1px solid #edf0f2; border-radius: 8px; padding: 0; background: #fbfdfb; }}
    .specific-rec summary {{ padding: 10px 12px; }}
    .specific-rec ul {{ margin: 0; padding: 0 14px 12px 28px; color: var(--muted); }}
    .specific-rec li {{ margin-top: 6px; }}
    .answer {{ border-left: 5px solid var(--green); background: #fbfdfb; }}
    .answer p {{ font-size: 16px; }}
    .decision-list {{ display: grid; gap: 10px; margin-top: 12px; }}
    .decision {{ display: grid; grid-template-columns: 34px 1fr; gap: 12px; border-top: 1px solid #edf0f2; padding-top: 12px; }}
    .decision:first-child {{ border-top: 0; padding-top: 0; }}
    .decision-num {{ width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; background: var(--soft-green); color: var(--green); font-weight: 900; }}
    .client-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 14px; }}
    .client-card {{ display: grid; grid-template-columns: 34px 1fr; gap: 12px; border: 1px solid var(--line); border-radius: 8px; background: #fff; padding: 14px; }}
    .client-rank {{ width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; background: var(--dark); color: #fffdf8; font-weight: 900; }}
    .client-head {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }}
    .client-metrics {{ display: flex; flex-wrap: wrap; gap: 8px 14px; color: var(--muted); font-size: 12px; margin: 6px 0 8px; }}
    .next-step {{ display: block; margin-top: 8px; font-size: 13px; }}
    .client-lines {{ display: grid; gap: 10px; margin-top: 10px; }}
    .client-line {{ display: grid; grid-template-columns: minmax(220px, .75fr) minmax(0, 1.25fr); gap: 14px; align-items: start; border: 1px solid var(--line); border-radius: 8px; background: #fff; padding: 13px; }}
    .client-line h3 {{ margin-bottom: 4px; }}
    .reason-chip {{ display: inline-block; border-radius: 999px; background: #eef2f6; color: var(--muted); padding: 5px 9px; font-size: 12px; font-weight: 800; margin-bottom: 7px; }}
    .assumption-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 10px; }}
    .assumption {{ border: 1px solid var(--line); border-radius: 8px; background: #fff; padding: 13px; }}
    .assumption strong {{ display: block; margin-bottom: 4px; }}
    details {{ border-bottom: 1px solid #edf0f2; padding: 12px 0; }}
    details:last-child {{ border-bottom: 0; }}
    summary {{ cursor: pointer; font-weight: 800; }}
    details p {{ margin-top: 8px; }}
    .small-note {{ font-size: 12px; color: var(--muted); margin-top: 10px; }}
    @media (max-width: 950px) {{
      header, main {{ padding-left: 16px; padding-right: 16px; }}
      h1 {{ font-size: 32px; }}
      .topbar {{ align-items: flex-start; flex-direction: column; margin-bottom: 24px; }}
      .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .two, .alert-list, .client-grid, .client-line, .assumption-grid {{ grid-template-columns: 1fr; }}
      .alert-group > summary {{ align-items: flex-start; flex-direction: column; }}
      .group-meta {{ white-space: normal; }}
      .month-row {{ grid-template-columns: 70px 1fr; }}
      .month-values {{ grid-column: 1 / -1; grid-template-columns: 1fr 1fr 1fr; }}
      table {{ font-size: 12px; }}
    }}
    @media (max-width: 620px) {{
      .kpis {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="topbar">
      <div class="brand">Sawy · Ruta 9</div>
    </div>
    <h1>Hola Sofia, estas son las oportunidades escondidas en tus datos</h1>
    <p class="subtitle">El objetivo no es mirar mas graficos: es entender por que se factura, pero la caja no acompaña, y decidir que ajustar esta semana.</p>
    <div class="hero-actions">
      <span class="hero-chip">{count_alerts(alerts, 'HIGH')} alertas altas</span>
      <span class="hero-chip">{len(alerts)} oportunidades detectadas</span>
    </div>
  </header>

  <main>
    <nav class="tabs" aria-label="Secciones">
      <button class="tab-button active" data-tab="diagnostico">Diagnostico</button>
      <button class="tab-button" data-tab="acciones">Acciones</button>
      <button class="tab-button" data-tab="canales">Canales y productos</button>
      <button class="tab-button" data-tab="clientes">Clientes</button>
      <button class="tab-button" data-tab="preguntas">Preguntas</button>
      <button class="tab-button" data-tab="metodo">Metodo</button>
    </nav>

    <section class="tab-panel active" id="diagnostico">
      <section class="answer">
        <h2>Diagnostico</h2>
        <p>Sofia: estas vendiendo, y el cafe deja margen bruto. El problema es que una parte importante de ese margen se pierde entre gastos operativos, descuentos y algunos formatos que quedan demasiado finos. No parece un negocio roto; parece un negocio que necesita ajustar precio, descuento y mix para que la plata que se factura tambien quede en la cuenta.</p>
      </section>

      <div class="grid kpis">
        <div class="card"><span class="kpi-label">Ventas netas</span><span class="kpi-value">{money(sales['valor'])}</span><span class="kpi-note">Facturas menos notas de credito</span></div>
        <div class="card"><span class="kpi-label">Margen bruto</span><span class="kpi-value">{money(gross_margin['valor'])}</span><span class="kpi-note">Ventas menos costo directo del producto</span></div>
        <div class="card"><span class="kpi-label">Gastos operativos</span><span class="kpi-value">{money(expenses['valor'])}</span><span class="kpi-note">Flete, sueldos, alquiler y otros gastos</span></div>
        <div class="card"><span class="kpi-label">Resultado operativo</span><span class="kpi-value bad-text">{money(operating['valor'])}</span><span class="kpi-note">Margen bruto menos gastos operativos</span></div>
      </div>

      <div class="grid two">
        <section>
          <h2>Evolucion mensual</h2>
          {monthly_chart(monthly)}
        </section>
        <section>
          <h2>Lectura rapida</h2>
          <p>El margen bruto existe, pero no alcanza de manera consistente para cubrir los gastos operativos. Por eso la accion no es solo vender mas: es vender mejor.</p>
          <p class="small-note">La clave es mover volumen hacia productos y canales con mejor margen, y corregir condiciones donde el margen queda bajo.</p>
        </section>
      </div>
    </section>

    <section class="tab-panel" id="acciones">
      <h2>Acciones recomendadas para esta semana</h2>
      <p>Estas medidas salen de los reportes. No son ordenes automaticas: son puntos concretos para que Sofia decida que conversar, que pausar y que empujar.</p>
      <div class="decision-list">
        <div class="decision"><div class="decision-num">1</div><div><h3>Revisar Granos del Sur y el canal distribuidor</h3><p>Es el mayor bloque de ventas, pero el margen bruto queda bajo. Conviene revisar descuento, precio minimo y flete absorbido.</p></div></div>
        <div class="decision"><div class="decision-num">2</div><div><h3>Revisar arquitectura de precios del Blend Casa</h3><p>La caja x6 parece demasiado barata contra vender 6 unidades de 1 kg. Antes de subir o promocionar, comparar pack, descuento y costo por kilo.</p></div></div>
        <div class="decision"><div class="decision-num">3</div><div><h3>Promocionar productos con mejor margen</h3><p>Usar combos, vidriera y comunicacion online para empujar las presentaciones de 250 g y accesorios que muestran mejor margen bruto.</p></div></div>
        <div class="decision"><div class="decision-num">4</div><div><h3>Empujar ecommerce y mostrador</h3><p>Son canales con mejor margen bruto. Si hay capacidad operativa, tienen mejor relacion entre esfuerzo comercial y margen.</p></div></div>
        <div class="decision"><div class="decision-num">5</div><div><h3>Llamar clientes mayoristas en alerta</h3><p>Usar la lista de clientes para revisar condiciones comerciales donde el margen queda por debajo del umbral.</p></div></div>
      </div>

      <section>
        <h2>Alertas accionables</h2>
        {alert_cards(alerts, by_channel, by_product, by_client)}
      </section>
    </section>

    <section class="tab-panel" id="canales">
      <div class="grid two">
        <section>
          <h2>Rentabilidad por canal</h2>
          <table>
            <thead><tr><th>Canal</th><th class="num">Ventas</th><th class="num">Margen bruto</th><th class="num">% margen</th><th class="num">% ventas</th><th>Alerta</th></tr></thead>
            <tbody>{rows_for_table(by_channel, [('condicion_comercial','text'), ('ventas_netas','money'), ('margen_bruto','money'), ('margen_bruto_pct','pct'), ('participacion_ventas_pct','pct'), ('alerta_margen','alert')])}</tbody>
          </table>
        </section>
        <section>
          <h2>Productos a revisar</h2>
          <div class="table-scroll">
            <table>
              <thead><tr><th>Producto</th><th class="num">Precio prom.</th><th class="num">Costo prom.</th><th class="num">% margen</th><th>Alerta</th></tr></thead>
              <tbody>{rows_for_table(product_risk, [('producto','text'), ('precio_venta_promedio','money'), ('costo_unitario_promedio','money'), ('margen_bruto_pct','pct'), ('alerta_margen','alert')])}</tbody>
            </table>
          </div>
        </section>
      </div>
    </section>

    <section class="tab-panel" id="clientes">
      <h2>Clientes a revisar primero</h2>
      <p>Ordenados por margen bruto mas bajo. La idea no es dejar de venderles, sino revisar si el descuento, el mix o las devoluciones justifican el volumen.</p>
      <div class="client-grid">
        {client_cards(client_risk)}
      </div>
      <section>
        <h2>Otros clientes para monitorear</h2>
        <div class="client-lines">{client_detail_rows(client_risk)}</div>
      </section>
    </section>

    <section class="tab-panel" id="preguntas">
      <h2>Preguntale algo a los datos</h2>
      <p>Primera version con preguntas guiadas y respuestas trazables desde Reports.</p>
      {questions()}
    </section>

    <section class="tab-panel" id="metodo">
      <h2>Como se construyo</h2>
      <p>El flujo separa datos crudos, tipado, reglas de negocio y reportes para no mezclar limpieza con visualizacion.</p>
      <div class="grid kpis">
        <div class="card"><span class="kpi-label">RAW</span><span class="kpi-value">ERP</span><span class="kpi-note">Archivos originales sin modificar</span></div>
        <div class="card"><span class="kpi-label">stage</span><span class="kpi-value">Tipos</span><span class="kpi-note">Fechas, numeros y controles basicos</span></div>
        <div class="card"><span class="kpi-label">clean</span><span class="kpi-value">Reglas</span><span class="kpi-note">Codigos viejos, costos y margen</span></div>
        <div class="card"><span class="kpi-label">Reports</span><span class="kpi-value">Decision</span><span class="kpi-note">Tablas para dashboard y preguntas</span></div>
      </div>
      <p class="small-note">La normalizacion de codigos viejos conserva el codigo original para auditoria. Los gastos operativos no se asignan por producto porque el ERP no trae esa apertura.</p>
      <p class="small-note">Las recomendaciones de canal, cliente y producto estan generadas por reglas de negocio codificadas sobre los reportes. Con una capa de IA integrada, esta misma base podria redactar recomendaciones dinamicas y responder repreguntas, pero manteniendo estos calculos como trazabilidad.</p>
      <section>
        <h2>Supuestos usados</h2>
        <div class="assumption-grid">
          <div class="assumption"><strong>Notas de credito</strong><p>Se toman como devoluciones: restan ventas, unidades, costo y margen.</p></div>
          <div class="assumption"><strong>Gastos operativos</strong><p>Se analizan a nivel negocio porque el ERP no los trae abiertos por producto o cliente.</p></div>
          <div class="assumption"><strong>Precios historicos</strong><p>Se usa el importe facturado del ERP. Los precios de lista actuales no recalculan ventas pasadas.</p></div>
          <div class="assumption"><strong>Margen por cliente/producto</strong><p>Es margen bruto. No representa resultado final despues de todos los gastos.</p></div>
        </div>
      </section>
      <section>
        <h2>Glosario</h2>
        <details open>
          <summary>Margen bruto</summary>
          <p>Es lo que queda despues de restar el costo directo del producto vendido. Todavia no descuenta sueldos, alquiler, flete ni otros gastos operativos.</p>
        </details>
        <details>
          <summary>Resultado operativo</summary>
          <p>Es el margen bruto menos los gastos operativos. Ayuda a ver si el negocio alcanza a cubrir su estructura.</p>
        </details>
        <details>
          <summary>Ventas netas</summary>
          <p>Son las ventas despues de restar notas de credito o devoluciones.</p>
        </details>
      </section>
    </section>
  </main>

  <script>
    const buttons = document.querySelectorAll('.tab-button');
    const panels = document.querySelectorAll('.tab-panel');
    buttons.forEach((button) => {{
      button.addEventListener('click', () => {{
        const tab = button.dataset.tab;
        buttons.forEach((item) => item.classList.toggle('active', item === button));
        panels.forEach((panel) => panel.classList.toggle('active', panel.id === tab));
      }});
    }});
  </script>
</body>
</html>
"""
    OUTPUT_PATH.write_text(html_doc, encoding="utf-8")
    print("Herramienta generada en:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
