from playwright.sync_api import Page, WebSocket, expect

# Makes every WebGL context request fail, the way a browser without WebGL support does
NO_WEBGL = """
delete window.WebGLRenderingContext;
delete window.WebGL2RenderingContext;
const realGetContext = HTMLCanvasElement.prototype.getContext;
HTMLCanvasElement.prototype.getContext = function (type, ...rest) {
    if (typeof type === "string" && type.toLowerCase().includes("webgl")) {
        return null;
    }
    return realGetContext.call(this, type, ...rest);
};
"""


def test_page_loads(live_server_url: str, page: Page) -> None:
    page.goto(live_server_url)
    expect(page.locator("#map")).to_be_visible()
    expect(page.locator("#connect-button")).to_be_visible()
    expect(page.locator("#receiver-status")).to_be_visible()
    expect(page.locator("#webgl-error")).to_be_hidden()


def test_webgl_error_shown_without_webgl(live_server_url: str, page: Page) -> None:
    sockets: list[WebSocket] = []
    page.on("websocket", lambda ws: sockets.append(ws))
    page.add_init_script(NO_WEBGL)

    page.goto(live_server_url)

    error = page.locator("#webgl-error")
    expect(error).to_be_visible()
    expect(error).to_contain_text("WebGL")
    expect(error).to_contain_text("browser")

    # the page stays inert - no connection is attempted (the other tests show that a
    # working page connects well within this window)
    page.wait_for_timeout(2000)
    assert not sockets, f"page opened websockets without WebGL: {[ws.url for ws in sockets]}"


def test_websockets_connect(live_server_url: str, page: Page) -> None:
    page.goto(live_server_url)
    expect(page.locator("#odid-status")).to_contain_text("Connected", timeout=5000)
    expect(page.locator("#heartbeat-status")).to_contain_text("Connected", timeout=5000)
