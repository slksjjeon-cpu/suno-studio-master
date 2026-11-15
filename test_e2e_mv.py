import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import time
import os
from playwright.sync_api import sync_playwright

test_url = "https://suno.com/song/6090ddec-8493-428a-beae-bd185fe3ef73"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page()

    page.on("console", lambda msg: print(f"[CONSOLE {msg.type}]: {msg.text}"))
    page.on("pageerror", lambda exc: print(f"[PAGE ERROR]: {exc}"))

    print("1. Navigating to http://localhost:8000 ...")
    page.goto("http://localhost:8000")
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    print("2. Importing Suno track...")
    inp = page.locator("#suno-url-input")
    inp.fill(test_url)
    inp.press("Enter")

    print("Waiting for Suno audio import and analysis to finish...")
    for _ in range(30):
        time.sleep(1)
        has_audio = page.evaluate("() => typeof state !== 'undefined' && state.audio !== null")
        if has_audio:
            print("Audio loaded in state!")
            break

    time.sleep(1)

    print("3. Opening AI Music Video Studio Modal (#btn-open-mv-modal)...")
    page.locator("#btn-open-mv-modal").click()
    time.sleep(0.5)
    modal_visible = page.locator("#modal-mv-studio").is_visible()
    print(f"Modal visible: {modal_visible}")
    assert modal_visible is True, "MV Studio modal must be visible"

    print("4. Selecting K-POP Cyberpunk style and 4 scenes...")
    page.evaluate("() => selectMvStyle('kpop_cyberpunk')")
    page.locator("#mv-scene-count").select_option("4")
    page.locator("#mv-concept-input").fill("네오 서울 비 내리는 밤거리와 네온 레이저 화려한 무대")

    print("5. Planning storyboard (#btn-plan-mv)...")
    page.locator("#btn-plan-mv").click()

    # Wait for storyboard to generate
    for _ in range(30):
        time.sleep(1)
        scenes_count = page.evaluate("() => typeof mvState !== 'undefined' && mvState.storyboard ? mvState.storyboard.scenes.length : 0")
        if scenes_count > 0:
            print(f"Storyboard generated with {scenes_count} scenes!")
            break

    # Verify scene elements in DOM
    cards_count = page.locator("#mv-scenes-container > div").count()
    print(f"Rendered scene cards in DOM: {cards_count}")
    assert cards_count == 4, f"Expected 4 scene cards, found {cards_count}"

    for i in range(cards_count):
        motion = page.evaluate(f"() => mvState.storyboard.scenes[{i}].camera_motion")
        lyric = page.evaluate(f"() => mvState.storyboard.scenes[{i}].lyric_text")
        print(f"  Scene #{i+1}: motion='{motion}', lyric='{lyric}'")

    print("6. Starting MP4 slideshow animation & dissolve rendering (#btn-start-mv-render)...")
    page.locator("#mv-range-select").select_option("section")
    page.locator("#btn-start-mv-render").click()

    print("Waiting for MP4 rendering to complete...")
    completed = False
    for i in range(60):
        time.sleep(2)
        stage = page.locator("#mv-progress-stage").inner_text()
        pct = page.locator("#mv-progress-percent").inner_text()
        print(f"[{i*2}s] Progress: {pct} | Stage: {stage}")

        is_done = page.evaluate("() => document.getElementById('mv-result-box')?.classList.contains('hidden') === false")
        if is_done:
            video_src = page.evaluate("() => document.getElementById('mv-result-video')?.src")
            print(f"SUCCESS! Video rendered at: {video_src}")
            completed = True
            break

    assert completed is True, "Video rendering should complete within timeout"

    browser.close()
    print("ALL END-TO-END TESTS COMPLETED SUCCESSFULLY!")
