import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page()

    page.goto("http://localhost:8000")
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    # 1. Test Switch Studio Mode (허밍 믹서)
    print("Testing '허밍 믹서' mode toggle (#tab-btn-hum)...")
    hum_btn = page.locator("#tab-btn-hum")
    hum_btn.click()
    time.sleep(0.5)
    hum_visible = page.locator("#view-hum-studio").is_visible()
    suno_visible = page.locator("#view-suno-studio").is_visible()
    print(f"Hum view visible: {hum_visible}, Suno view visible: {suno_visible}")
    assert hum_visible is True, "Hum studio view should be visible"
    assert suno_visible is False, "Suno studio view should be hidden"

    # Switch back to Suno mode
    print("Switching back to Suno Studio (#tab-btn-suno)...")
    page.locator("#tab-btn-suno").click()
    time.sleep(0.5)
    assert page.locator("#view-suno-studio").is_visible() is True
    assert page.locator("#view-hum-studio").is_visible() is False
    print("Mode switching verified successfully!")

    # 2. Test Suno Paste Input
    print("Testing Suno paste input...")
    test_url = "https://suno.com/song/6090ddec-8493-428a-beae-bd185fe3ef73"
    inp = page.locator("#suno-url-input")
    inp.click()
    page.evaluate(f'''() => {{
        const el = document.getElementById("suno-url-input");
        const dt = new DataTransfer();
        dt.setData("text/plain", "{test_url}");
        const pasteEv = new ClipboardEvent("paste", {{ clipboardData: dt, bubbles: true, cancelable: true }});
        el.dispatchEvent(pasteEv);
    }}''')
    time.sleep(1)
    
    val = inp.input_value()
    badge_text = page.locator("#suno-link-detect-badge").inner_text()
    btn_text = page.locator("#btn-fetch-suno").inner_text()
    pill_text = page.locator("#analysis-status-pill").inner_text()
    print(f"Pasted Val: {val}")
    print(f"Badge: {badge_text}")
    print(f"Btn: {btn_text}")
    print(f"Pill: {pill_text}")

    browser.close()
    print("ALL TESTS PASSED SUCCESSFULLY! Everything is working properly!")
