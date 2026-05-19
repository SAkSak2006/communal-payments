# -*- coding: utf-8 -*-
import sys
import os
import time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright, Page

BASE_URL = "http://localhost:8000"
OUT_DIR = Path("screenshots")
OUT_DIR.mkdir(exist_ok=True)

VIEWPORT = {"width": 1440, "height": 900}


def login(page: Page, username: str, password: str):
    page.goto(f"{BASE_URL}/admin/login")
    page.wait_for_load_state("networkidle")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def shot(page: Page, filename: str, selector: str | None = None):
    path = str(OUT_DIR / filename)
    if selector:
        el = page.locator(selector)
        el.screenshot(path=path)
    else:
        page.screenshot(path=path, full_page=False)
    print(f"  ✓ {filename}")


def operator_screenshots(page: Page):
    print("\n[ОПЕРАТОР] Вход...")
    login(page, "operator", "operator123")

    # В.18 — Список показаний
    page.goto(f"{BASE_URL}/admin/readings/")
    page.wait_for_load_state("networkidle")
    shot(page, "B18_operator_readings_list.png")

    # В.19 — Форма добавления показания
    page.goto(f"{BASE_URL}/admin/readings/create")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    shot(page, "B19_operator_readings_form.png")

    # В.20 — Список платежей
    page.goto(f"{BASE_URL}/admin/payments/")
    page.wait_for_load_state("networkidle")
    shot(page, "B20_operator_payments_list.png")

    # В.21 — Форма добавления платежа
    page.goto(f"{BASE_URL}/admin/payments/create")
    page.wait_for_load_state("networkidle")
    shot(page, "B21_operator_payments_form.png")


def admin_screenshots(page: Page):
    print("\n[АДМИН] Вход...")
    login(page, "admin", "admin123")

    # Дашборд
    page.goto(f"{BASE_URL}/admin/")
    page.wait_for_load_state("networkidle")
    shot(page, "admin_dashboard.png")

    # Жильцы
    page.goto(f"{BASE_URL}/admin/residents/")
    page.wait_for_load_state("networkidle")
    shot(page, "admin_residents.png")

    # Счётчики
    page.goto(f"{BASE_URL}/admin/meters/")
    page.wait_for_load_state("networkidle")
    shot(page, "admin_meters.png")

    # Тарифы
    page.goto(f"{BASE_URL}/admin/tariffs/")
    page.wait_for_load_state("networkidle")
    shot(page, "admin_tariffs.png")

    # Начисления
    page.goto(f"{BASE_URL}/admin/charges/")
    page.wait_for_load_state("networkidle")
    shot(page, "admin_charges.png")

    # Отчёты
    page.goto(f"{BASE_URL}/admin/reports/")
    page.wait_for_load_state("networkidle")
    shot(page, "admin_reports.png")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT)
        page = context.new_page()

        operator_screenshots(page)

        # Очистить cookies перед входом под другим пользователем
        context.clear_cookies()

        admin_screenshots(page)

        browser.close()
        print(f"\nГотово! Скриншоты сохранены в папку: {OUT_DIR.resolve()}")
        print(f"Всего файлов: {len(list(OUT_DIR.glob('*.png')))}")


if __name__ == "__main__":
    main()
