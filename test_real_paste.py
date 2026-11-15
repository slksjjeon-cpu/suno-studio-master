import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.sync_api import sync_playwright
import time

test_url = "https://suno.com/song/6090ddec-8493-428a-beae-bd185fe3ef73"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page()

    page.on("console", lambda msg: print(f"[CONSOLE {msg.type}]: {msg.text}"))
    page.on("pageerror", lambda exc: print(f"[PAGE ERROR]: {exc}"))
    page.on("dialog", lambda d: (print(f"[DIALOG {d.type}]: {d.message}"), d.accept()))

    page.goto("http://localhost:8000")
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    print("--- Simulating User Pasting into #suno-url-input ---")
    inp = page.locator("#suno-url-input")
    inp.click()

    # Dispatch native paste event as a real browser would:
    page.evaluate(f'''() => {{
        const el = document.getElementById("suno-url-input");
        const dt = new DataTransfer();
        dt.setData("text/plain", "{test_url}");
        const pasteEv = new ClipboardEvent("paste", {{ clipboardData: dt, bubbles: true, cancelable: true }});
        el.dispatchEvent(pasteEv);
    }}''')

    time.sleep(0.5)
    val = inp.input_value()
    print(f"Input value right after paste: '{val}'")

    for i in range(30):
        time.sleep(1)
        val = inp.input_value()
        btn = page.locator("#btn-fetch-suno").inner_text()
        pill = page.locator("#analysis-status-pill").inner_text()
        badge = page.locator("#suno-link-detect-badge").inner_text()
        active_job = page.evaluate("() => document.getElementById('active-job-box')?.classList.contains('hidden') === false")
        job_msg = page.evaluate("() => document.getElementById('active-job-msg')?.innerText")
        cards = page.evaluate("() => document.querySelectorAll('#completed-drafts-list > div').length")
        step = page.evaluate("() => typeof state !== 'undefined' ? state.currentStep : -1")
        print(f"[{i}s] step={step} | val='{val[:30]}...' | btn='{btn}' | pill='{pill}' | badge='{badge}' | jobActive={active_job} ('{job_msg}') | cards={cards}")
        if cards > 0:
            print("SUCCESS! Completed cards rendered:", cards)
            break

    browser.close()
