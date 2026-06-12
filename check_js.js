const fs = require('fs');
const html = fs.readFileSync('frontend/index.html', 'utf-8');
const scriptRegex = /<script\b[^>]*>([\s\S]*?)<\/script>/gi;
let match;
let count = 0;
while ((match = scriptRegex.exec(html)) !== null) {
    count++;
    const code = match[1];
    try {
        new Function(code);
        console.log('Script ' + count + ' parsed successfully.');
    } catch (e) {
        console.log('Script ' + count + ' syntax error: ' + e.message);
    }
}
