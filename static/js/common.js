/**
 * 🔧 TradLive - Fonctions utilitaires communes
 * Bibliothèque de fonctions partagées pour toute l'application
 * Architecture inspirée des standards Netflix, Spotify, Airbnb
 */

/* ========================================
   CONSTANTES GLOBALES
======================================== */
const TRADLIVE_CONFIG = {
    // Délais d'animation
    ANIMATION_FAST: 150,
    ANIMATION_NORMAL: 300,
    ANIMATION_SLOW: 600,
    
    // Délais de feedback
    STATUS_HIDE_DELAY: 5000,
    SUCCESS_REDIRECT_DELAY: 2000,
    
    // Configuration réseau
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000,
    
    // Stockage local
    STORAGE_KEYS: {
        LANGUAGE: 'tradlive_language',
        USER: 'tradlive_user',
        PREFERENCES: 'tradlive_preferences'
    }
};

/* ========================================
   DÉTECTION DU NAVIGATEUR ET CAPACITÉS
======================================== */
class BrowserCapabilities {
    constructor() {
        this.userAgent = navigator.userAgent;
        this.capabilities = this.detectCapabilities();
        this.browserInfo = this.detectBrowser();
    }
    
    detectCapabilities() {
        return {
            // APIs disponibles
            microphone: 'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices,
            speechRecognition: 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window,
            speechSynthesis: 'speechSynthesis' in window,
            webRTC: 'RTCPeerConnection' in window,
            localStorage: 'localStorage' in window,
            
            // Fonctionnalités du navigateur
            supportsWebP: this.checkWebPSupport(),
            supportsTouch: 'ontouchstart' in window,
            isMobile: /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(this.userAgent),
            
            // Performance
            connectionType: this.getConnectionType(),
            hardwareConcurrency: navigator.hardwareConcurrency || 2
        };
    }
    
    detectBrowser() {
        const ua = this.userAgent;
        
        if (ua.includes('Chrome') && !ua.includes('Edge')) {
            return { name: 'Chrome', family: 'chromium', score: 100 };
        } else if (ua.includes('Edg/')) {
            return { name: 'Edge', family: 'chromium', score: 95 };
        } else if (ua.includes('Firefox')) {
            return { name: 'Firefox', family: 'gecko', score: 80 };
        } else if (ua.includes('Safari') && !ua.includes('Chrome')) {
            return { name: 'Safari', family: 'webkit', score: 70 };
        }
        
        return { name: 'Unknown', family: 'unknown', score: 50 };
    }
    
    checkWebPSupport() {
        const canvas = document.createElement('canvas');
        canvas.width = 1;
        canvas.height = 1;
        return canvas.toDataURL('image/webp').indexOf('webp') !== -1;
    }
    
    getConnectionType() {
        if ('connection' in navigator) {
            return navigator.connection.effectiveType || 'unknown';
        }
        return 'unknown';
    }
    
    getOverallScore() {
        let score = this.browserInfo.score;
        
        // Bonus pour les fonctionnalités supportées
        if (this.capabilities.speechRecognition) score += 20;
        if (this.capabilities.speechSynthesis) score += 10;
        if (this.capabilities.microphone) score += 15;
        if (!this.capabilities.isMobile) score += 5;
        
        return Math.min(score, 100);
    }
    
    getRecommendations() {
        const score = this.getOverallScore();
        
        if (score >= 90) {
            return {
                level: 'excellent',
                message: '✅ Navigateur parfaitement compatible !',
                suggestions: []
            };
        } else if (score >= 70) {
            return {
                level: 'good',
                message: '✅ Navigateur compatible avec quelques limitations',
                suggestions: ['Mettre à jour votre navigateur pour une meilleure expérience']
            };
        } else {
            return {
                level: 'limited',
                message: '⚠️ Compatibilité limitée détectée',
                suggestions: [
                    'Utilisez Chrome ou Edge pour une expérience optimale',
                    'Activez le microphone dans les paramètres',
                    'Mettez à jour votre navigateur'
                ]
            };
        }
    }
}

/* ========================================
   GESTIONNAIRE D'ANIMATIONS
======================================== */
class AnimationManager {
    static fadeIn(element, duration = TRADLIVE_CONFIG.ANIMATION_NORMAL) {
        return new Promise((resolve) => {
            element.style.opacity = '0';
            element.style.transition = `opacity ${duration}ms ease`;
            
            requestAnimationFrame(() => {
                element.style.opacity = '1';
                setTimeout(resolve, duration);
            });
        });
    }
    
    static slideInUp(element, duration = TRADLIVE_CONFIG.ANIMATION_NORMAL) {
        return new Promise((resolve) => {
            element.style.opacity = '0';
            element.style.transform = 'translateY(20px)';
            element.style.transition = `all ${duration}ms ease`;
            
            requestAnimationFrame(() => {
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
                setTimeout(resolve, duration);
            });
        });
    }
    
    static scaleIn(element, duration = TRADLIVE_CONFIG.ANIMATION_NORMAL) {
        return new Promise((resolve) => {
            element.style.opacity = '0';
            element.style.transform = 'scale(0.8)';
            element.style.transition = `all ${duration}ms cubic-bezier(0.68, -0.55, 0.265, 1.55)`;
            
            requestAnimationFrame(() => {
                element.style.opacity = '1';
                element.style.transform = 'scale(1)';
                setTimeout(resolve, duration);
            });
        });
    }
    
    static shake(element, duration = 600) {
        return new Promise((resolve) => {
            element.style.animation = `shake ${duration}ms ease`;
            setTimeout(() => {
                element.style.animation = '';
                resolve();
            }, duration);
        });
    }
    
    static pulse(element, duration = 600) {
        return new Promise((resolve) => {
            element.style.animation = `pulse ${duration}ms ease`;
            setTimeout(() => {
                element.style.animation = '';
                resolve();
            }, duration);
        });
    }
    
    // Animation staggerée pour plusieurs éléments
    static staggerAnimation(elements, animationType = 'slideInUp', delay = 100) {
        return Promise.all(
            Array.from(elements).map((element, index) => {
                return new Promise((resolve) => {
                    setTimeout(() => {
                        this[animationType](element).then(resolve);
                    }, index * delay);
                });
            })
        );
    }
}

/* ========================================
   GESTIONNAIRE DE NOTIFICATIONS
======================================== */
class NotificationManager {
    constructor() {
        this.container = this.createContainer();
        this.notifications = new Map();
    }
    
    createContainer() {
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                max-width: 400px;
                pointer-events: none;
            `;
            document.body.appendChild(container);
        }
        return container;
    }
    
    show(message, type = 'info', options = {}) {
        const id = Date.now() + Math.random();
        const notification = this.createNotification(message, type, options);
        
        this.container.appendChild(notification);
        this.notifications.set(id, notification);
        
        // Animation d'entrée
        requestAnimationFrame(() => {
            notification.style.transform = 'translateX(0)';
            notification.style.opacity = '1';
        });
        
        // Auto-suppression
        const duration = options.duration || 5000;
        if (duration > 0) {
            setTimeout(() => this.hide(id), duration);
        }
        
        return id;
    }
    
    createNotification(message, type, options) {
        const notification = document.createElement('div');
        const colors = {
            success: '#4CAF50',
            error: '#f44336',
            warning: '#ff9800',
            info: '#2196F3'
        };
        
        notification.style.cssText = `
            background: ${colors[type] || colors.info};
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            margin-bottom: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            transform: translateX(100%);
            opacity: 0;
            transition: all 0.3s ease;
            pointer-events: auto;
            cursor: pointer;
            border-left: 4px solid rgba(255,255,255,0.3);
            font-weight: 500;
        `;
        
        // Icônes selon le type
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 16px;">${icons[type] || icons.info}</span>
                <span>${message}</span>
            </div>
        `;
        
        // Clic pour fermer
        notification.addEventListener('click', () => {
            const id = Array.from(this.notifications.entries())
                .find(([, notif]) => notif === notification)?.[0];
            if (id) this.hide(id);
        });
        
        return notification;
    }
    
    hide(id) {
        const notification = this.notifications.get(id);
        if (notification) {
            notification.style.transform = 'translateX(100%)';
            notification.style.opacity = '0';
            
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
                this.notifications.delete(id);
            }, 300);
        }
    }
    
    clear() {
        this.notifications.forEach((_, id) => this.hide(id));
    }
}

/* ========================================
   GESTIONNAIRE DE STOCKAGE LOCAL
======================================== */
class StorageManager {
    static set(key, value) {
        try {
            const serialized = JSON.stringify({
                value,
                timestamp: Date.now(),
                version: '1.0'
            });
            localStorage.setItem(key, serialized);
            return true;
        } catch (error) {
            console.warn('Erreur de stockage local:', error);
            return false;
        }
    }
    
    static get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            if (!item) return defaultValue;
            
            const parsed = JSON.parse(item);
            return parsed.value;
        } catch (error) {
            console.warn('Erreur de lecture du stockage local:', error);
            return defaultValue;
        }
    }
    
    static remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.warn('Erreur de suppression du stockage local:', error);
            return false;
        }
    }
    
    static clear() {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.warn('Erreur de vidage du stockage local:', error);
            return false;
        }
    }
    
    static getStorageInfo() {
        try {
            const total = new Blob(Object.values(localStorage)).size;
            return {
                used: total,
                available: 5 * 1024 * 1024 - total, // ~5MB limit
                keys: Object.keys(localStorage).length
            };
        } catch (error) {
            return { used: 0, available: 0, keys: 0 };
        }
    }
}

/* ========================================
   GESTIONNAIRE DE REQUÊTES RÉSEAU
======================================== */
class NetworkManager {
    static async request(url, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            timeout: 10000,
            retries: TRADLIVE_CONFIG.RETRY_ATTEMPTS
        };
        
        const config = { ...defaultOptions, ...options };
        
        for (let attempt = 0; attempt <= config.retries; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), config.timeout);
                
                const response = await fetch(url, {
                    ...config,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                return { success: true, data };
                
            } catch (error) {
                console.warn(`Tentative ${attempt + 1}/${config.retries + 1} échouée:`, error.message);
                
                if (attempt === config.retries) {
                    return { 
                        success: false, 
                        error: error.message,
                        isTimeout: error.name === 'AbortError'
                    };
                }
                
                // Délai avant la prochaine tentative
                await new Promise(resolve => 
                    setTimeout(resolve, TRADLIVE_CONFIG.RETRY_DELAY * (attempt + 1))
                );
            }
        }
    }
    
    static async get(url, params = {}) {
        const urlWithParams = new URL(url, window.location.origin);
        Object.entries(params).forEach(([key, value]) => {
            urlWithParams.searchParams.append(key, value);
        });
        
        return this.request(urlWithParams.toString());
    }
    
    static async post(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
}

/* ========================================
   UTILITAIRES DIVERS
======================================== */
class Utils {
    // Debouncing pour éviter les appels répétés
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Throttling pour limiter la fréquence d'exécution
    static throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    // Génération d'IDs uniques
    static generateId(prefix = 'id') {
        return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    // Formattage des dates
    static formatDate(date, locale = 'fr-FR') {
        return new Intl.DateTimeFormat(locale, {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(new Date(date));
    }
    
    // Validation d'email
    static isValidEmail(email) {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    }
    
    // Truncate text
    static truncate(text, length = 100, suffix = '...') {
        if (text.length <= length) return text;
        return text.substring(0, length) + suffix;
    }
    
    // Capitalisation
    static capitalize(text) {
        return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
    }
    
    // Nettoyage des espaces
    static cleanText(text) {
        return text.trim().replace(/\s+/g, ' ');
    }
    
    // Vérification si un élément est visible
    static isElementVisible(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= window.innerHeight &&
            rect.right <= window.innerWidth
        );
    }
    
    // Copie dans le presse-papier
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (error) {
            // Fallback pour les navigateurs plus anciens
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            const success = document.execCommand('copy');
            document.body.removeChild(textArea);
            return success;
        }
    }
}

/* ========================================
   GESTIONNAIRE D'ÉVÉNEMENTS GLOBAUX
======================================== */
class EventManager {
    constructor() {
        this.listeners = new Map();
        this.setupGlobalListeners();
    }
    
    setupGlobalListeners() {
        // Gestion des erreurs JavaScript
        window.addEventListener('error', (event) => {
            console.error('Erreur JavaScript:', event.error);
            this.emit('app:error', { type: 'javascript', error: event.error });
        });
        
        // Gestion des erreurs de ressources
        window.addEventListener('error', (event) => {
            if (event.target !== window) {
                console.warn('Erreur de ressource:', event.target.src || event.target.href);
                this.emit('app:resource-error', { element: event.target });
            }
        }, true);
        
        // Gestion des changements de connexion
        window.addEventListener('online', () => {
            this.emit('app:connection', { online: true });
        });
        
        window.addEventListener('offline', () => {
            this.emit('app:connection', { online: false });
        });
        
        // Gestion du redimensionnement
        window.addEventListener('resize', Utils.throttle(() => {
            this.emit('app:resize', { 
                width: window.innerWidth, 
                height: window.innerHeight 
            });
        }, 250));
    }
    
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);
    }
    
    off(event, callback) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(callback);
        }
    }
    
    emit(event, data = {}) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Erreur dans le listener ${event}:`, error);
                }
            });
        }
    }
}

/* ========================================
   INITIALISATION GLOBALE
======================================== */
// Instances globales
window.TradLive = {
    browser: new BrowserCapabilities(),
    animations: AnimationManager,
    notifications: new NotificationManager(),
    storage: StorageManager,
    network: NetworkManager,
    utils: Utils,
    events: new EventManager(),
    config: TRADLIVE_CONFIG
};

// Initialisation au chargement du DOM
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 TradLive Common.js chargé');
    
    // Détection des capacités du navigateur
    const browserInfo = window.TradLive.browser.getRecommendations();
    console.log(`🌐 Navigateur: ${browserInfo.level} - ${browserInfo.message}`);
    
    // Ajout de classes CSS utiles sur le body
    document.body.classList.add(
        `browser-${window.TradLive.browser.browserInfo.family}`,
        `capability-${browserInfo.level}`,
        window.TradLive.browser.capabilities.isMobile ? 'is-mobile' : 'is-desktop',
        window.TradLive.browser.capabilities.supportsTouch ? 'has-touch' : 'no-touch'
    );
    
    // Émission d'événement de démarrage
    window.TradLive.events.emit('app:ready', {
        timestamp: Date.now(),
        browser: window.TradLive.browser.browserInfo,
        capabilities: window.TradLive.browser.capabilities
    });
});

// Export pour les modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.TradLive;
}