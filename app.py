from __future__ import annotations

import html
import hmac
import os
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

from flask import Flask, Response, render_template, request
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
LOGO_PATH = ROOT / "static" / "meyrin-ctt-logo.png"
CLUB_NAME = "Meyrin CTT"
CLUB_ADDRESS = "Rue De-Livron 2\n1217 Meyrin"
BRAND_BLUE = colors.HexColor("#153B67")
BRAND_RED = colors.HexColor("#E4312B")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#667085")
PALE_BLUE = colors.HexColor("#EEF4FA")
LIGHT_LINE = colors.HexColor("#D7DEE8")


def money(value: Decimal) -> str:
    value = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{value:,.2f}".replace(",", "'") + " CHF"


def dec(value: str | None, default: str = "0") -> Decimal:
    cleaned = (value or "").strip().replace("'", "").replace(" ", "").replace(",", ".")
    if not cleaned:
        return Decimal(default)
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Valeur numérique invalide: {value}") from exc


def display_date(value: str) -> str:
    for date_format in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, date_format).strftime("%d.%m.%Y")
        except ValueError:
            continue
    return value


def checkbox_enabled(form, name: str, default: bool = True) -> bool:
    values = form.getlist(name) if hasattr(form, "getlist") else [form.get(name)]
    values = [str(value).lower() for value in values if value is not None]
    if not values:
        return default
    return values[-1] not in {"0", "false", "off", "no"}


def filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-")
    return cleaned or "document"


def p(text: object, style: ParagraphStyle) -> Paragraph:
    safe = html.escape(str(text or ""), quote=True)
    for tag in ("<br/>", "<b>", "</b>"):
        safe = safe.replace(html.escape(tag), tag)
    return Paragraph(safe.replace("\n", "<br/>"), style)


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK),
        "small": ParagraphStyle("Small", parent=base["BodyText"], fontName="Helvetica", fontSize=7.3, leading=9, textColor=MUTED),
        "label": ParagraphStyle("Label", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=MUTED, uppercase=True),
        "table_header": ParagraphStyle("TableHeader", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9, textColor=colors.white),
        "title": ParagraphStyle("Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20, leading=23, textColor=BRAND_BLUE, alignment=TA_RIGHT),
        "section": ParagraphStyle("Section", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=BRAND_BLUE),
        "right": ParagraphStyle("Right", parent=base["BodyText"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK, alignment=TA_RIGHT),
        "right_bold": ParagraphStyle("RightBold", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=INK, alignment=TA_RIGHT),
        "center": ParagraphStyle("Center", parent=base["BodyText"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK, alignment=TA_CENTER),
        "total": ParagraphStyle("Total", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=13, leading=15, textColor=BRAND_BLUE, alignment=TA_CENTER),
    }


def logo_flowable(width: float = 38 * mm) -> Image | Spacer:
    if LOGO_PATH.exists():
        img = Image(str(LOGO_PATH))
        img._restrictSize(width, 22 * mm)
        return img
    return Spacer(width, 12 * mm)


def document_response(pdf: bytes, filename: str, download: bool) -> Response:
    disposition = "attachment" if download else "inline"
    encoded = quote(filename)
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"{disposition}; filename*=UTF-8''{encoded}"},
    )


def base_doc(buffer: BytesIO, title: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=13 * mm,
        title=title,
        author=CLUB_NAME,
        subject=title,
    )


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LIGHT_LINE)
    canvas.line(16 * mm, 10 * mm, A4[0] - 16 * mm, 10 * mm)
    canvas.setFont("Helvetica", 6.8)
    canvas.setFillColor(MUTED)
    canvas.drawString(16 * mm, 6.5 * mm, "Meyrin CTT · Rue De-Livron 2 · 1217 Meyrin")
    canvas.drawRightString(A4[0] - 16 * mm, 6.5 * mm, f"Page {doc.page}")
    canvas.restoreState()


def salary_pdf(form) -> tuple[bytes, str]:
    st = styles()
    trainer = form.get("trainer_name", "").strip()
    if not trainer:
        raise ValueError("Le nom de l'entraîneur est obligatoire.")

    remuneration_mode = form.get("remuneration_mode", "global")
    gross_lines = []
    contribution_base = Decimal("0")
    if remuneration_mode == "detailed":
        descriptions = form.getlist("activity_description[]")
        quantities = form.getlist("activity_hours[]")
        rates = form.getlist("activity_rate[]")
        charge_flags = form.getlist("activity_subject_to_charges[]")
        for index, (description, quantity, rate) in enumerate(zip(descriptions, quantities, rates)):
            hours = dec(quantity)
            hourly_rate = dec(rate)
            if description.strip() or hours or hourly_rate:
                amount = hours * hourly_rate
                subject_to_charges = index >= len(charge_flags) or charge_flags[index].lower() not in {"0", "false", "off", "no"}
                label = description.strip() or "Activité"
                gross_lines.append((label if subject_to_charges else f"{label} (sans charges)", hours, "heure", hourly_rate, amount))
                if subject_to_charges:
                    contribution_base += amount
    else:
        hours = dec(form.get("hours"))
        hourly_rate = dec(form.get("hourly_rate"))
        amount = hours * hourly_rate
        subject_to_charges = checkbox_enabled(form, "global_subject_to_charges")
        label = form.get("global_description", "Heures d'entraînement").strip() or "Heures d'entraînement"
        gross_lines.append((label if subject_to_charges else f"{label} (sans charges)", hours, "heure", hourly_rate, amount))
        if subject_to_charges:
            contribution_base += amount

    tax_exempt_amount = dec(form.get("tax_exempt_amount"))
    gross = sum((row[4] for row in gross_lines), Decimal("0")) + tax_exempt_amount
    if tax_exempt_amount or form.get("tax_exempt_description", "").strip():
        tax_exempt_label = form.get("tax_exempt_description", "Rémunération exonérée").strip() or "Rémunération exonérée"
        gross_lines.append((f"{tax_exempt_label} (exonéré)", Decimal("1"), "forfait", tax_exempt_amount, tax_exempt_amount))

    deduction_specs = [
        ("AVS / AI / APG", dec(form.get("avs_rate"), "5.3")),
        ("Assurance chômage", dec(form.get("unemployment_rate"), "1.1")),
        ("Assurance accident", dec(form.get("accident_rate"))),
        ("LPP", dec(form.get("lpp_rate"))),
        ("Impôt à la source", dec(form.get("withholding_rate"))),
    ]
    extra_label = form.get("extra_deduction_label", "").strip()
    extra_rate = dec(form.get("extra_deduction_rate"))
    if extra_label or extra_rate:
        deduction_specs.append((extra_label or "Autre retenue", extra_rate))

    deductions_enabled = checkbox_enabled(form, "deductions_enabled")
    deductions = []
    for label, rate in deduction_specs:
        amount = (contribution_base * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if deductions_enabled else Decimal("0")
        deductions.append((label, rate, amount))
    total_deductions = sum((row[2] for row in deductions), Decimal("0"))
    net = gross - total_deductions

    period_start = display_date(form.get("period_start", ""))
    period_end = display_date(form.get("period_end", ""))
    period = f"Période du {period_start} au {period_end}"

    buffer = BytesIO()
    doc = base_doc(buffer, f"Bulletin de paye - {trainer}")
    story = []
    header = Table(
        [
            [logo_flowable(), p("BULLETIN DE PAYE", st["title"])],
            [p("Rue De-Livron 2<br/>1217 Meyrin", st["small"]), p(period, st["right"])],
        ],
        colWidths=[80 * mm, 98 * mm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4 * mm),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 2 * mm),
    ]))
    story += [header, Spacer(1, 5 * mm)]

    employee = Table(
        [
            [p("EMPLOYEUR", st["label"]), p("ENTRAÎNEUR", st["label"])],
            [p(f"{CLUB_NAME}\n{CLUB_ADDRESS}\nFonction: {form.get('role', 'Moniteur de tennis de table')}", st["body"]),
             p(f"<b>{trainer}</b>\n{form.get('trainer_address', '')}\nN° AVS: {form.get('avs_number', '')}\nDate de naissance: {display_date(form.get('birth_date', ''))}", st["body"])],
        ],
        colWidths=[89 * mm, 89 * mm],
    )
    employee.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, LIGHT_LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LIGHT_LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
    ]))
    story += [employee, Spacer(1, 5 * mm), p("RÉMUNÉRATION", st["section"]), Spacer(1, 1.5 * mm)]

    pay_data = [[p("Désignation", st["table_header"]), p("Quantité", st["table_header"]), p("Unité", st["table_header"]), p("Tarif", st["table_header"]), p("Montant", st["table_header"])]]
    for label, qty, unit, rate, amount in gross_lines:
        pay_data.append([p(label, st["body"]), p(qty.normalize(), st["right"]), p(unit, st["body"]), p(money(rate), st["right"]), p(money(amount), st["right"] )])
    pay_data.append([p("Salaire brut", st["right_bold"]), "", "", "", p(money(gross), st["right_bold"])])
    pay = Table(pay_data, colWidths=[66 * mm, 23 * mm, 22 * mm, 31 * mm, 36 * mm], repeatRows=1)
    pay.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -2), 0.4, LIGHT_LINE),
        ("SPAN", (0, -1), (3, -1)),
        ("BACKGROUND", (0, -1), (-1, -1), PALE_BLUE),
        ("BOX", (0, -1), (-1, -1), 0.6, BRAND_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.3 * mm),
    ]))
    story += [pay, Spacer(1, 4.5 * mm), p("COTISATIONS ET RETENUES", st["section"]), Spacer(1, 1.5 * mm)]

    ded_data = [[p("Désignation", st["table_header"]), p("Base", st["table_header"]), p("Taux", st["table_header"]), p("Retenue", st["table_header"])]]
    for label, rate, amount in deductions:
        ded_data.append([p(label, st["body"]), p(money(contribution_base), st["right"]), p(f"{rate.normalize()} %", st["right"]), p(money(amount), st["right"])])
    ded_data.append([p("Total des cotisations", st["right_bold"]), "", "", p(money(total_deductions), st["right_bold"])])
    ded = Table(ded_data, colWidths=[76 * mm, 38 * mm, 28 * mm, 36 * mm], repeatRows=1)
    ded.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -2), 0.4, LIGHT_LINE),
        ("SPAN", (0, -1), (2, -1)),
        ("BACKGROUND", (0, -1), (-1, -1), PALE_BLUE),
        ("BOX", (0, -1), (-1, -1), 0.6, BRAND_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.9 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.9 * mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.3 * mm),
    ]))
    story += [ded, Spacer(1, 5 * mm)]

    summary = Table(
        [
            [p("SALAIRE BRUT", st["label"]), p("CHARGES SALARIALES", st["label"]), p("SALAIRE NET", st["label"])],
            [p(money(gross), st["total"]), p(money(total_deductions), st["total"]), p(money(net), st["total"])],
        ],
        colWidths=[59.3 * mm] * 3,
    )
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.8, BRAND_BLUE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LIGHT_LINE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, 0), 2.2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2.2 * mm),
        ("TOPPADDING", (0, 1), (-1, 1), 4 * mm),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 4 * mm),
    ]))
    signatures = Table(
        [[p("Date", st["label"]), p("Fonction", st["label"]), p("Signature", st["label"])], ["", "", ""]],
        colWidths=[59.3 * mm] * 3,
        rowHeights=[8 * mm, 18 * mm],
    )
    signatures.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LIGHT_LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LIGHT_LINE),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [KeepTogether([summary, Spacer(1, 5 * mm), signatures])]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    filename = f"Bulletin-paye-{filename_part(trainer)}-{form.get('period_end', date.today().isoformat())}.pdf"
    return buffer.getvalue(), filename


def invoice_pdf(form) -> tuple[bytes, str]:
    st = styles()
    trainer = form.get("invoice_trainer_name", "").strip()
    if not trainer:
        raise ValueError("Le nom de l'émetteur est obligatoire.")
    descriptions = form.getlist("item_description[]")
    quantities = form.getlist("item_quantity[]")
    units = form.getlist("item_unit[]")
    rates = form.getlist("item_rate[]")
    lines = []
    for description, quantity, unit, rate in zip(descriptions, quantities, units, rates):
        if not description.strip() and not quantity.strip() and not rate.strip():
            continue
        qty = dec(quantity, "1")
        unit_rate = dec(rate)
        lines.append((description.strip() or "Prestation", qty, unit.strip() or "unité", unit_rate, qty * unit_rate))
    if not lines:
        raise ValueError("Ajoutez au moins une prestation à la facture.")
    subtotal = sum((row[4] for row in lines), Decimal("0"))
    vat_rate = dec(form.get("vat_rate"))
    vat = (subtotal * vat_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = subtotal + vat
    number = form.get("invoice_number", "").strip() or f"{date.today():%Y%m%d}"
    buffer = BytesIO()
    doc = base_doc(buffer, f"Facture {number}")
    story = []
    header = Table(
        [[logo_flowable(), p("FACTURE", st["title"])], [p(f"<b>{trainer}</b><br/>{form.get('invoice_trainer_address', '')}", st["body"]), p(f"<b>N° {number}</b><br/>Émise le {display_date(form.get('issue_date', ''))}<br/>Échéance: {display_date(form.get('due_date', ''))}", st["right"]) ]],
        colWidths=[89 * mm, 89 * mm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4 * mm),
    ]))
    story += [header, Spacer(1, 8 * mm)]
    client = Table(
        [[p("FACTURÉ À", st["label"])], [p(f"<b>{form.get('client_name', CLUB_NAME)}</b><br/>{form.get('client_address', CLUB_ADDRESS)}", st["body"]) ]],
        colWidths=[86 * mm],
    )
    client.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, LIGHT_LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
    ]))
    story += [client, Spacer(1, 9 * mm)]
    data = [[p("Prestation", st["table_header"]), p("Quantité", st["table_header"]), p("Unité", st["table_header"]), p("Tarif", st["table_header"]), p("Montant", st["table_header"])]]
    for description, qty, unit, rate, amount in lines:
        data.append([p(description, st["body"]), p(qty.normalize(), st["right"]), p(unit, st["body"]), p(money(rate), st["right"]), p(money(amount), st["right"])])
    items = Table(data, colWidths=[72 * mm, 23 * mm, 22 * mm, 29 * mm, 32 * mm], repeatRows=1)
    items.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, LIGHT_LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.8 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.8 * mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.4 * mm),
    ]))
    story += [items, Spacer(1, 5 * mm)]
    totals = Table(
        [
            [p("Sous-total", st["right"]), p(money(subtotal), st["right"])],
            [p(f"TVA ({vat_rate.normalize()} %)", st["right"]), p(money(vat), st["right"])],
            [p("TOTAL", st["right_bold"]), p(money(total), st["right_bold"])],
        ],
        colWidths=[38 * mm, 40 * mm],
        hAlign="RIGHT",
    )
    totals.setStyle(TableStyle([
        ("LINEABOVE", (0, -1), (-1, -1), 1, BRAND_BLUE),
        ("BACKGROUND", (0, -1), (-1, -1), PALE_BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    payment_text = f"<b>Coordonnées de paiement</b><br/>IBAN: {form.get('iban', '')}<br/>{form.get('payment_note', 'Merci pour votre confiance.')}"
    story += [totals, Spacer(1, 14 * mm), Table([[p(payment_text, st["body"])]], colWidths=[178 * mm], style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.6, LIGHT_LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue(), f"Facture-{filename_part(number)}-{filename_part(trainer)}.pdf"


def create_app() -> Flask:
    app = Flask(__name__)

    @app.before_request
    def optional_basic_auth():
        expected = os.environ.get("APP_PASSWORD")
        if not expected or request.path == "/health":
            return None
        username = os.environ.get("APP_USERNAME", "admin")
        auth = request.authorization
        if not auth or not hmac.compare_digest(auth.username or "", username) or not hmac.compare_digest(auth.password or "", expected):
            return Response("Authentification requise", 401, {"WWW-Authenticate": 'Basic realm="Meyrin CTT documents"'})
        return None

    @app.get("/")
    def index():
        today = date.today()
        month_start = today.replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_end = next_month - timedelta(days=1)
        return render_template(
            "index.html",
            today=today.isoformat(),
            due=(today + timedelta(days=30)).isoformat(),
            month_start=month_start.isoformat(),
            month_end=month_end.isoformat(),
            month_start_ch=month_start.strftime("%d.%m.%Y"),
            month_end_ch=month_end.strftime("%d.%m.%Y"),
            protected=bool(os.environ.get("APP_PASSWORD")),
        )

    @app.post("/salary-slip.pdf")
    def generate_salary():
        try:
            pdf, filename = salary_pdf(request.form)
            return document_response(pdf, filename, request.form.get("action") == "download")
        except ValueError as exc:
            return render_template("error.html", message=str(exc)), 400

    @app.post("/invoice.pdf")
    def generate_invoice():
        try:
            pdf, filename = invoice_pdf(request.form)
            return document_response(pdf, filename, request.form.get("action") == "download")
        except ValueError as exc:
            return render_template("error.html", message=str(exc)), 400

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
