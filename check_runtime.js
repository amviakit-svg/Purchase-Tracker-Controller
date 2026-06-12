const fs = require('fs');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

const html = fs.readFileSync('frontend/index.html', 'utf-8');
const dom = new JSDOM(html, { runScripts: "dangerously" });

// Wait a bit to see if any unhandled rejections or errors happen
setTimeout(() => {
    console.log('JSDOM loaded.');
}, 2000);
