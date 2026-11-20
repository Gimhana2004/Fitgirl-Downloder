// ==UserScript==
// @name         DataNodes Auto-Clicker & Direct Bridge for FitGirl
// @namespace    https://github.com/fitgirl-downloader
// @version      5.0
// @description  Automates DataNodes Step 1 & Step 2, and transmits direct links directly to FitGirl Downloader via local bridge (Works on Safari & Chrome)!
// @author       Antigravity
// @match        *://*.datanodes.to/*
// @match        *://datanodes.to/*
// @grant        none
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    console.log('[DataNodes Auto v5.0] Running on Safari / Chrome');

    // 1. Send direct URL to our Python Downloader via local bridge
    function sendToDownloader(directUrl) {
        // Send via local HTTP server on port 18999
        fetch('http://127.0.0.1:18999', {
            method: 'POST',
            mode: 'cors',
            headers: { 'Content-Type': 'text/plain' },
            body: directUrl
        }).then(() => {
            console.log('[DataNodes Auto] Successfully sent to FitGirl Downloader!');
            updateBanner('🚀 SENT TO FITGIRL DOWNLOADER! Starting Download...', '#a6e3a1');
        }).catch(err => {
            console.warn('[DataNodes Auto] Bridge send error:', err);
        });

        // Also attempt clipboard copy
        try {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(directUrl);
            }
        } catch (e) {}
    }

    // 2. Intercept fetch at document-start before DataNodes scripts run
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        const response = await originalFetch.apply(this, args);
        try {
            const clone = response.clone();
            clone.json().then(data => {
                if (data && data.url) {
                    const directUrl = decodeURIComponent(data.url);
                    console.log('[DataNodes Auto] >>> CAPTURED DIRECT URL:', directUrl);

                    sendToDownloader(directUrl);

                    // Auto-close tab after 2.5 seconds so you don't have open tabs
                    setTimeout(() => {
                        window.close();
                    }, 2500);
                }
            }).catch(() => {});
        } catch (e) {}
        return response;
    };

    // 3. Floating Status Banner
    let banner = null;
    function getOrCreateBanner() {
        if (!banner && document.body) {
            banner = document.createElement('div');
            banner.id = 'dn-auto-banner';
            banner.style.cssText = `
                position: fixed;
                top: 15px;
                left: 50%;
                transform: translateX(-50%);
                background: #1e1e2e;
                color: #89b4fa;
                padding: 10px 24px;
                border-radius: 30px;
                font-family: Arial, sans-serif;
                font-size: 14px;
                font-weight: bold;
                z-index: 99999999;
                box-shadow: 0 4px 20px rgba(0,0,0,0.6);
                border: 2px solid #89b4fa;
                text-align: center;
            `;
            banner.innerHTML = '⚡ DataNodes Auto-Clicker: Active';
            document.body.appendChild(banner);
        }
        return banner;
    }

    function updateBanner(text, color = '#89b4fa') {
        const b = getOrCreateBanner();
        if (b) {
            b.innerHTML = text;
            b.style.color = color;
        }
    }

    // 4. Automation Loop (Step 1 & Step 2)
    let step1Submitted = false;

    const mainInterval = setInterval(() => {
        getOrCreateBanner();

        // --- STEP 1: Continue to Download Form ---
        const form = document.getElementById('downloadForm');
        const continueBtn = document.getElementById('method_free');
        const revealWrapper = document.getElementById('downloadReveal');

        if (form && !step1Submitted) {
            const isButtonEnabled = continueBtn && !continueBtn.disabled;
            const isRevealed = revealWrapper && window.getComputedStyle(revealWrapper).opacity === '1';

            updateBanner('⏳ Step 1: Scan verifying...', '#f9e2af');

            if (isButtonEnabled || isRevealed) {
                step1Submitted = true;
                updateBanner('🚀 Step 1: Advancing to Step 2...', '#a6e3a1');

                if (!form.querySelector('input[name="method_free"]')) {
                    const hidden = document.createElement('input');
                    hidden.type = 'hidden';
                    hidden.name = 'method_free';
                    hidden.value = 'Free Download >>';
                    form.appendChild(hidden);
                }

                setTimeout(() => {
                    form.submit();
                }, 500);
                return;
            }
        }

        // --- STEP 2: Countdown & Free Download Button ---
        const countdownEl = document.querySelector('download-countdown');
        if (countdownEl || window.location.href.includes('/download')) {
            const allButtons = document.querySelectorAll('button');
            for (let b of allButtons) {
                const txt = (b.innerText || b.textContent || '').trim().toLowerCase();
                const classList = b.className || '';

                if (txt.includes('free download') || txt.includes('start download') || classList.includes('bg-blue')) {
                    if (txt.includes('starting in') || txt.includes('ready in') || txt.includes('preparing')) {
                        updateBanner('⏳ Step 2: Waiting for countdown...', '#f9e2af');
                        return;
                    }

                    if (!b.disabled && b.offsetParent !== null) {
                        clearInterval(mainInterval);
                        updateBanner('🔥 Step 2: Clicking Free Download...', '#a6e3a1');
                        setTimeout(() => {
                            b.click();
                        }, 500);
                        return;
                    }
                }
            }
        }
    }, 500);

})();
