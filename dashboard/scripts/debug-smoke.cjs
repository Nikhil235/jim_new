const { chromium } = require('playwright');

(async () => {
  const logs = [];
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on('console', (m) => logs.push({ type: m.type(), text: m.text() }));
  page.on('pageerror', (e) => logs.push({ type: 'pageerror', text: e.message }));
  try {
    await page.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2500);
  } catch (e) {
    logs.push({ type: 'navigation', text: String(e) });
  }
  const errors = logs.filter((l) => l.type === 'pageerror' || l.type === 'error');
  console.log(JSON.stringify({ url: page.url(), errorCount: errors.length, errors, all: logs }, null, 2));
  await browser.close();
})();
