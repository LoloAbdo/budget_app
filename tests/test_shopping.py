"""tests/test_shopping.py — Shopping price tracker: parsing + DB + alerts.

All parsing runs on saved HTML strings; no test ever hits the network.
"""
import pytest

from services import shopping_service as ss


# ── URL / currency helpers ────────────────────────────────────────────────────

@pytest.mark.parametrize("url,asin", [
    ("https://www.amazon.ca/dp/B0ABCDEFGH", "B0ABCDEFGH"),
    ("https://amazon.com/Some-Title/dp/B01234567X/ref=sr_1_1?keywords=x", "B01234567X"),
    ("https://www.amazon.ca/gp/product/B0987654ZZ", "B0987654ZZ"),
    ("https://www.amazon.ca/hz/wishlist/ls/ABC", None),
    ("not a url", None),
])
def test_asin_from_url(url, asin):
    assert ss.asin_from_url(url) == asin


@pytest.mark.parametrize("url,domain,currency", [
    ("https://www.amazon.ca/dp/B0ABCDEFGH", "amazon.ca", "CAD"),
    ("https://www.amazon.com/dp/B0ABCDEFGH", "amazon.com", "USD"),
    ("https://www.amazon.co.uk/dp/B0ABCDEFGH", "amazon.co.uk", "GBP"),
    ("https://www.amazon.fr/dp/B0ABCDEFGH", "amazon.fr", "EUR"),
    ("garbage", "amazon.ca", "CAD"),
])
def test_domain_and_currency(url, domain, currency):
    d = ss.domain_from_url(url)
    assert d == domain
    assert ss.currency_for_domain(d) == currency


def test_canonical_url_strips_junk():
    url = "https://www.amazon.ca/Some-Long-Title/dp/B0ABCDEFGH/ref=abc?tag=xyz"
    asin = ss.asin_from_url(url)
    assert ss.canonical_url(asin, ss.domain_from_url(url)) == "https://amazon.ca/dp/B0ABCDEFGH"


@pytest.mark.parametrize("text,value", [
    ("CDN$ 1,299.99", 1299.99),
    ("$19.99", 19.99),
    ("1.299,00 €", 1299.00),      # EU decimal comma
    ("19,99 €", 19.99),
    ("1,299", 1299.0),            # whole-number thousands (not 1.299)
    ("1 299,99 €", 1299.99), # French non-breaking-space thousands
    ("1,234,567.89", 1234567.89),
    ("1299", 1299.0),
    ("", None),
    ("free", None),
])
def test_parse_price_text(text, value):
    assert ss.parse_price_text(text) == value


# ── Product page parsing ──────────────────────────────────────────────────────

_PRODUCT_HTML = """
<html><body>
<span id="productTitle">   Cool Gadget 3000   </span>
<div id="corePrice_feature_div">
  <span class="a-price"><span class="a-offscreen">CDN$ 1,299.99</span></span>
</div>
</body></html>
"""

_BLOCK_HTML = "<html><body><h4>Robot Check</h4>Enter the characters you see below</body></html>"

_NOPRICE_HTML = '<html><body><span id="productTitle">No Price Item</span></body></html>'


def test_parse_product_ok():
    info = ss.parse_product(_PRODUCT_HTML, "amazon.ca")
    assert info.ok
    assert info.title == "Cool Gadget 3000"
    assert info.price == 1299.99
    assert info.currency == "CAD"


def test_parse_product_no_price():
    info = ss.parse_product(_NOPRICE_HTML, "amazon.ca")
    assert not info.ok
    assert info.title == "No Price Item"
    assert info.price is None


def test_is_blocked_html():
    assert ss.is_blocked_html(_BLOCK_HTML)
    assert not ss.is_blocked_html(_PRODUCT_HTML)


# ── Wishlist parsing ──────────────────────────────────────────────────────────

_WISHLIST_HTML = """
<ul id="g-items">
  <li data-itemid="I1">
    <a href="/dp/B0ABCDEFGH/ref=x" title="Widget A">Widget A</a>
    <span class="a-price"><span class="a-offscreen">$19.99</span></span>
  </li>
  <li data-itemid="I2">
    <a href="/gp/product/B01234567X" title="Widget B">Widget B</a>
  </li>
  <li data-itemid="I3">
    <a href="/no-product-here" title="Junk">Junk</a>
  </li>
</ul>
"""


def test_parse_wishlist():
    seeds = ss.parse_wishlist(_WISHLIST_HTML, "amazon.ca")
    asins = [s["asin"] for s in seeds]
    assert asins == ["B0ABCDEFGH", "B01234567X"]   # junk li skipped
    first = seeds[0]
    assert first["price"] == 19.99
    assert first["title"] == "Widget A"
    assert first["url"] == "https://amazon.ca/dp/B0ABCDEFGH"
    assert seeds[1]["price"] is None


# ── DB layer ──────────────────────────────────────────────────────────────────

def test_add_dedupes_by_asin(db, user_id):
    a = db.add_watched_item(user_id, "https://amazon.ca/dp/B0ABCDEFGH",
                            asin="B0ABCDEFGH", domain="amazon.ca")
    b = db.add_watched_item(user_id, "https://amazon.ca/dp/B0ABCDEFGH",
                            asin="B0ABCDEFGH", domain="amazon.ca")
    assert a == b
    assert len(db.get_watched_items(user_id)) == 1


def test_update_freezes_start_and_logs_history(db, user_id):
    iid = db.add_watched_item(user_id, "https://amazon.ca/dp/B0ABCDEFGH",
                              asin="B0ABCDEFGH")
    db.update_item_price(iid, 100.0)
    db.update_item_price(iid, 80.0)
    item = db.get_watched_items(user_id)[0]
    assert item["start_price"] == 100.0      # frozen on first success
    assert item["current_price"] == 80.0
    assert item["is_blocked"] == 0
    hist = db.get_price_history(iid)
    assert [h["price"] for h in hist] == [100.0, 80.0]


def test_price_alert_on_drop(db, user_id):
    iid = db.add_watched_item(user_id, "https://amazon.ca/dp/B0ABCDEFGH",
                              asin="B0ABCDEFGH", start_price=100.0)
    db.update_item_price(iid, 90.0)
    alerts = db.get_price_alerts(user_id)
    assert len(alerts) == 1
    assert alerts[0]["drop"] == pytest.approx(10.0)
    assert alerts[0]["drop_pct"] == pytest.approx(10.0)


def test_no_alert_when_price_rises_or_equal(db, user_id):
    iid = db.add_watched_item(user_id, "https://amazon.ca/dp/B0ABCDEFGH",
                              asin="B0ABCDEFGH", start_price=100.0)
    db.update_item_price(iid, 110.0)
    assert db.get_price_alerts(user_id) == []


def test_mark_blocked_keeps_price(db, user_id):
    iid = db.add_watched_item(user_id, "https://amazon.ca/dp/B0ABCDEFGH",
                              asin="B0ABCDEFGH")
    db.update_item_price(iid, 50.0)
    db.mark_item_blocked(iid)
    item = db.get_watched_items(user_id)[0]
    assert item["is_blocked"] == 1
    assert item["current_price"] == 50.0     # last price preserved


def test_tables_exist_on_fresh_db(db):
    names = {r["name"] for r in db._fetchall(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"watched_items", "price_history"} <= names
