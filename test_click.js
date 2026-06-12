const fs = require('fs');
const html = fs.readFileSync('frontend/index.html', 'utf-8');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

const dom = new JSDOM(html, { runScripts: "dangerously", url: "http://localhost:5000/" });

setTimeout(() => {
    try {
        console.log("Before click, hidden:", dom.window.document.getElementById('page-upload').classList.contains('hidden'));
        dom.window.switchTab('upload');
        console.log("After click, hidden:", dom.window.document.getElementById('page-upload').classList.contains('hidden'));
    } catch(e) {
        console.error("Error during switchTab:", e);
    }
}, 1000);
