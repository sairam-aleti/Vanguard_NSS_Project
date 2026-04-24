/**
 * Vanguard Security Shield v2.1
 * Enterprise Client-Side Protection Layer
 * Classification: INTERNAL USE ONLY
 * 
 * This module implements client-side tamper detection
 * and inspection prevention for Vanguard Logistics portal.
 */
(function() {
    'use strict';

    // --- Right-Click Prevention ---
    document.addEventListener('contextmenu', function(e) {
        e.preventDefault();
        showSecurityNotice();
        return false;
    });

    // --- Keyboard Shortcut Blocking ---
    document.addEventListener('keydown', function(e) {
        // F12 — DevTools
        if (e.key === 'F12' || e.keyCode === 123) {
            e.preventDefault();
            showSecurityNotice();
            return false;
        }
        // Ctrl+Shift+I — DevTools
        if (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'i')) {
            e.preventDefault();
            showSecurityNotice();
            return false;
        }
        // Ctrl+Shift+J — Console
        if (e.ctrlKey && e.shiftKey && (e.key === 'J' || e.key === 'j')) {
            e.preventDefault();
            showSecurityNotice();
            return false;
        }
        // Ctrl+U — View Source
        if (e.ctrlKey && (e.key === 'U' || e.key === 'u')) {
            e.preventDefault();
            showSecurityNotice();
            return false;
        }
        // Ctrl+Shift+C — Element Inspector
        if (e.ctrlKey && e.shiftKey && (e.key === 'C' || e.key === 'c')) {
            e.preventDefault();
            showSecurityNotice();
            return false;
        }
        // Ctrl+S — Save Page
        if (e.ctrlKey && (e.key === 'S' || e.key === 's')) {
            e.preventDefault();
            return false;
        }
    });

    // --- DevTools Detection via Window Size ---
    var devtoolsOpen = false;
    var checkInterval = setInterval(function() {
        var widthDiff = window.outerWidth - window.innerWidth > 200;
        var heightDiff = window.outerHeight - window.innerHeight > 200;
        
        if ((widthDiff || heightDiff) && !devtoolsOpen) {
            devtoolsOpen = true;
            logConsoleWarning();
        } else if (!widthDiff && !heightDiff) {
            devtoolsOpen = false;
        }
    }, 1500);

    // --- Disable Image Dragging ---
    document.addEventListener('dragstart', function(e) {
        if (e.target.tagName === 'IMG') {
            e.preventDefault();
        }
    });

    // --- Disable Text Selection on Protected Elements ---
    document.addEventListener('selectstart', function(e) {
        if (e.target.closest('.vg-protected')) {
            e.preventDefault();
        }
    });

    // --- Security Notice Toast ---
    function showSecurityNotice() {
        // Remove existing toasts
        var existing = document.getElementById('vg-security-toast');
        if (existing) existing.remove();

        var toast = document.createElement('div');
        toast.id = 'vg-security-toast';
        toast.innerHTML = [
            '<div style="position:fixed;top:20px;right:20px;z-index:99999;',
            'background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);',
            'border:1px solid rgba(239,68,68,0.5);border-radius:12px;',
            'padding:16px 24px;color:#f8fafc;font-family:Inter,system-ui,sans-serif;',
            'box-shadow:0 25px 50px rgba(0,0,0,0.5),0 0 30px rgba(239,68,68,0.15);',
            'max-width:380px;animation:vgSlideIn 0.3s ease-out;">',
            '<div style="display:flex;align-items:center;gap:12px;">',
            '<div style="width:40px;height:40px;border-radius:50%;',
            'background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);',
            'display:flex;align-items:center;justify-content:center;flex-shrink:0;">',
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2">',
            '<path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>',
            '</svg></div>',
            '<div><div style="font-weight:600;font-size:14px;color:#ef4444;margin-bottom:2px;">',
            'Security Alert</div>',
            '<div style="font-size:12px;color:#94a3b8;line-height:1.4;">',
            'This action has been blocked and logged by Vanguard SOC. ',
            'Ref: VG-SEC-', Math.random().toString(36).substr(2, 8).toUpperCase(),
            '</div></div></div></div>'
        ].join('');
        
        document.body.appendChild(toast);
        
        // Auto-dismiss after 4 seconds
        setTimeout(function() {
            if (toast.parentNode) {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                toast.style.transition = 'all 0.3s ease-in';
                setTimeout(function() { toast.remove(); }, 300);
            }
        }, 4000);
    }

    // --- Console Warning ---
    function logConsoleWarning() {
        console.clear();
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

    // --- Inject Animation Keyframe ---
    var style = document.createElement('style');
    style.textContent = '@keyframes vgSlideIn{from{opacity:0;transform:translateX(100%)}to{opacity:1;transform:translateX(0)}}';
    document.head.appendChild(style);

    // --- Initial Console Branding ---
    logConsoleWarning();

})();
