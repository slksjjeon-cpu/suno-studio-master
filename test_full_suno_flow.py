from playwright.sync_api import sync_playwright
import time

test_url = "https://suno.com/song/6090ddec-8493-428a-beae-bd185fe3ef73"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page()
    
    # Listen to console messages
    page.on("console", lambda msg: print(f"[BROWSER CONSOLE {msg.type}]: {msg.text}"))
    page.on("pageerror", lambda exc: print(f"[BROWSER PAGE ERROR]: {exc}"))
    page.on("dialog", lambda dialog: (print(f"[BROWSER DIALOG {dialog.type}]: {dialog.message}"), dialog.accept()))

    print("Navigating to http://localhost:8000 ...")
    page.goto("http://localhost:8000")
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    print("Filling Suno URL and pressing Enter...")
    inp = page.locator("#suno-url-input")
    inp.fill(test_url)
    inp.press("Enter")

    # Now monitor for up to 45 seconds to see what happens
    start = time.time()
    while time.time() - start < 45:
        btn_text = page.locator("#btn-fetch-suno").inner_text()
        pill_text = page.locator("#analysis-status-pill").inner_text()
        wf_step = page.evaluate("() => typeof state !== 'undefined' ? state.workflowStep : 'no-state'")
        audio_src = page.evaluate("() => typeof state !== 'undefined' && state.audio ? state.audio.url : 'none'")
        print(f"[{int(time.time() - start)}s] pill: '{pill_text}' | btn: '{btn_text}' | step: {wf_step} | audio: {audio_src}")
        
        if wf_step == 3 or wf_step == 2:
            print("Successfully transitioned step:", wf_step)
            break
        time.sleep(2)

    browser.close()
