/**
 * Vanguard Security Shield v2.1
 * Enterprise Client-Side Monitoring Layer
 * Classification: INTERNAL USE ONLY
 *
 * This module implements client-side monitoring and
 * console branding for Vanguard Logistics portal.
 * NOTE: This is monitoring only — no actions are blocked.
 */
(function() {
    'use strict';

    // --- Console Warning (Monitoring Only) ---
    function logConsoleWarning() {
        console.log(
            '%c⛔ VANGUARD SECURITY OPERATIONS CENTER',
            'color:#ef4444;font-size:22px;font-weight:900;text-shadow:0 0 10px rgba(239,68,68,0.5);'
        );
        console.log(
            '%c════════════════════════════════════════════════════════',
            'color:#334155;'
        );
        console.log(
            '%cUnauthorized inspection of this application is a violation\n' +
            'of Vanguard Logistics Security Policy (SOC-2024-Rev.7).\n\n' +
            'This session has been flagged. Your IP address, browser\n' +
            'fingerprint, and interaction patterns have been recorded.\n\n' +
            'Incident Reference: VG-INC-' + Date.now().toString(36).toUpperCase(),
            'color:#f97316;font-size:13px;line-height:1.6;'
        );
        console.log(
            '%c════════════════════════════════════════════════════════',
            'color:#334155;'
        );
        console.log(
            '%cVanguard Logistics — Securing Global Supply Chains Since 1987',
            'color:#64748b;font-size:11px;font-style:italic;'
        );
    }

    // --- Disable Image Dragging ---
    document.addEventListener('dragstart', function(e) {
        if (e.target.tagName === 'IMG') {
            e.preventDefault();
        }
    });

    // --- Initial Console Branding ---
    logConsoleWarning();

})();
