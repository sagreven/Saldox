// Exporteert rapport.html naar rapport.pdf (A4) met Playwright/Chromium.
// Gebruik: node render_pdf.js <rapport.html> <rapport.pdf> "<voettekst>"
const path = require('path');
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const [inHtml, outPdf, titel] = process.argv.slice(2);
  await page.goto('file://' + path.resolve(inHtml), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const shots = process.argv.indexOf('--shots');
  if (shots > -1) {
    const dir = process.argv[shots + 1];
    for (const [w, name] of [[1280, 'desktop'], [390, 'mobiel']]) {
      await page.setViewportSize({ width: w, height: 900 });
      await page.screenshot({ path: path.join(dir, name + '.png'), fullPage: true });
    }
  }
  await page.emulateMedia({ media: 'print' });
  await page.pdf({
    path: path.resolve(outPdf),
    format: 'A4',
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate:
      '<div style="width:100%;font:600 7.5pt Inter,Arial,sans-serif;color:#4a5a52;padding:0 13mm;display:flex;justify-content:space-between">' +
      '<span><span style="color:#0b3d2e">Saldox</span> · ' + titel + '</span>' +
      '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>',
  });
  await browser.close();
  console.log('geschreven: ' + outPdf);
})().catch(e => { console.error(e); process.exit(1); });
