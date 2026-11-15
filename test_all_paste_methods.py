from playwright.sync_api import sync_playwright
import time

test_url = "https://suno.com/song/6090ddec-8493-428a-beae-bd185fe3ef73"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    
    # Test 1: Paste directly into input box
    print("--- TEST 1: Paste into input box ---")
    page = browser.new_page()
    page.goto("http://localhost:8000")
    time.sleep(1)
    
    inp = page.locator("#suno-url-input")
    inp.click()
    page.evaluate(f'''() => {{
        const el = document.getElementById("suno-url-input");
        const dt = new DataTransfer();
        dt.setData("text/plain", "{test_url}");
        const ev = new ClipboardEvent("paste", {{ clipboardData: dt, bubbles: true, cancelable: true }});
        el.dispatchEvent(ev);
    }}''')
    time.sleep(1)
    val = inp.input_value()
    btn_text = page.locator("#btn-fetch-suno").inner_text()
    print(f"Test 1 result: val='{val}' | btn='{btn_text}'")
    page.close()

    # Test 2: Typing/Filling into input box and clicking '바로 마스터링'
    print("--- TEST 2: Click 바로 마스터링 button ---")
    page = browser.new_page()
    page.goto("http://localhost:8000")
    time.sleep(1)
    
    inp = page.locator("#suno-url-input")
    inp.fill(test_url)
    btn = page.locator("#btn-fetch-suno")
    btn.click()
    time.sleep(1)
    btn_text = btn.inner_text()
    pill_text = page.locator("#analysis-status-pill").inner_text()
    print(f"Test 2 result: btn='{btn_text}' | pill='{pill_text}'")
    page.close()

    # Test 3: Pressing Enter in input box
    print("--- TEST 3: Press Enter in input box ---")
    page = browser.new_page()
    page.goto("http://localhost:8000")
    time.sleep(1)
    
    inp = page.locator("#suno-url-input")
    inp.fill(test_url)
    inp.press("Enter")
    time.sleep(1)
    btn_text = page.locator("#btn-fetch-suno").inner_text()
    pill_text = page.locator("#analysis-status-pill").inner_text()
    print(f"Test 3 result: btn='{btn_text}' | pill='{pill_text}'")
    page.close()

    # Test 4: Global paste anywhere on page
    print("--- TEST 4: Global paste anywhere on page ---")
    page = browser.new_page()
    page.goto("http://localhost:8000")
    time.sleep(1)
    
    page.evaluate(f'''() => {{
        const dt = new DataTransfer();
        dt.setData("text/plain", "{test_url}");
        const ev = new ClipboardEvent("paste", {{ clipboardData: dt, bubbles: true, cancelable: true }});
        window.dispatchEvent(ev);
    }}''')
    time.sleep(1)
    val = page.locator("#suno-url-input").input_value()
    btn_text = page.locator("#btn-fetch-suno").inner_text()
    pill_text = page.locator("#analysis-status-pill").inner_text()
    print(f"Test 4 result: val='{val}' | btn='{btn_text}' | pill='{pill_text}'")
    page.close()

    # Test 5: Click clipboard button
    print("--- TEST 5: Click clipboard button ---")
    page = browser.new_page()
    page.goto("http://localhost:8000")
    time.sleep(1)
    
    cb_btn = page.locator("#btn-paste-clipboard")
    cb_btn.click()
    time.sleep(1)
    val = page.locator("#suno-url-input").input_value()
    print(f"Test 5 result: val='{val}'")
    page.close()

    browser.close()
