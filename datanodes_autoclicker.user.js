// ==UserScript==
// @name         FitGirl Auto-Clicker & Direct Bridge (FuckingFast + DataNodes)
// @namespace    https://github.com/Gimhana2004/Fitgirl-Downloder
// @version      7.5
// @description  Automates FF & DataNodes downloads, detects dead links/404, and transmits directly to FitGirl Downloader!
// @author       Gimhana
// @match        *://*.fuckingfast.co/*
// @match        *://fuckingfast.co/*
// @match        *://*.datanodes.to/*
// @match        *://datanodes.to/*
// @match        *://fitgirl-repacks.site/*
// @match        *://*.fitgirl-repacks.site/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setClipboard
// @grant        window.close
// @run-at       document-start
// ==/UserScript==

(function() {
    'use strict';

    const hostname = window.location.hostname;
    console.log('[FitGirl Auto v7.0] Initialized on:', hostname);

    // ==========================================
    // 1. Dual-Channel Link Transmitter
    // ==========================================
    function transmitDirectLink(directUrl, customMsg) {
        console.log('[FitGirl Auto] Transmitting link:', directUrl);

        // Channel A: OS Clipboard
        try {
            if (typeof GM_setClipboard !== 'undefined') {
                GM_setClipboard(directUrl, 'text');
            } else if (navigator.clipboard) {
                navigator.clipboard.writeText(directUrl);
            }
        } catch (e) {
            console.warn('[FitGirl Auto] Clipboard write warning:', e);
        }

        // Channel B: Local HTTP Bridge on Port 18999
        try {
            if (typeof GM_xmlhttpRequest !== 'undefined') {
                GM_xmlhttpRequest({
                    method: 'POST',
                    url: 'http://127.0.0.1:18999',
                    data: directUrl,
                    headers: { 'Content-Type': 'text/plain' },
                    onload: function(resp) {
                        console.log('[FitGirl Auto] Bridge received link successfully:', resp.responseText);
                        updateBanner(customMsg || '🚀 SENT TO FITGIRL DOWNLOADER! Closing Tab...', '#a6e3a1');
                    },
                    onerror: function(err) {
                        console.warn('[FitGirl Auto] Bridge transmit error:', err);
                        updateBanner(customMsg || '📋 Copied to Clipboard! Closing Tab...', '#a6e3a1');
                    }
                });
            } else {
                fetch('http://127.0.0.1:18999', {
                    method: 'POST',
                    mode: 'cors',
                    headers: { 'Content-Type': 'text/plain' },
                    body: directUrl
                }).catch(() => {});
            }
        } catch (e) {
            console.warn('[FitGirl Auto] Bridge send exception:', e);
        }

        // Auto-close tab after 2.2 seconds
        setTimeout(() => {
            try {
                window.close();
            } catch(e) {}
        }, 2200);
    }

    // ==========================================
    // 2. Floating Banner
    // ==========================================
    let banner = null;
    function getOrCreateBanner() {
        if (!banner && document.body) {
            banner = document.createElement('div');
            banner.id = 'fitgirl-auto-banner';
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
            banner.innerHTML = '⚡ FitGirl Auto: Ready';
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


    // ==========================================
    // 3. FUCKINGFAST.CO AUTOMATION
    // ==========================================
    if (hostname.includes('fuckingfast.co')) {
        console.log('[FitGirl Auto] Mode: FuckingFast detected');

        // Neuter annoying ad popups
        try {
            window.open = function() {
                console.log('[FitGirl Auto] Ad popup blocked');
                return null;
            };
        } catch(e) {}

        let captured = false;

        function handleFuckingFastDirect(url) {
            if (captured || !url) return;
            captured = true;

            let finalUrl = url;
            if (finalUrl.startsWith('/')) {
                finalUrl = new URL(finalUrl, window.location.origin).href;
            }

            // Append filename fragment from URL hash if missing
            if (window.location.hash && !finalUrl.includes('#')) {
                finalUrl += window.location.hash;
            }

            console.log('[FitGirl Auto] >>> FUCKINGFAST DIRECT URL CAPTURED:', finalUrl);
            updateBanner('✅ FuckingFast Direct Link Captured! Sending...', '#a6e3a1');
            transmitDirectLink(finalUrl, '🚀 SENT TO FITGIRL DOWNLOADER! Closing Tab...');
        }

        // Intercept HTMX fetch & XHR responses (which contain hx-redirect)
        const originalFetch = window.fetch;
        window.fetch = async function(...args) {
            const resp = await originalFetch.apply(this, args);
            try {
                const redir = resp.headers.get('hx-redirect') || resp.headers.get('hx-location') || resp.headers.get('location');
                if (redir && redir.includes('http')) {
                    handleFuckingFastDirect(redir);
                }
            } catch(e) {}
            return resp;
        };

        const originalXhrOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(...args) {
            this.addEventListener('readystatechange', () => {
                if (this.readyState >= 2) {
                    try {
                        const redir = this.getResponseHeader('hx-redirect') || this.getResponseHeader('hx-location');
                        if (redir && redir.includes('http')) {
                            handleFuckingFastDirect(redir);
                        }
                    } catch(e) {}
                }
            });
            return originalXhrOpen.apply(this, args);
        };

        function reportDeadLink(reason) {
            if (captured) return;
            captured = true;
            console.log('[FitGirl Auto] File Not Found on Server:', reason);
            updateBanner('❌ FILE NOT FOUND / DELETED ON SERVER!', '#f38ba8');

            let fname = 'unknown_part.rar';
            if (window.location.hash) {
                fname = decodeURIComponent(window.location.hash.substring(1));
            }

            const deadPayload = `DEAD_LINK:${window.location.href}:::${fname}`;
            if (typeof GM_xmlhttpRequest !== 'undefined') {
                GM_xmlhttpRequest({
                    method: 'POST',
                    url: 'http://127.0.0.1:18999',
                    data: deadPayload,
                    headers: { 'Content-Type': 'text/plain' }
                });
            }

            setTimeout(() => {
                try { window.close(); } catch(e) {}
            }, 2500);
        }

        function resolveFuckingFastPage() {
            if (captured) return;
            getOrCreateBanner();

            // Check if page displays File Not Found or Deleted
            const pageText = (document.body ? document.body.innerText : '').toLowerCase();
            if (pageText.includes('file not found') ||
                pageText.includes('file has been removed') ||
                pageText.includes('file does not exist') ||
                pageText.includes('404 not found') ||
                pageText.includes('deleted due to copyright') ||
                pageText.includes('file was deleted')) {
                reportDeadLink('Page text indicates file deleted/not found');
                return;
            }

            updateBanner('⚡ F-Fast: Resolving Direct Link...', '#89b4fa');

            const pathParts = window.location.pathname.split('/').filter(Boolean);
            const fileId = pathParts[pathParts.length - 1];

            // Method 1: Send HTMX POST request directly to /f/{id}/go
            if (fileId && !fileId.includes('.')) {
                fetch(`/f/${encodeURIComponent(fileId)}/go`, {
                    method: 'POST',
                    credentials: 'include',
                    headers: {
                        'HX-Request': 'true',
                        'HX-Current-URL': window.location.href,
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    body: ''
                }).then(resp => {
                    if (resp.status === 404) {
                        reportDeadLink('Server returned HTTP 404');
                        return;
                    }
                    const redir = resp.headers.get('hx-redirect') || resp.headers.get('hx-location');
                    if (redir) {
                        handleFuckingFastDirect(redir);
                    }
                }).catch(() => {});
            }

            // Method 2: Fallback click DOWNLOAD button
            setTimeout(() => {
                if (captured) return;
                const trigger = document.querySelector(`[hx-post*="/${fileId}/"], [hx-post], [data-hx-post]`) ||
                                Array.from(document.querySelectorAll('a, button')).find(el => {
                                    const t = (el.textContent || '').trim().toLowerCase();
                                    return t === 'download' || t.includes('download');
                                });

                if (trigger) {
                    updateBanner('🔥 Auto-Clicking DOWNLOAD Button...', '#f9e2af');
                    trigger.click();
                    setTimeout(() => {
                        if (!captured) {
                            trigger.click();
                        }
                    }, 500);
                } else {
                    // If no trigger after 3s, check if page says not found
                    setTimeout(() => {
                        if (!captured) {
                            const lateText = (document.body ? document.body.innerText : '').toLowerCase();
                            if (lateText.includes('not found') || lateText.includes('error') || lateText.includes('deleted')) {
                                reportDeadLink('No download button found');
                            }
                        }
                    }, 2000);
                }
            }, 700);
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', resolveFuckingFastPage);
        } else {
            resolveFuckingFastPage();
        }
        return;
    }


    // ==========================================
    // 4. DATANODES.TO AUTOMATION
    // ==========================================
    if (hostname.includes('datanodes.to')) {
        console.log('[FitGirl Auto] Mode: DataNodes detected');

        const originalFetch = window.fetch;
        window.fetch = async function(...args) {
            const response = await originalFetch.apply(this, args);
            try {
                const clone = response.clone();
                clone.json().then(data => {
                    if (data && data.url) {
                        const directUrl = decodeURIComponent(data.url);
                        console.log('[FitGirl Auto] >>> CAPTURED DATANODES URL:', directUrl);
                        updateBanner('✅ Direct Link Captured! Sending...', '#a6e3a1');
                        transmitDirectLink(directUrl);
                    }
                }).catch(() => {});
            } catch (e) {}
            return response;
        };

        let step1Submitted = false;
        const mainInterval = setInterval(() => {
            getOrCreateBanner();

            const bodyText = (document.body ? document.body.innerText : '').toLowerCase();
            if (bodyText.includes('file not found') || bodyText.includes('file was deleted') || bodyText.includes('file has been removed')) {
                clearInterval(mainInterval);
                updateBanner('❌ FILE NOT FOUND / DELETED ON SERVER!', '#f38ba8');
                let fname = window.location.pathname.split('/').filter(Boolean).pop() || 'unknown_part.rar';
                const deadPayload = `DEAD_LINK:${window.location.href}:::${fname}`;
                if (typeof GM_xmlhttpRequest !== 'undefined') {
                    GM_xmlhttpRequest({
                        method: 'POST',
                        url: 'http://127.0.0.1:18999',
                        data: deadPayload,
                        headers: { 'Content-Type': 'text/plain' }
                    });
                }
                setTimeout(() => { try { window.close(); } catch(e) {} }, 2500);
                return;
            }

            // Step 1: Wait for scan and click Free Download >>
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

                    setTimeout(() => { form.submit(); }, 500);
                    return;
                }
            }

            // Step 2: Wait for countdown and click final download button
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
                            setTimeout(() => { b.click(); }, 500);
                            return;
                        }
                    }
                }
            }
        }, 500);
        return;
    }


    // ==========================================
    // 5. FITGIRL REPACKS PAGE HELPER
    // ==========================================
    if (hostname.includes('fitgirl-repacks.site')) {
        console.log('[FitGirl Auto] Mode: FitGirl Repack page detected');

        function setupFitGirlHelper() {
            // Find all FuckingFast links on the page
            const links = Array.from(document.querySelectorAll('a[href*="fuckingfast.co"]'))
                               .map(a => a.href)
                               .filter((v, i, a) => a.indexOf(v) === i);

            if (links.length === 0) return;

            console.log(`[FitGirl Auto] Found ${links.length} FuckingFast download parts!`);

            const helperBtn = document.createElement('button');
            helperBtn.id = 'fitgirl-grab-all-btn';
            helperBtn.innerHTML = `🚀 Send ${links.length} FuckingFast Parts to Downloader`;
            helperBtn.style.cssText = `
                position: fixed;
                bottom: 25px;
                right: 25px;
                background: linear-gradient(135deg, #a6e3a1, #89b4fa);
                color: #11111b;
                border: none;
                border-radius: 25px;
                padding: 12px 24px;
                font-family: Arial, sans-serif;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                z-index: 99999999;
                transition: transform 0.2s, background 0.2s;
            `;

            helperBtn.onmouseenter = () => { helperBtn.style.transform = 'scale(1.05)'; };
            helperBtn.onmouseleave = () => { helperBtn.style.transform = 'scale(1)'; };

            helperBtn.onclick = () => {
                helperBtn.innerHTML = '⏳ Sending to App...';
                const payload = links.join('\n');

                if (typeof GM_setClipboard !== 'undefined') {
                    GM_setClipboard(payload, 'text');
                }

                if (typeof GM_xmlhttpRequest !== 'undefined') {
                    GM_xmlhttpRequest({
                        method: 'POST',
                        url: 'http://127.0.0.1:18999',
                        data: payload,
                        headers: { 'Content-Type': 'text/plain' },
                        onload: function(r) {
                            helperBtn.innerHTML = `✅ ${links.length} Parts Sent to Downloader!`;
                            helperBtn.style.background = '#a6e3a1';
                            setTimeout(() => {
                                helperBtn.innerHTML = `🚀 Send ${links.length} FuckingFast Parts to Downloader`;
                                helperBtn.style.background = 'linear-gradient(135deg, #a6e3a1, #89b4fa)';
                            }, 3500);
                        },
                        onerror: function() {
                            helperBtn.innerHTML = `📋 Copied ${links.length} Parts! (Paste in App)`;
                            setTimeout(() => {
                                helperBtn.innerHTML = `🚀 Send ${links.length} FuckingFast Parts to Downloader`;
                            }, 3500);
                        }
                    });
                }
            };

            document.body.appendChild(helperBtn);
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupFitGirlHelper);
        } else {
            setupFitGirlHelper();
        }
    }

})();
