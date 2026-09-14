from io import BytesIO

from pypdf import PdfReader

from app import app


def test_home_and_health():
    client = app.test_client()
    home = client.get("/")
    assert home.status_code == 200
    assert "ENTRAÎNEURS ENREGISTRÉS".encode() in home.data
    assert b"trainer-profile" in home.data
    assert client.get("/health").json == {"status": "ok"}


def test_salary_slip_matches_reference_calculation():
    client = app.test_client()
    response = client.post(
        "/salary-slip.pdf",
        data={
            "trainer_name": "Camille Exemple",
            "trainer_address": "Rue du Sport 1\n1200 Genève",
            "role": "Moniteur de tennis de table",
            "period_start": "2026-05-01",
            "period_end": "2026-05-31",
            "hours": "8.5",
            "hourly_rate": "50",
            "days": "2",
            "daily_rate": "120",
            "other_amount": "0",
            "avs_rate": "5.3",
            "unemployment_rate": "1.1",
            "accident_rate": "0",
            "lpp_rate": "0",
            "withholding_rate": "0",
            "extra_deduction_rate": "0",
        },
    )
    assert response.status_code == 200
    reader = PdfReader(BytesIO(response.data))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) == 1
    assert "665.00 CHF" in text
    assert "42.00 CHF" in text
    assert "623.00 CHF" in text


def test_invoice_total():
    client = app.test_client()
    response = client.post(
        "/invoice.pdf",
        data={
            "invoice_trainer_name": "Camille Exemple",
            "invoice_number": "202609-01",
            "issue_date": "2026-09-14",
            "due_date": "2026-10-14",
            "vat_rate": "0",
            "item_description[]": ["Cours", "Stage"],
            "item_quantity[]": ["8.5", "1"],
            "item_unit[]": ["heure", "forfait"],
            "item_rate[]": ["50", "120"],
        },
    )
    assert response.status_code == 200
    text = PdfReader(BytesIO(response.data)).pages[0].extract_text()
    assert "545.00 CHF" in text
