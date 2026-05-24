from playwright.sync_api import Page, expect


def test_page_loads(live_server_url: str, page: Page) -> None:
    page.goto(live_server_url)
    expect(page.locator("#map")).to_be_visible()
    expect(page.locator("#connect-button")).to_be_visible()
    expect(page.locator("#receiver-status")).to_be_visible()


def test_websockets_connect(live_server_url: str, page: Page) -> None:
    page.goto(live_server_url)
    expect(page.locator("#odid-status")).to_contain_text("Connected", timeout=5000)
    expect(page.locator("#heartbeat-status")).to_contain_text("Connected", timeout=5000)
