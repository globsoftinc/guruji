/**
 * Auth State Cache - Optimistic UI rendering for Clerk authentication
 * 
 * This module caches auth UI state in localStorage to provide instant UI
 * rendering while Clerk SDK initializes in the background.
 * 
 * NOTE: This does NOT cache credentials - only UI state.
 * Actual authentication still goes through Clerk's secure flow.
 */

const AuthCache = {
    STORAGE_KEY: 'guruji_auth_cache',
    CACHE_TTL: 24 * 60 * 60 * 1000, // 24 hours in milliseconds

    /**
     * Get cached auth state
     * @returns {Object|null} Cached auth state or null if invalid/expired
     */
    get() {
        try {
            const cached = localStorage.getItem(this.STORAGE_KEY);
            if (!cached) return null;

            const data = JSON.parse(cached);
            
            // Check if cache is expired
            if (Date.now() - data.lastSync > this.CACHE_TTL) {
                this.clear();
                return null;
            }

            return data;
        } catch (e) {
            this.clear();
            return null;
        }
    },

    /**
     * Save auth state to cache
     * @param {Object} state - Auth state to cache
     */
    set(state) {
        try {
            const data = {
                isLoggedIn: state.isLoggedIn || false,
                userId: state.userId || null,
                userName: state.userName || '',
                userImage: state.userImage || null,
                lastSync: Date.now()
            };
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
        } catch (e) {
            // localStorage might be full or disabled
            console.warn('AuthCache: Unable to save state');
        }
    },

    /**
     * Clear the auth cache (on sign out)
     */
    clear() {
        try {
            localStorage.removeItem(this.STORAGE_KEY);
        } catch (e) {
            // Ignore errors
        }
    },

    /**
     * Check if user appears to be logged in (from cache)
     * @returns {boolean}
     */
    isLoggedIn() {
        const cached = this.get();
        return cached ? cached.isLoggedIn : false;
    },

    /**
     * Get cached user ID for early API calls
     * @returns {string|null}
     */
    getUserId() {
        const cached = this.get();
        return cached ? cached.userId : null;
    },

    /**
     * Sync cache with actual Clerk state
     * @param {Object} clerkUser - Clerk user object
     */
    syncWithClerk(clerkUser) {
    if (clerkUser) {
        // User is logged in - mark that they have an account
        this.markHasAccount();
        
        this.set({
            isLoggedIn: true,
            userId: clerkUser.id,
            userName: clerkUser.fullName || clerkUser.firstName || 'User',
            userImage: clerkUser.imageUrl || null
        });
    } else {
        this.clear();
        // Note: We don't clear hasAccount - they still have an account even when logged out
    }
},
/**
 * Mark that user has created an account (call after successful signup)
 */
markHasAccount() {
    try {
        localStorage.setItem('guruji_has_account', 'true');
    } catch (e) {
        console.warn('AuthCache: Unable to save account status');
    }
},

/**
 * Check if user has ever had an account
 * @returns {boolean}
 */
hasAccount() {
    try {
        return localStorage.getItem('guruji_has_account') === 'true';
    } catch (e) {
        return false;
    }
},
    /**
     * Render optimistic Sign In button immediately
     * @param {HTMLElement} container - Container element for the button
     * @returns {boolean} Whether optimistic UI was rendered
     */
    renderOptimisticUI(container) {
        if (!container) return false;

        const cached = this.get();

        if (cached && cached.isLoggedIn) {
            // Show a placeholder user indicator
            container.innerHTML = `
                <a href="/dashboard" class="nav-link">Dashboard</a>
                <div class="auth-loading" style="display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.5rem; border-radius: 50%; background: var(--bg-tertiary, #1a1a2e); min-width: 32px; min-height: 32px; justify-content: center;">
                    ${cached.userImage 
                        ? `<img src="${cached.userImage}" alt="" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover;">` 
                        : `<i class="fas fa-user" style="color: var(--text-secondary, #888);"></i>`
                    }
                </div>
            `;
            return true;
} else if (cached === null) {
    // No cache - check if they have an account
    const buttonText = this.hasAccount() ? 'Sign In' : 'Sign Up';
    const buttonIcon = this.hasAccount() ? 'fa-sign-in-alt' : 'fa-user-plus';
    container.innerHTML = `
        <button class="btn btn-primary" id="optimistic-signin" style="opacity: 0.7;">
            <i class="fas fa-spinner fa-spin"></i> ${buttonText}
        </button>
    `;
    return true;
} else {
    // Cache says not logged in - show appropriate button
    const buttonText = this.hasAccount() ? 'Sign In' : 'Sign Up';
    const buttonIcon = this.hasAccount() ? 'fa-sign-in-alt' : 'fa-user-plus';
    container.innerHTML = `
        <button class="btn btn-primary" id="optimistic-signin">
            <i class="fas ${buttonIcon}"></i> ${buttonText}
        </button>
    `;
    // Make it clickable
    const btn = container.querySelector('#optimistic-signin');
    if (btn) {
        btn.onclick = () => {
            if (window.Clerk) {
                if (this.hasAccount()) {
                    window.Clerk.openSignIn();
                } else {
                    window.Clerk.openSignUp();
                }
            } else {
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
                btn.disabled = true;
            }
        };
    }
    return true;
}
    }
};

// Make it globally available
window.AuthCache = AuthCache;
