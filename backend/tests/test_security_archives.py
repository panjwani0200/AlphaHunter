from datetime import date

from fastapi.testclient import TestClient

from app.collectors.nse.security_archives import NseSecurityArchiveCollector
from app.main import create_app


def test_security_archive_csv_parser() -> None:
    collector = NseSecurityArchiveCollector()
    csv_text = """SYMBOL,SERIES,DATE,PREV CLOSE,OPEN PRICE,HIGH PRICE,LOW PRICE,LAST PRICE,CLOSE PRICE,VWAP,TOTAL TRADED QUANTITY,TURNOVER ₹,NO. OF TRADES,DELIVERABLE QTY,% DLY QT TO TRADED QTY
RELIANCE,EQ,24-Jun-2026,1309.50,1305.70,1322.00,1297.50,1313.40,1313.60,1312.24,"1,10,30,917","14,47,51,76,030.90","1,81,859","60,21,744",54.59
"""

    records = collector._parse_csv(csv_text)

    assert len(records) == 1
    assert records[0].symbol == "RELIANCE"
    assert records[0].trade_date == date(2026, 6, 24)
    assert records[0].deliverable_quantity == 6021744
    assert records[0].delivery_to_traded_percent == 54.59


def test_security_archive_endpoint_returns_records() -> None:
    client = TestClient(create_app())

    response = client.get("/api/market/security-archives?symbol=RELIANCE&range=1M")

    assert response.status_code == 200
    records = response.json()
    assert records
    assert records[0]["symbol"] == "RELIANCE"
    assert "delivery_to_traded_percent" in records[0]
