import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from playwright.sync_api import sync_playwright

class PlaywrightScraper:
    def __init__(self):
        self.base_url = "https://www.nseindia.com/option-chain"
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--disable-http2"]
        )
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            window.chrome = {
                runtime: {}
            };
        """)
        self.page = self.context.new_page()
        try:
            self.page.goto(self.base_url, wait_until="load", timeout=15000)
            self.page.wait_for_timeout(3000)
        except Exception:
            pass

    def stop(self):
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass

    def fetch(self, url: str) -> str:
        if not self.context:
            self.start()
        
        if url.startswith("/"):
            url = f"https://www.nseindia.com{url}"
        
        try:
            # First ensure we are at the base URL to get cookies
            if not self.page.url.startswith("https://www.nseindia.com"):
                try:
                    self.page.goto(self.base_url, wait_until="load", timeout=15000)
                    self.page.wait_for_timeout(3000)
                except Exception:
                    pass
            
            # Execute fetch inside page context to inherit active cookies/headers and bypass Cloudflare
            text = self.page.evaluate("""async (targetUrl) => {
                const response = await fetch(targetUrl);
                if (!response.ok) {
                    throw new Error('HTTP error ' + response.status);
                }
                return await response.text();
            }""", url)
            return text
        except Exception as e:
            try:
                # Force refresh base page and try once more
                self.page.goto(self.base_url, wait_until="load", timeout=15000)
                self.page.wait_for_timeout(3000)
                text = self.page.evaluate("""async (targetUrl) => {
                    const response = await fetch(targetUrl);
                    if (!response.ok) {
                        throw new Error('HTTP error ' + response.status);
                    }
                    return await response.text();
                }""", url)
                return text
            except Exception as retry_err:
                raise RuntimeError(f"Scraper failed: {retry_err}") from e

scraper = PlaywrightScraper()

class ScraperHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == "/fetch":
            query_params = urllib.parse.parse_qs(parsed_url.query)
            urls = query_params.get("url", [])
            if not urls:
                self.send_error_response("Missing url parameter")
                return
                
            target_url = urls[0]
            try:
                text = scraper.fetch(target_url)
                self.send_success_response(text)
            except Exception as e:
                self.send_error_response(str(e))
        else:
            self.send_response(404)
            self.end_headers()

    def send_success_response(self, data_str: str):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {"ok": True, "data": data_str}
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def send_error_response(self, err_msg: str):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {"ok": False, "error": err_msg}
        self.wfile.write(json.dumps(response).encode("utf-8"))

def run():
    scraper.start()
    server_address = ("127.0.0.1", 8001)
    httpd = HTTPServer(server_address, ScraperHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        scraper.stop()

if __name__ == "__main__":
    run()
