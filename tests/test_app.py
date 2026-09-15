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
            "remuneration_mode": "global",
            "global_description": "Entraînement",
            "hours": "13.3",
            "hourly_rate": "50",
            "tax_exempt_amount": "0",
            "deductions_enabled": "1",
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
    assert "42.57 CHF" in text
    assert "622.43 CHF" in text


def test_salary_deductions_use_cents_and_exclude_exempt_pay():
    client = app.test_client()
    response = client.post(
        "/salary-slip.pdf",
        data={
            "trainer_name": "Camille Exemple",
            "birth_date": "12.04.1990",
            "period_start": "2026-09-01",
            "period_end": "2026-09-30",
            "remuneration_mode": "global",
            "hours": "8.5",
            "hourly_rate": "50",
            "tax_exempt_description": "Remboursement de frais",
            "tax_exempt_amount": "100",
            "deductions_enabled": "1",
            "avs_rate": "5.3",
            "unemployment_rate": "0",
            "accident_rate": "0",
            "lpp_rate": "0",
            "withholding_rate": "0",
            "extra_deduction_rate": "0",
        },
    )
    assert response.status_code == 200
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(response.data)).pages)
    assert "Date de naissance: 12.04.1990" in text
    assert "Remboursement de frais (exonéré)" in text
    assert "425.00 CHF" in text
    assert "22.53 CHF" in text
    assert "525.00 CHF" in text
    assert "502.47 CHF" in text


def test_salary_detailed_activities_and_disabled_deductions():
    client = app.test_client()
    response = client.post(
        "/salary-slip.pdf",
        data={
            "trainer_name": "Camille Exemple",
            "period_start": "01.09.2026",
            "period_end": "30.09.2026",
            "remuneration_mode": "detailed",
            "activity_description[]": ["Entraînement enfants", "Formation adultes"],
            "activity_hours[]": ["4.5", "3"],
            "activity_rate[]": ["50", "60"],
            "tax_exempt_amount": "0",
            "deductions_enabled": "0",
            "avs_rate": "5.3",
            "unemployment_rate": "1.1",
        },
    )
    assert response.status_code == 200
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(response.data)).pages)
    assert "Période du 01.09.2026 au 30.09.2026" in text
    assert "Entraînement enfants" in text
    assert "Formation adultes" in text
    assert "405.00 CHF" in text
    assert "0.00 CHF" in text


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
