import { chromium } from 'playwright';

const logs = [];
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();

page.on('console', (msg) => {
  logs.push({ type: msg.type(), text: msg.text() });
});
page.on('pageerror', (err) => {
  logs.push({ type: 'pageerror', text: err.message });
});

try {
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);
} catch (e) {
  logs.push({ type: 'navigation', text: String(e) });
}

const errors = logs.filter((l) => l.type === 'pageerror' || l.type === 'error');
console.log(JSON.stringify({ url: page.url(), errorCount: errors.length, errors, sample: logs.slice(0, 15) }, null, 2));
await browser.close();
