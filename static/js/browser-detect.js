/**
 * Browser Detection Utility - Detects in-app browsers that block pop-ups
 * 
 * In-app browsers (Instagram, Facebook, TikTok, etc.) typically block pop-ups,
 * which breaks Clerk's openSignIn() and openSignUp() methods.
 * This utility helps detect these browsers so we can use redirect-based auth instead.
 */

const BrowserDetect = {
    /**
     * User agent patterns for common in-app browsers
     */
    inAppBrowserPatterns: [
        'Instagram',           // Instagram WebView
        'FBAN',               // Facebook App (Android)
        'FBAV',               // Facebook App (iOS)
        'FB_IAB',             // Facebook In-App Browser
        'FB4A',               // Facebook for Android
        'FBIOS',              // Facebook for iOS
        'TikTok',             // TikTok WebView
        'BytedanceWebview',   // TikTok/Douyin WebView
        'Snapchat',           // Snapchat WebView
        'LinkedIn',           // LinkedIn WebView
        'Pinterest',          // Pinterest WebView
        'Twitter',            // Twitter/X WebView
        'Line',               // Line WebView
        'KAKAOTALK',          // KakaoTalk WebView
        'WeChat',             // WeChat WebView
        'MicroMessenger',     // WeChat WebView (alternative)
        'QQ',                 // QQ WebView
        'Weibo',              // Weibo WebView
        'GSA',                // Google Search App
    ],

    /**
     * Check if current browser is an in-app browser
     * @returns {boolean} True if running in an in-app browser
     */
    isInAppBrowser() {
        const ua = navigator.userAgent || navigator.vendor || window.opera || '';
        
        // Check for known in-app browser patterns
        for (const pattern of this.inAppBrowserPatterns) {
            if (ua.includes(pattern)) {
                return true;
            }
        }
        
        // Check for generic Android WebView
        // Android WebViews typically have 'wv' in the user agent
        if (/Android/.test(ua) && /wv/.test(ua)) {
            return true;
        }
        
        // Check for iOS WebView (not Safari or Chrome)
        // iOS WebViews don't have 'Safari' in UA but have AppleWebKit
        if (/iPhone|iPad|iPod/.test(ua) && /AppleWebKit/.test(ua) && !/Safari/.test(ua)) {
            return true;
        }
        
        // Check if window.open is blocked (some WebViews block this)
        // This is a more aggressive detection that catches edge cases
        if (this._isPopupBlocked()) {
            return true;
        }
        
        return false;
    },

    /**
     * Test if pop-ups are blocked by trying to open a blank window
     * @returns {boolean} True if pop-ups appear to be blocked
     * @private
     */
    _isPopupBlocked() {
        try {
            // Try to detect if we're in a context where pop-ups would be blocked
            // In-app browsers often set restrictive window properties
            
            // Check for restricted opener
            if (window.opener === null && document.referrer === '' && window.self === window.top) {
                // Could be direct navigation, not necessarily in-app browser
                return false;
            }
            
            // Some in-app browsers restrict window features
            if (typeof window.open === 'undefined') {
                return true;
            }
            
            return false;
        } catch (e) {
            // If we can't check, assume it might be blocked
            return false;
        }
    },

    /**
     * Get the name of the detected in-app browser (for debugging)
     * @returns {string|null} Name of the in-app browser or null if not detected
     */
    getInAppBrowserName() {
        const ua = navigator.userAgent || navigator.vendor || window.opera || '';
        
        for (const pattern of this.inAppBrowserPatterns) {
            if (ua.includes(pattern)) {
                return pattern;
            }
        }
        
        if (/Android/.test(ua) && /wv/.test(ua)) {
            return 'Android WebView';
        }
        
        if (/iPhone|iPad|iPod/.test(ua) && /AppleWebKit/.test(ua) && !/Safari/.test(ua)) {
            return 'iOS WebView';
        }
        
        return null;
    },

    /**
     * Open Clerk sign-in with appropriate method for the browser
     * Uses redirect for in-app browsers, pop-up for regular browsers
     * @param {string} redirectUrl - URL to redirect to after sign-in (optional)
     */
    openSignIn(redirectUrl) {
        const returnUrl = redirectUrl || window.location.href;
        
        if (this.isInAppBrowser()) {
            // Use redirect-based auth for in-app browsers
            window.location.href = `/sign-in?redirect_url=${encodeURIComponent(returnUrl)}`;
        } else if (window.Clerk && window.Clerk.openSignIn) {
            // Use pop-up for regular browsers
            window.Clerk.openSignIn();
        } else {
            // Fallback to redirect if Clerk not ready
            window.location.href = `/sign-in?redirect_url=${encodeURIComponent(returnUrl)}`;
        }
    },

    /**
     * Open Clerk sign-up with appropriate method for the browser
     * Uses redirect for in-app browsers, pop-up for regular browsers
     * @param {string} redirectUrl - URL to redirect to after sign-up (optional)
     */
    openSignUp(redirectUrl) {
        const returnUrl = redirectUrl || window.location.href;
        
        if (this.isInAppBrowser()) {
            // Use redirect-based auth for in-app browsers
            window.location.href = `/sign-up?redirect_url=${encodeURIComponent(returnUrl)}`;
        } else if (window.Clerk && window.Clerk.openSignUp) {
            // Use pop-up for regular browsers
            window.Clerk.openSignUp();
        } else {
            // Fallback to redirect if Clerk not ready
            window.location.href = `/sign-up?redirect_url=${encodeURIComponent(returnUrl)}`;
        }
    }
};

// Make it globally available
window.BrowserDetect = BrowserDetect;

// Log detection result for debugging (only in development)
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    const browserName = BrowserDetect.getInAppBrowserName();
    if (browserName) {
        console.log(`[BrowserDetect] In-app browser detected: ${browserName}`);
    }
}
