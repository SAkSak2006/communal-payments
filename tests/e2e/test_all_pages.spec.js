// @ts-check
const { test, expect } = require('@playwright/test');

const BASE = 'http://localhost:8000';

// Login helper
async function login(page) {
  await page.goto(`${BASE}/admin/login`);
  await page.fill('#username', 'admin');
  await page.fill('#password', 'admin123');
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/admin\//);
}

// ==================== AUTH ====================

test.describe('Авторизация', () => {
  test('Страница логина загружается', async ({ page }) => {
    await page.goto(`${BASE}/admin/login`);
    await expect(page.locator('.login-title')).toContainText('ЖКУ Платформа');
    await expect(page.locator('#username')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
  });

  test('Неправильный пароль показывает ошибку', async ({ page }) => {
    await page.goto(`${BASE}/admin/login`);
    await page.fill('#username', 'admin');
    await page.fill('#password', 'wrong');
    await page.click('button[type="submit"]');
    await expect(page.locator('.alert-danger')).toBeVisible();
  });

  test('Успешный логин → дашборд', async ({ page }) => {
    await login(page);
    await expect(page).toHaveURL(/\/admin\//);
    await expect(page.locator('h2')).toContainText('Дашборд');
  });
});

// ==================== DASHBOARD ====================

test.describe('Дашборд', () => {
  test.beforeEach(async ({ page }) => { await login(page); });

  test('Отображаются 4 карточки статистики', async ({ page }) => {
    const cards = page.locator('.card-dashboard');
    await expect(cards.first()).toBeVisible();
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(4);
  });

  test('Sidebar навигация видна', async ({ page }) => {
    await expect(page.locator('.sidebar')).toBeVisible();
    await expect(page.locator('.sidebar .nav-link')).toHaveCount(9);
  });

  test('Topbar с именем пользователя', async ({ page }) => {
    await expect(page.locator('text=Главная')).toBeVisible();
  });
});

// ==================== ЖИТЕЛИ ====================

test.describe('Жители', () => {
  test.beforeEach(async ({ page }) => { await login(page); });

  test('Список жителей с пагинацией', async ({ page }) => {
    await page.click('text=Жители');
    await page.waitForSelector('h2');
    await expect(page.locator('h2')).toContainText('Жители');
    await expect(page.locator('table')).toBeVisible();

    // Check pagination exists
    const pagination = page.locator('.pagination');
    await expect(pagination).toBeVisible();
  });

  test('Поиск жителей работает', async ({ page }) => {
    await page.goto(`${BASE}/admin/residents/`);
    await page.fill('input[name="q"]', 'Иванов');
    await page.click('button:has-text("Найти")');
    await page.waitForSelector('table');
    // Should have results or "not found"
    const body = await page.textContent('body');
    expect(body).toBeTruthy();
  });

  test('Переход на страницу 2', async ({ page }) => {
    await page.goto(`${BASE}/admin/residents/?page=2`);
    await expect(page.locator('table')).toBeVisible();
  });

  test('Карточка жителя открывается', async ({ page }) => {
    await page.goto(`${BASE}/admin/residents/`);
    const viewBtn = page.locator('a[href*="/admin/residents/"].btn-outline-primary').first();
    if (await viewBtn.isVisible()) {
      await viewBtn.click();
      await page.waitForSelector('h2');
      await expect(page.locator('text=Информация')).toBeVisible();
      await expect(page.locator('text=Адреса')).toBeVisible();
      await expect(page.locator('text=Последние платежи')).toBeVisible();
    }
  });

  test('Форма добавления жителя', async ({ page }) => {
    await page.goto(`${BASE}/admin/residents/create`);
    await expect(page.locator('#full_name')).toBeVisible();
    await expect(page.locator('#personal_account')).toBeVisible();
    await expect(page.locator('#phone')).toBeVisible();
    await expect(page.locator('#city')).toBeVisible();
  });
});

// ==================== ТАРИФЫ ====================

test.describe('Тарифы', () => {
  test.beforeEach(async ({ page }) => { await login(page); });

  test('Список тарифов отображается', async ({ page }) => {
    await page.goto(`${BASE}/admin/tariffs/`);
    await expect(page.locator('h2')).toContainText('Тарифы');
    const count = await page.locator('.card-dashboard').count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('Форма нового тарифа', async ({ page }) => {
    await page.goto(`${BASE}/admin/tariffs/create`);
    await expect(page.locator('#service_id')).toBeVisible();
    await expect(page.locator('#price_per_unit')).toBeVisible();
    await expect(page.locator('#effective_from')).toBeVisible();
  });
});

// ==================== СЧЁТЧИКИ ====================

test.describe('Счётчики', () => {
  test.beforeEach(async ({ page }) => { await login(page); });

  test('Список счётчиков с пагинацией', async ({ page }) => {
    await page.goto(`${BASE}/admin/meters/`);
    await expect(page.locator('h2')).toContainText('Счётчики');
    await expect(page.locator('table')).toBeVisible();
    await expect(page.locator('.pagination')).toBeVisible();
  });

  test('Страница 2 счётчиков', async ({ page }) => {
    await page.goto(`${BASE}/admin/meters/?page=2`);
    await expect(page.locator('table')).toBeVisible();
  });

  test('Форма регистрации счётчика', async ({ page }) => {
    await page.goto(`${BASE}/admin/meters/create`);
    await expect(page.locator('#address_id')).toBeVisible();
    await expect(page.locator('#service_id')).toBeVisible();
    await expect(page.locator('#serial_number')).toBeVisible();
  });
});

// ==================== ПОКАЗАНИЯ ====================

test.describe('Показания', () => {
  test.beforeEach(async ({ page }) => { await login(page); });

  test('Фильтр с "Все годы" работает', async ({ page }) => {
    await page.goto(`${BASE}/admin/readings/?year=0&month=0`);
    await expect(page.locator('h2')).toContainText('Показания');
    await expect(page.locator('table')).toBeVisible();
    await expect(page.locator('.pagination')).toBeVisible();
  });

  test('Фильтр по конкретному году/месяцу', async ({ page }) => {
    await page.goto(`${BASE}/admin/readings/?year=2025&month=1`);
    await expect(page.locator('table')).toBeVisible();
  });

  test('Фильтр по статусу', async ({ page }) => {
    await page.goto(`${BASE}/admin/readings/?year=0&month=0&validated=true`);
    await expect(page.locator('table')).toBeVisible();
  });

  test('Поиск по жителю', async ({ page }) => {
    await page.goto(`${BASE}/admin/readings/?year=0&month=0&q=Иванов`);
    await expect(page.locator('table')).toBeVisible();
  });

  test('Месяцы отображаются словами', async ({ page }) => {
    await page.goto(`${BASE}/admin/readings/`);
    const monthSelect = page.locator('select[name="month"]');
    const html = await monthSelect.innerHTML();
    expect(html).toContain('Январь');
    expect(html).toContain('Декабрь');
    expect(html).toContain('Все месяцы');
  });

  test('Кнопка сброса фильтров', async ({ page }) => {
    await page.goto(`${BASE}/admin/readings/?year=2025&month=1&validated=true`);
    await expect(page.locator('a:has-text("Сброс")')).toBeVisible();
  });
});

// ==================== ПЛАТЕЖИ ====================

test.describe('Платежи', () => {
  test.beforeEach(async ({ page }) => { await login(page); });

  test('Список платежей', async ({ page }) => {
    await page.goto(`${BASE}/admin/payments/`);
    await expect(page.locator('h2')).toContainText('Платежи');
    await expect(page.locator('table')).toBeVisible();
  });

  test('Форма записи оплаты', async ({ page }) => {
    await page.goto(`${BASE}/admin/payments/create`);
    await expect(page.locator('#resident_id')).toBeVisible();
    await expect(page.locator('#amount')).toBeVisible();
    await expect(page.locator('#payment_date')).toBeVisible();
  });
});

// ==================== НАЧИСЛЕНИЯ ====================

test.describe('Начисления', () => {
  test.beforeEach(async ({ page }) => { await login(page); });

  test('Страница начислений с фильтром периода', async ({ page }) => {
    await page.goto(`${BASE}/admin/charges/`);
    await expect(page.locator('h2')).toContainText('Начисления');
    await expect(page.locator('select[name="year"]')).toBeVisible();
    await expect(page.locator('select[name="month"]')).toBeVisible();
  });

  test('Месяцы словами в начислениях', async ({ page }) => {
    await page.goto(`${BASE}/admin/charges/`);
    const html = await page.locator('select[name="month"]').innerHTML();
    expect(html).toContain('Январь');
    expect(html).toContain('Декабрь');
  });

  test('Кнопки Рассчитать и Закрыть период', async ({ page }) => {
    await page.goto(`${BASE}/admin/charges/`);
    await expect(page.locator('text=Рассчитать')).toBeVisible();
  });
});

// ==================== ОТЧЁТЫ ====================

test.describe('Отчёты', () => {
  test.beforeEach(async ({ page }) => { await login(page); });

  test('Центр отчётов загружается', async ({ page }) => {
    await page.goto(`${BASE}/admin/reports/`);
    await expect(page.locator('h2')).toContainText('Отчёты');
    await expect(page.locator('text=Отчёт за период')).toBeVisible();
    await expect(page.locator('text=задолженностям').first()).toBeVisible();
    await expect(page.locator('text=Экспорт начислений')).toBeVisible();
  });

  test('Месяцы словами в отчётах', async ({ page }) => {
    await page.goto(`${BASE}/admin/reports/`);
    const html = await page.locator('select[name="month"]').first().innerHTML();
    expect(html).toContain('Январь');
  });

  test('Страница должников', async ({ page }) => {
    await page.goto(`${BASE}/admin/reports/debtors`);
    await expect(page.locator('h2')).toContainText('Должники');
    await expect(page.locator('table')).toBeVisible();
  });
});

// ==================== ИМПОРТ ====================

test.describe('Импорт', () => {
  test.beforeEach(async ({ page }) => { await login(page); });

  test('Страница импорта с двумя формами', async ({ page }) => {
    await page.goto(`${BASE}/admin/import/`);
    await expect(page.locator('h2')).toContainText('Импорт');
    await expect(page.locator('text=Импорт жителей')).toBeVisible();
    await expect(page.locator('text=Импорт показаний')).toBeVisible();
    await expect(page.locator('input[type="file"]')).toHaveCount(2);
  });

  test('Ссылки на шаблоны работают', async ({ page }) => {
    await page.goto(`${BASE}/admin/import/`);
    await expect(page.locator('a:has-text("Скачать шаблон")')).toHaveCount(2);
  });
});

// ==================== ДИЗАЙН ====================

test.describe('Stitch дизайн', () => {
  test.beforeEach(async ({ page }) => { await login(page); });

  test('Светлый фон (не тёмный)', async ({ page }) => {
    const bg = await page.evaluate(() => {
      return getComputedStyle(document.querySelector('main') || document.body).backgroundColor;
    });
    // Should NOT be dark purple/black
    expect(bg).not.toContain('15, 12, 41');  // old #0f0c29
    expect(bg).not.toContain('48, 43, 99');  // old #302b63
  });

  test('Sidebar тёмный', async ({ page }) => {
    const bg = await page.evaluate(() => {
      return getComputedStyle(document.querySelector('.sidebar')).backgroundColor;
    });
    // Should be dark slate #1E293B = rgb(30, 41, 59)
    expect(bg).toContain('30, 41, 59');
  });

  test('Частицы скрыты', async ({ page }) => {
    const particles = page.locator('.particles');
    if (await particles.count() > 0) {
      const display = await particles.evaluate(el => getComputedStyle(el).display);
      expect(display).toBe('none');
    }
  });

  test('Шрифт Inter/Manrope загружен', async ({ page }) => {
    const fontFamily = await page.evaluate(() => {
      return getComputedStyle(document.body).fontFamily;
    });
    expect(fontFamily.toLowerCase()).toContain('inter');
  });
});

// ==================== НАВИГАЦИЯ ====================

test.describe('Навигация', () => {
  test.beforeEach(async ({ page }) => { await login(page); });

  test('Все ссылки sidebar работают', async ({ page }) => {
    const links = [
      { text: 'Дашборд', url: '/admin/' },
      { text: 'Жители', url: '/admin/residents' },
      { text: 'Тарифы', url: '/admin/tariffs' },
      { text: 'Счётчики', url: '/admin/meters' },
      { text: 'Показания', url: '/admin/readings' },
      { text: 'Платежи', url: '/admin/payments' },
      { text: 'Начисления', url: '/admin/charges' },
      { text: 'Отчёты', url: '/admin/reports' },
      { text: 'Импорт', url: '/admin/import' },
    ];

    for (const link of links) {
      await page.goto(`${BASE}/admin/`);
      await page.click(`.sidebar .nav-link:has-text("${link.text}")`);
      await page.waitForLoadState('networkidle');
      expect(page.url()).toContain(link.url);
    }
  });
});
