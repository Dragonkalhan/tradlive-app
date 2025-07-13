/**
 * 🎤 TradLive - Logique complète de la salle de traduction (VERSION FINALE)
 * Intégration complète avec common.js et translations.js (16 langues)
 * Architecture professionnelle Netflix/Spotify niveau - PRODUCTION READY
 * 🌐 Déployé sur: https://tradlive-app.onrender.com
 */

/* ========================================
   VARIABLES GLOBALES DE LA SALLE
======================================== */
let userData = null;
let roomData = null;
let recognition = null;
let participantRecognition = null;
let isListening = false;
let isParticipantListening = false;
let isHost = false;
let updateInterval = null;
let heartbeatInterval = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

// Variables pour éviter la lecture en boucle (CRITIQUE - NE PAS MODIFIER)
let lastSpokenText = '';
let lastSpokenTimestamp = 0;
let lastTranslationId = null;
let networkErrorCount = 0;

// Éléments DOM (seront initialisés au chargement)
let statusEl, controlsEl, hostControlsEl, participantControlsEl;
let micButton, participantMicButton, textModeButton, participantTextButton;
let waveAnimation, participantWave, qrSection, qrCodeImage, connectionStatus;
let textInputFallback, participantTextInput;
let hostInterface, participantInterface;
let hostOriginalText, hostResponsesText;
let participantOriginalText, participantTranslatedText, participantMessageArea;
let participantOwnText, participantFrenchText, participantTargetLanguage;
let participantsListEl, participantCountEl;

/* ========================================
   NOMS DES LANGUES (MAPPING) - INTÉGRÉ AVEC TRANSLATIONS.JS
======================================== */
function getLanguageName(code) {
    // Système unifié avec translations.js
    if (window.getTranslation && window.interfaceLanguage) {
        const langKey = `lang_${getLangKey(code)}`;
        return window.getTranslation(langKey, window.interfaceLanguage);
    }
    
    // Fallback robuste
    const languageNames = {
        fr: "Français", en: "English", es: "Español", 
        de: "Deutsch", it: "Italiano", pt: "Português",
        ru: "Русский", "zh-CN": "中文", ja: "日本語",
        ar: "العربية", uk: "Українська", fa: "فارسی",
        hi: "हिन्दी", bn: "বাংলা", te: "తెలుగు", mr: "मराठी"
    };
    return languageNames[code] || code;
}

function getLangKey(code) {
    const mapping = {
        'fr': 'french', 'en': 'english', 'es': 'spanish',
        'de': 'german', 'it': 'italian', 'pt': 'portuguese',
        'ru': 'russian', 'zh-CN': 'chinese', 'ja': 'japanese',
        'ar': 'arabic', 'uk': 'ukrainian', 'fa': 'persian',
        'hi': 'hindi', 'bn': 'bengali', 'te': 'telugu', 'mr': 'marathi'
    };
    return mapping[code] || 'french';
}

function getRecognitionLanguageCode(code) {
    const mapping = {
        'en': 'en-US', 'es': 'es-ES', 'de': 'de-DE', 'it': 'it-IT',
        'pt': 'pt-PT', 'ru': 'ru-RU', 'zh-CN': 'zh-CN', 'ja': 'ja-JP',
        'ar': 'ar-SA', 'uk': 'uk-UA', 'fa': 'fa-IR', 'hi': 'hi-IN',
        'bn': 'bn-IN', 'te': 'te-IN', 'mr': 'mr-IN', 'fr': 'fr-FR'
    };
    return mapping[code] || 'fr-FR';
}

/* ========================================
   SYNTHÈSE VOCALE (ANTI-SPAM RENFORCÉ) - FINALISÉE
======================================== */
function speakText(text, language = 'fr', translationId = null) {
    if (!text || text.trim() === '') return;
    
    // Système anti-spam renforcé (CRITIQUE - NE PAS MODIFIER)
    const currentTime = Date.now();
    const translationKey = translationId || `${text.substring(0, 50)}_${language}_${currentTime}`;
    
    // Vérifier si c'est exactement la même traduction (même ID)
    if (translationKey === lastTranslationId) {
        console.log('🔇 Traduction identique ignorée (même ID):', translationKey);
        return;
    }
    
    // Double vérification avec le texte ET le délai
    if (text === lastSpokenText && (currentTime - lastSpokenTimestamp) < 8000) {
        console.log('🔇 Traduction identique ignorée (délai 8s):', text.substring(0, 30) + '...');
        return;
    }
    
    if ('speechSynthesis' in window) {
        // Arrêter toute lecture en cours pour éviter la superposition
        window.speechSynthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = getVoiceLanguageCode(language);
        utterance.volume = 0.8;
        utterance.rate = 0.9;
        utterance.pitch = 1;
        
        // Sélection intelligente de la voix
        const voices = window.speechSynthesis.getVoices();
        const voice = voices.find(v => 
            v.lang.startsWith(utterance.lang.substring(0, 2)) && 
            (v.localService || v.default)
        );
        if (voice) {
            utterance.voice = voice;
        }
        
        utterance.onend = function() {
            console.log('🎵 Lecture terminée:', text.substring(0, 30) + '...');
        };
        
        utterance.onerror = function(error) {
            console.warn('⚠️ Erreur synthèse vocale:', error);
        };
        
        try {
            window.speechSynthesis.speak(utterance);
            console.log('🎵 Audio lancé:', text.substring(0, 30) + '...', 'Langue:', language);
            
            // Mémoriser avec ID unique (CRITIQUE)
            lastSpokenText = text;
            lastSpokenTimestamp = currentTime;
            lastTranslationId = translationKey;
        } catch (error) {
            console.error('❌ Erreur lancement audio:', error);
        }
    } else {
        console.log('❌ Synthèse vocale non disponible');
    }
}

function getVoiceLanguageCode(langCode) {
    const voices = {
        'fr': 'fr-FR', 'en': 'en-US', 'es': 'es-ES', 'de': 'de-DE',
        'it': 'it-IT', 'pt': 'pt-PT', 'ru': 'ru-RU', 'zh-CN': 'zh-CN',
        'ja': 'ja-JP', 'ar': 'ar-SA', 'uk': 'uk-UA', 'hi': 'hi-IN',
        'bn': 'bn-IN', 'te': 'te-IN', 'mr': 'mr-IN', 'fa': 'fa-IR'
    };
    return voices[langCode] || 'fr-FR';
}

/* ========================================
   GESTION D'INCOMPATIBILITÉ MICRO - FINALISÉE
======================================== */
function showMicrophoneIncompatibleMessage() {
    console.log('🎤 Affichage message d\'incompatibilité microphone');
    
    // Utiliser le système TradLive si disponible
    if (window.TradLive?.notifications) {
        const message = getTranslation('mic_incompatible_message') || 
            'Votre navigateur ne peut pas utiliser la reconnaissance vocale avec TradLive.';
        
        window.TradLive.notifications.show(message, 'warning', { duration: 8000 });
        
        setTimeout(() => {
            const solution = getTranslation('use_text_mode') || 
                'Utilisez la zone de saisie ci-dessous pour écrire vos messages.';
            window.TradLive.notifications.show(solution, 'info', { duration: 6000 });
        }, 1000);
    } else {
        // Fallback avec création d'élément
        showIncompatibilityFallback();
    }
}

function showIncompatibilityFallback() {
    const messageDiv = document.createElement('div');
    messageDiv.innerHTML = `
        <div style="text-align: center; margin: 20px 0; padding: 20px; background: rgba(244, 67, 54, 0.9); color: white; border-radius: 15px; border: 2px solid #e74c3c;">
            <h3 style="color: white; margin-bottom: 15px;">🎤 ${getTranslation('mic_incompatible') || 'Microphone non compatible'}</h3>
            <p style="font-size: 16px; margin-bottom: 10px;">
                ${getTranslation('mic_incompatible_message') || 'Votre navigateur ne peut pas utiliser la reconnaissance vocale avec TradLive.'}
            </p>
            <p style="font-size: 14px; opacity: 0.9; margin-bottom: 15px;">
                💡 <strong>${getTranslation('solution') || 'Solution'} :</strong> ${getTranslation('use_text_mode') || 'Utilisez la zone de saisie ci-dessous pour écrire vos messages.'}
            </p>
        </div>
    `;
    
    const controlsEl = document.getElementById('controls');
    if (controlsEl) {
        controlsEl.insertAdjacentElement('beforebegin', messageDiv);
        
        // Animation d'apparition
        setTimeout(() => {
            messageDiv.style.opacity = '0';
            messageDiv.style.transform = 'translateY(-10px)';
            messageDiv.style.transition = 'all 0.5s ease';
            
            requestAnimationFrame(() => {
                messageDiv.style.opacity = '1';
                messageDiv.style.transform = 'translateY(0)';
            });
        }, 100);
    }
}

function cleanInterfaceForTextOnly() {
    console.log('🧹 Nettoyage interface pour mode texte uniquement...');
    
    // Masquer tous les boutons micro avec animation fluide
    document.querySelectorAll('.mic-button').forEach(btn => {
        btn.style.transition = 'all 0.3s ease';
        btn.style.opacity = '0';
        btn.style.transform = 'scale(0.9)';
        
        setTimeout(() => {
            btn.style.display = 'none';
        }, 300);
    });
    
    // Masquer les boutons "Mode Texte" (plus nécessaires)
    document.querySelectorAll('.text-mode-button').forEach(btn => {
        btn.style.transition = 'all 0.3s ease';
        btn.style.opacity = '0';
        
        setTimeout(() => {
            btn.style.display = 'none';
        }, 300);
    });
    
    // Masquer les animations d'onde
    document.querySelectorAll('.wave-animation').forEach(wave => {
        wave.style.display = 'none';
    });
    
    // Afficher automatiquement la zone de saisie
    setTimeout(() => {
        if (isHost) {
            showTextInput();
            console.log('📝 Zone texte hôte activée automatiquement');
        } else {
            showParticipantTextInput();
            console.log('📝 Zone texte participant activée automatiquement');
        }
    }, 500);
    
    // Mettre à jour le statut
    setTimeout(() => {
        const message = getTranslation('text_mode_activated') || 
            'Mode texte activé. Utilisez la zone de saisie ci-dessous.';
        showStatus(message, 'info');
    }, 1000);
}

/* ========================================
   INITIALISATION DE LA SALLE (FONCTION PRINCIPALE) - FINALISÉE
======================================== */
function initializeRoom() {
    console.log('🏠 Initialisation de la salle TradLive (version finale)...');
    
    // Initialiser les éléments DOM
    initializeDOMElements();
    
    // Récupérer les données utilisateur
    const userDataStr = getStorageItem('tradlive_user');
    if (!userDataStr) {
        const message = getTranslation('user_data_missing') || 
            'Données utilisateur manquantes. Retour à l\'accueil...';
        showError(message);
        setTimeout(() => window.location.href = '/rooms', 2000);
        return;
    }
    
    try {
        userData = typeof userDataStr === 'string' ? JSON.parse(userDataStr) : userDataStr;
    } catch (error) {
        console.error('❌ Erreur parsing userData:', error);
        showError('Données utilisateur corrompues. Retour à l\'accueil...');
        setTimeout(() => window.location.href = '/rooms', 2000);
        return;
    }
    
    // Vérifier la cohérence de salle
    const currentRoomId = window.location.pathname.split('/').pop();
    if (userData.room_id !== currentRoomId) {
        showError('Incohérence de salle. Retour à l\'accueil...');
        setTimeout(() => window.location.href = '/rooms', 2000);
        return;
    }
    
    // Initialiser l'interface utilisateur
    setupUserInterface();
    
    // Initialiser les voix de synthèse
    initializeSpeechSynthesis();
    
    // Charger les informations de la salle
    loadRoomInfo();
    
    // Démarrer les systèmes temps réel
    startRealTimeUpdates();
    startHeartbeat();
    
    // Configurer la reconnaissance vocale
    setupSpeechRecognition();
    
    // Finaliser l'initialisation
    finalizeInitialization();
}

function setupUserInterface() {
    // Afficher les informations utilisateur
    const nicknameEl = document.getElementById('user-nickname');
    const languageEl = document.getElementById('user-language');
    const roomCodeEl = document.getElementById('qr-room-code');
    
    if (nicknameEl) nicknameEl.textContent = userData.nickname;
    if (languageEl) languageEl.textContent = getLanguageName(userData.language);
    if (roomCodeEl) roomCodeEl.textContent = userData.room_id;
    
    // Récupérer et appliquer la langue d'interface
    window.interfaceLanguage = getStorageItem('tradlive_language', 'fr');
    
    // Appliquer les traductions
    if (window.applyTranslations && window.interfaceLanguage) {
        applyTranslations(window.interfaceLanguage);
    }
    
    // Animation d'entrée de la page
    setTimeout(() => {
        const container = document.querySelector('.room-container');
        if (container) {
            container.classList.add('loaded');
        }
    }, 100);
}

function initializeSpeechSynthesis() {
    if ('speechSynthesis' in window) {
        // Forcer le chargement des voix
        window.speechSynthesis.getVoices();
        
        window.speechSynthesis.onvoiceschanged = function() {
            const voicesCount = window.speechSynthesis.getVoices().length;
            console.log('🎵 Voix de synthèse disponibles:', voicesCount);
        };
        
        // Pré-charger les voix principales avec un délai
        setTimeout(() => {
            const testLanguages = ['fr-FR', 'en-US', 'es-ES', 'de-DE'];
            testLanguages.forEach(lang => {
                try {
                    const utterance = new SpeechSynthesisUtterance(' ');
                    utterance.lang = lang;
                    utterance.volume = 0;
                    window.speechSynthesis.speak(utterance);
                } catch (error) {
                    console.warn(`⚠️ Erreur pré-chargement voix ${lang}:`, error);
                }
            });
        }, 1000);
    }
}

function finalizeInitialization() {
    // Mettre à jour le QR code
    updateQRCode();
    
    // Configurer les event listeners des boutons
    setupButtonListeners();
    
    // Vérifier la compatibilité du navigateur
    setTimeout(() => {
        checkBrowserCompatibility();
    }, 1000);
    
    // Émettre événement d'initialisation
    if (window.TradLive?.events) {
        window.TradLive.events.emit('room:initialized', {
            roomId: userData.room_id,
            userId: userData.user_id,
            isHost: isHost,
            language: userData.language
        });
    }
    
    console.log('✅ Initialisation de la salle terminée avec succès');
}

function checkBrowserCompatibility() {
    if (window.TradLive?.browser) {
        const browserInfo = window.TradLive.browser.getRecommendations();
        if (browserInfo) {
            showBrowserCompatibilityMessage(browserInfo);
        }
    } else {
        // Vérification basique si TradLive n'est pas disponible
        const isCompatible = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        if (!isCompatible) {
            setTimeout(() => {
                cleanInterfaceForTextOnly();
            }, 500);
        }
    }
}

function showBrowserCompatibilityMessage(compatibilityInfo) {
    console.log('🎨 Évaluation compatibilité navigateur:', compatibilityInfo.level);
    
    if (window.TradLive?.notifications) {
        const type = compatibilityInfo.level === 'excellent' ? 'success' : 
                    compatibilityInfo.level === 'good' ? 'info' : 'warning';
        
        window.TradLive.notifications.show(compatibilityInfo.message, type, { duration: 6000 });
        
        // Afficher les suggestions si nécessaire
        if (compatibilityInfo.suggestions?.length > 0) {
            setTimeout(() => {
                compatibilityInfo.suggestions.forEach((suggestion, index) => {
                    setTimeout(() => {
                        window.TradLive.notifications.show(suggestion, 'info', { duration: 5000 });
                    }, index * 1500);
                });
            }, 1000);
        }
    }
    
    // Actions selon le niveau de compatibilité
    if (compatibilityInfo.level === 'limited') {
        console.log('❌ Compatibilité limitée détectée, basculement mode texte');
        setTimeout(() => {
            cleanInterfaceForTextOnly();
        }, 2000);
    }
}

/* ========================================
   GESTION DES ÉLÉMENTS DOM - FINALISÉE
======================================== */
function initializeDOMElements() {
    const elementIds = [
        'status', 'controls', 'host-controls', 'participant-controls',
        'mic-button', 'participant-mic-button', 'text-mode-button', 'participant-text-button',
        'wave-animation', 'participant-wave', 'qr-section', 'qr-code-image', 'connection-status',
        'text-input-fallback', 'participant-text-input',
        'host-interface', 'participant-interface',
        'host-original-text', 'host-responses-text',
        'participant-original-text', 'participant-translated-text', 'participant-message-area',
        'participant-own-text', 'participant-french-text', 'participant-target-language',
        'participants-list', 'participant-count'
    ];
    
    const elements = {};
    elementIds.forEach(id => {
        elements[id] = document.getElementById(id);
        if (!elements[id]) {
            console.warn(`⚠️ Élément DOM non trouvé: ${id}`);
        }
    });
    
    // Assignation globale pour compatibilité
    Object.assign(window, {
        statusEl: elements['status'],
        controlsEl: elements['controls'],
        hostControlsEl: elements['host-controls'],
        participantControlsEl: elements['participant-controls'],
        micButton: elements['mic-button'],
        participantMicButton: elements['participant-mic-button'],
        textModeButton: elements['text-mode-button'],
        participantTextButton: elements['participant-text-button'],
        waveAnimation: elements['wave-animation'],
        participantWave: elements['participant-wave'],
        qrSection: elements['qr-section'],
        qrCodeImage: elements['qr-code-image'],
        connectionStatus: elements['connection-status'],
        textInputFallback: elements['text-input-fallback'],
        participantTextInput: elements['participant-text-input'],
        hostInterface: elements['host-interface'],
        participantInterface: elements['participant-interface'],
        hostOriginalText: elements['host-original-text'],
        hostResponsesText: elements['host-responses-text'],
        participantOriginalText: elements['participant-original-text'],
        participantTranslatedText: elements['participant-translated-text'],
        participantMessageArea: elements['participant-message-area'],
        participantOwnText: elements['participant-own-text'],
        participantFrenchText: elements['participant-french-text'],
        participantTargetLanguage: elements['participant-target-language'],
        participantsListEl: elements['participants-list'],
        participantCountEl: elements['participant-count']
    });
}

/* ========================================
   CHARGEMENT DES INFORMATIONS DE SALLE - FINALISÉ
======================================== */
function loadRoomInfo() {
    const url = `/api/room/${userData.room_id}/info`;
    
    makeApiRequest(url)
        .then(data => {
            if (data.success) {
                roomData = data.data ? data.data.room : data.room;
                reconnectAttempts = 0;
                updateConnectionStatus(true);
                
                // Identifier le rôle de l'utilisateur
                const currentUser = roomData.users.find(u => u.user_id === userData.user_id);
                if (currentUser) {
                    isHost = currentUser.is_host;
                    setupRoleInterface();
                    updateParticipantsList();
                    
                    // Émettre événement de connexion
                    if (window.TradLive?.events) {
                        window.TradLive.events.emit('room:connected', {
                            roomData: roomData,
                            isHost: isHost
                        });
                    }
                } else {
                    throw new Error('Utilisateur non trouvé dans la salle');
                }
            } else {
                throw new Error(data.error || 'Erreur inconnue');
            }
        })
        .catch(error => {
            console.error('❌ Erreur chargement salle:', error);
            handleConnectionError();
        });
}

function setupRoleInterface() {
    // CORRECTION : Éviter les appels multiples
    const alreadyConfigured = document.querySelector('.role-configured');
    if (alreadyConfigured) {
        return; // Interface déjà configurée
    }
    
    if (isHost) {
        // Interface hôte
        showElement('host-controls');
        showElement('host-interface');
        
        const qrSection = document.getElementById('qr-section');
        if (qrSection) {
            qrSection.classList.add('show');
        }
        
        // Marquer comme configuré
        document.body.classList.add('role-configured');
        
        console.log('👑 Interface hôte configurée');
    } else {
        // Interface participant
        showElement('participant-controls');
        showElement('participant-interface');
        
        // Marquer comme configuré  
        document.body.classList.add('role-configured');
        
        console.log('👤 Interface participant configurée');
    }
    
    // Afficher les contrôles communs
    showElement('controls');
    animateElement('controls', 'slideInUp');
}

function handleConnectionError() {
    reconnectAttempts++;
    updateConnectionStatus(false);
    
    if (reconnectAttempts < maxReconnectAttempts) {
        const delay = Math.min(reconnectAttempts * 1000, 5000);
        console.log(`🔄 Tentative de reconnexion ${reconnectAttempts}/${maxReconnectAttempts} dans ${delay}ms`);
        
        setTimeout(() => loadRoomInfo(), delay);
    } else {
        const message = getTranslation('connection_failed') || 
            'Impossible de se connecter à la salle';
        showError(message);
        
        // Proposer le retour aux salles
        setTimeout(() => {
            const confirmMessage = getTranslation('return_to_rooms') || 
                'Retourner à la liste des salles ?';
            if (confirm(confirmMessage)) {
                window.location.href = '/rooms';
            }
        }, 3000);
    }
}

function updateConnectionStatus(connected) {
    // Mettre à jour les DEUX éléments de statut
    const connectionStatus = document.getElementById('connection-status');
    const mainStatus = document.getElementById('status');
    
    if (connected) {
        const message = getTranslation('connected') || 'Connecté ✅';
        
        // Petit statut en-tête
        if (connectionStatus) {
            connectionStatus.textContent = message;
            connectionStatus.style.color = '#4CAF50';
        }
        
        // Gros statut principal
        if (mainStatus) {
            mainStatus.textContent = message;
            mainStatus.className = 'status connected show';
        }
        
        animateElement('connection-status', 'pulse');
    } else {
        const message = getTranslation('reconnecting') || 
            `Reconnexion... (${reconnectAttempts}/${maxReconnectAttempts})`;
            
        // Petit statut en-tête
        if (connectionStatus) {
            connectionStatus.textContent = message;
            connectionStatus.style.color = '#f44336';
        }
        
        // Gros statut principal  
        if (mainStatus) {
            mainStatus.textContent = message;
            mainStatus.className = 'status error show';
        }
        
        animateElement('connection-status', 'shake');
    }
}

function updateParticipantsList() {
    const participantsListEl = document.getElementById('participants-list');
    const participantCountEl = document.getElementById('participant-count');
    
    if (!roomData?.users || !participantsListEl || !participantCountEl) return;
    
    const userCount = roomData.users.length;
    
    // CORRECTION : Éviter la recréation si rien n'a changé
    const currentCount = participantCountEl.textContent;
    if (currentCount === userCount.toString() && participantsListEl.children.length > 0) {
        return; // Liste identique, pas de recréation
    }
    
    participantCountEl.textContent = userCount;
    
    if (userCount === 0) {
        const message = getTranslation('no_participants') || 'Aucun participant';
        participantsListEl.innerHTML = `<div class="loading">${message}</div>`;
        return;
    }
    
    const hostBadgeText = getTranslation('host_badge') || 'HÔTE';
    
    participantsListEl.innerHTML = roomData.users.map(user => `
        <div class="participant">
            <div>
                <span class="participant-name">${escapeHtml(user.nickname)}</span>
                ${user.is_host ? `<span class="host-badge">${hostBadgeText}</span>` : ''}
            </div>
            <span class="participant-language">${getLanguageName(user.language)}</span>
        </div>
    `).join('');
    
    // Animation staggerée des participants
    const participants = document.querySelectorAll('.participant');
    participants.forEach((participant, index) => {
        setTimeout(() => {
            animateElement(participant, 'slideInLeft');
        }, index * 100);
    });
}

/* ========================================
   RECONNAISSANCE VOCALE - FINALISÉE
======================================== */
function setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        console.log('❌ API de reconnaissance vocale non disponible');
        const message = getTranslation('speech_not_supported') || 
            'Reconnaissance vocale non supportée. Utilisez le mode texte.';
        showError(message);
        cleanInterfaceForTextOnly();
        return;
    }
    
    try {
        if (isHost) {
            setupHostRecognition(SpeechRecognition);
        } else {
            setupParticipantRecognition(SpeechRecognition);
        }
        console.log('✅ Reconnaissance vocale configurée avec succès');
    } catch (error) {
        console.error('❌ Erreur configuration reconnaissance vocale:', error);
        cleanInterfaceForTextOnly();
    }
}

function setupHostRecognition(SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.lang = 'fr-FR';
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    
    recognition.onresult = function(event) {
        const lastResultIndex = event.results.length - 1;
        const transcript = event.results[lastResultIndex][0].transcript;
        
        if (event.results[lastResultIndex].isFinal) {
            sendHostTranslation(transcript);
        } else {
            updateHostOriginalText(transcript);
        }
    };
    
    recognition.onerror = function(event) {
        console.error('❌ Erreur reconnaissance hôte:', event.error);
        handleRecognitionError(event.error, 'host');
    };
    
    recognition.onend = function() {
        if (isListening) {
            tryRestartRecognition(recognition, 'host');
        }
    };
}

function setupParticipantRecognition(SpeechRecognition) {
    participantRecognition = new SpeechRecognition();
    participantRecognition.lang = getRecognitionLanguageCode(userData.language);
    participantRecognition.continuous = true;
    participantRecognition.interimResults = true;
    participantRecognition.maxAlternatives = 1;
    
    participantRecognition.onresult = function(event) {
        const lastResultIndex = event.results.length - 1;
        const transcript = event.results[lastResultIndex][0].transcript;
        
        if (event.results[lastResultIndex].isFinal) {
            sendParticipantTranslation(transcript);
        } else {
            const message = getTranslation('recognizing') || 'En cours: ';
            showStatus(message + transcript, 'info');
        }
    };
    
    participantRecognition.onerror = function(event) {
        console.error('❌ Erreur reconnaissance participant:', event.error);
        handleRecognitionError(event.error, 'participant');
    };
    
    participantRecognition.onend = function() {
        if (isParticipantListening) {
            tryRestartRecognition(participantRecognition, 'participant');
        }
    };
}

function tryRestartRecognition(recognitionInstance, type) {
    try {
        recognitionInstance.start();
    } catch (error) {
        console.warn(`⚠️ Impossible de redémarrer la reconnaissance ${type}:`, error);
        if (type === 'host') {
            stopHostListening();
        } else {
            stopParticipantListening();
        }
    }
}

function handleRecognitionError(error, type) {
    switch (error) {
        case 'network':
            handleNetworkError(type);
            break;
        case 'not-allowed':
            handlePermissionError(type);
            break;
        case 'no-speech':
            console.log('🤫 Pas de parole détectée, continue...');
            break;
        default:
            handleGenericError(error, type);
    }
}

function handleNetworkError(type) {
    networkErrorCount++;
    console.log(`🌐 Problème réseau (${networkErrorCount}/3), réessai...`);
    
    if (networkErrorCount >= 3) {
        console.log('❌ Trop d\'erreurs réseau, basculement mode texte');
        
        if (window.TradLive?.notifications) {
            window.TradLive.notifications.show(
                'Connexion instable détectée. Basculement en mode texte.',
                'warning',
                { duration: 8000 }
            );
        }
        
        cleanInterfaceForTextOnly();
        type === 'host' ? stopHostListening() : stopParticipantListening();
        return;
    }
    
    const message = getTranslation('network_problem') || 
        `Problème réseau, nouvelle tentative... (${networkErrorCount}/3)`;
    showStatus(message, 'info');
}

function handlePermissionError(type) {
    const message = getTranslation('mic_permission_error') || 
        '❌ Autorisez le microphone et rechargez la page.';
    showError(message);
    
    if (window.TradLive?.notifications) {
        window.TradLive.notifications.show(
            'Accès au microphone requis',
            'error',
            { duration: 10000 }
        );
    }
    
    type === 'host' ? stopHostListening() : stopParticipantListening();
}

function handleGenericError(error, type) {
    console.log('❌ Erreur reconnaissance:', error);
    const message = getTranslation('mic_problem') || 
        'Problème micro. Mode texte activé.';
    showError(message);
    
    if (type === 'host') {
        showTextInput();
        stopHostListening();
    } else {
        showParticipantTextInput();
        stopParticipantListening();
    }
}

/* ========================================
   CONTRÔLES MICROPHONE - FINALISÉS
======================================== */
function toggleHostListening() {
    console.log('🎤 Toggle micro hôte, état actuel:', isListening);
    isListening ? stopHostListening() : startHostListening();
}

function startHostListening() {
    console.log('🎤 Démarrage micro hôte...');
    
    if (!recognition) {
        console.log('⚠️ Recréation de la reconnaissance...');
        setupSpeechRecognition();
        if (!recognition) {
            console.log('❌ Échec création reconnaissance, mode texte');
            showTextInput();
            return;
        }
    }
    
    // Demander permission microphone
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(() => {
            try {
                recognition.start();
                isListening = true;
                networkErrorCount = 0;
                
                updateMicButtonState(micButton, true, 'stop_button');
                showElement(waveAnimation, true);
                
                const message = getTranslation('listening_french') || 
                    'En écoute... Parlez en français.';
                showStatus(message, 'info');
                
                notifySuccess('🎤 Microphone activé');
                console.log('✅ Reconnaissance vocale hôte démarrée');
            } catch (error) {
                console.error('❌ Erreur démarrage reconnaissance:', error);
                handleStartupError('host');
            }
        })
        .catch(error => {
            console.error('❌ Erreur accès microphone hôte:', error);
            handleMicrophoneAccessError('host');
        });
}

function stopHostListening() {
    if (recognition) recognition.stop();
    isListening = false;
    
    updateMicButtonState(micButton, false, 'speak_french');
    hideElement(waveAnimation);
    
    const message = getTranslation('click_mic') || 
        'Cliquez sur le micro pour parler.';
    showStatus(message, 'connected');
    
    console.log('🎤 Microphone hôte arrêté');
}

function toggleParticipantListening() {
    console.log('🎤 Toggle micro participant, état actuel:', isParticipantListening);
    isParticipantListening ? stopParticipantListening() : startParticipantListening();
}

function startParticipantListening() {
    console.log('🎤 Démarrage micro participant...');
    
    if (!participantRecognition) {
        console.log('⚠️ Recréation de la reconnaissance participant...');
        setupSpeechRecognition();
        if (!participantRecognition) {
            console.log('❌ Échec création reconnaissance participant, mode texte');
            showParticipantTextInput();
            return;
        }
    }
    
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(() => {
            try {
                participantRecognition.start();
                isParticipantListening = true;
                
                updateMicButtonState(participantMicButton, true, 'stop_button');
                showElement(participantWave, true);
                
                const langName = getLanguageName(userData.language);
                const message = getTranslation('listening_your_language') || 
                    `En écoute... Parlez en ${langName}.`;
                showStatus(message, 'info');
                
                notifySuccess('🎤 Microphone activé');
                console.log('✅ Reconnaissance vocale participant démarrée');
            } catch (error) {
                console.error('❌ Erreur démarrage reconnaissance participant:', error);
                handleStartupError('participant');
            }
        })
        .catch(error => {
            console.error('❌ Erreur accès microphone participant:', error);
            handleMicrophoneAccessError('participant');
        });
}

function stopParticipantListening() {
    if (participantRecognition) participantRecognition.stop();
    isParticipantListening = false;
    
    updateMicButtonState(participantMicButton, false, 'speak_your_language');
    hideElement(participantWave);
    
    const message = getTranslation('click_mic') || 
        'Cliquez sur le micro pour parler.';
    showStatus(message, 'connected');
    
    console.log('🎤 Microphone participant arrêté');
}

function updateMicButtonState(button, isActive, textKey) {
    if (!button) return;
    
    const text = getTranslation(textKey) || button.textContent;
    button.textContent = text;
    
    if (isActive) {
        button.classList.add('active');
    } else {
        button.classList.remove('active');
    }
}

function handleStartupError(type) {
    const message = getTranslation('recognition_start_error') || 
        'Erreur démarrage reconnaissance. Mode texte activé.';
    showError(message);
    
    if (type === 'host') {
        showTextInput();
    } else {
        showParticipantTextInput();
    }
}

function handleMicrophoneAccessError(type) {
    const message = getTranslation('mic_access_error') || 
        'Impossible d\'accéder au microphone. Mode texte activé.';
    showError(message);
    
    if (type === 'host') {
        showTextInput();
    } else {
        showParticipantTextInput();
    }
}

/* ========================================
   ENVOI DES TRADUCTIONS - FINALISÉ
======================================== */
function sendHostTranslation(text) {
    if (!text?.trim()) return;
    
    console.log('📤 Envoi traduction hôte:', text.substring(0, 50) + '...');
    
    const message = getTranslation('broadcasting') || 
        'Diffusion de la traduction...';
    showStatus(message, 'info');
    
    updateHostOriginalText(text);
    
    const requestData = {
        user_id: userData.user_id,
        text: text,
        source_language: 'fr'
    };
    
    makeApiRequest(`/api/room/${userData.room_id}/translate`, 'POST', requestData)
        .then(data => {
            if (data.success) {
                const successMessage = getTranslation('message_sent') || 
                    'Message diffusé avec synthèse vocale !';
                showStatus(successMessage, 'connected');
                
                notifySuccess('📤 Message diffusé');
                
                // Émettre événement
                emitEvent('translation:sent', {
                    text: text,
                    type: 'host',
                    language: 'fr'
                });
            } else {
                throw new Error(data.error || 'Erreur de traduction');
            }
        })
        .catch(error => {
            console.error('❌ Erreur envoi traduction hôte:', error);
            showError('Erreur envoi traduction: ' + error.message);
            notifyError('Erreur d\'envoi');
        });
}

function sendParticipantTranslation(text) {
    if (!text?.trim()) return;
    
    console.log('📤 Envoi traduction participant:', text.substring(0, 50) + '...');
    
    const message = getTranslation('sending_response') || 
        'Envoi de votre réponse...';
    showStatus(message, 'info');
    
    updateParticipantOwnText(text);
    
    const requestData = {
        user_id: userData.user_id,
        text: text,
        source_language: userData.language,
        target_language: 'fr'
    };
    
    makeApiRequest(`/api/room/${userData.room_id}/translate`, 'POST', requestData)
        .then(data => {
            if (data.success) {
                const successMessage = getTranslation('response_sent') || 
                    'Réponse envoyée à l\'hôte !';
                showStatus(successMessage, 'connected');
                
                notifySuccess('📤 Réponse envoyée');
                
                updateParticipantFrenchText();
                
                // Émettre événement
                emitEvent('translation:sent', {
                    text: text,
                    type: 'participant',
                    language: userData.language
                });
            } else {
                throw new Error(data.error || 'Erreur de traduction');
            }
        })
        .catch(error => {
            console.error('❌ Erreur envoi traduction participant:', error);
            showError('Erreur envoi traduction: ' + error.message);
            notifyError('Erreur d\'envoi');
        });
}

function updateHostOriginalText(text) {
    if (hostOriginalText) {
        hostOriginalText.textContent = text;
        hostOriginalText.classList.remove('empty-translation');
        animateElement(hostOriginalText, 'pulse');
    }
}

function updateParticipantOwnText(text) {
    if (participantOwnText && participantMessageArea) {
        participantOwnText.textContent = text;
        showElement(participantMessageArea);
        animateElement(participantMessageArea, 'slideInUp');
    }
}

function updateParticipantFrenchText() {
    if (participantFrenchText) {
        const translatingMessage = getTranslation('translating') || 
            'Traduction en cours...';
        participantFrenchText.textContent = translatingMessage;
        animateElement(participantFrenchText, 'pulse');
    }
}

/* ========================================
   MODE TEXTE - FINALISÉ
======================================== */
function showTextInput() {
    console.log('📝 Affichage mode texte hôte');
    if (textInputFallback) {
        textInputFallback.classList.add('show');
        
        const textInput = document.getElementById('text-input');
        if (textInput) {
            setTimeout(() => textInput.focus(), 300);
        }
        
        animateElement(textInputFallback, 'slideInUp');
        console.log('✅ Mode texte hôte activé');
    }
}

function hideTextInput() {
    console.log('📝 Masquage mode texte hôte');
    if (textInputFallback) {
        textInputFallback.classList.remove('show');
        animateElement(textInputFallback, 'fadeOut');
    }
}

function sendHostText() {
    const textInput = document.getElementById('text-input');
    if (!textInput) return;
    
    const text = textInput.value.trim();
    if (text) {
        sendHostTranslation(text);
        textInput.value = '';
        hideTextInput();
    }
}

function showParticipantTextInput() {
    console.log('📝 Affichage mode texte participant');
    if (participantTextInput) {
        participantTextInput.classList.add('show');
        
        const textInput = document.getElementById('participant-text');
        if (textInput) {
            setTimeout(() => textInput.focus(), 300);
        }
        
        animateElement(participantTextInput, 'slideInUp');
        console.log('✅ Mode texte participant activé');
    }
}

function hideParticipantTextInput() {
    console.log('📝 Masquage mode texte participant');
    if (participantTextInput) {
        participantTextInput.classList.remove('show');
        animateElement(participantTextInput, 'fadeOut');
    }
}

function sendParticipantText() {
    const textInput = document.getElementById('participant-text');
    if (!textInput) return;
    
    const text = textInput.value.trim();
    if (text) {
        sendParticipantTranslation(text);
        textInput.value = '';
        hideParticipantTextInput();
    }
}

/* ========================================
   MISES À JOUR TEMPS RÉEL - FINALISÉES
======================================== */
function startRealTimeUpdates() {
      // CORRECTION : Éviter les intervals multiples
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
    }
    
    updateInterval = setInterval(() => {
        const url = `/api/room/${userData.room_id}/updates?user_id=${userData.user_id}`;
        
        makeApiRequest(url)
            .then(data => {
                if (data.success) {
                    reconnectAttempts = 0;
                    updateConnectionStatus(true);
                    processRoomUpdates(data);
                    
                    // Émettre événement de mise à jour
                    emitEvent('room:updated', data);
                }
            })
            .catch(error => {
                console.error('❌ Erreur mise à jour:', error);
                reconnectAttempts++;
                updateConnectionStatus(false);
                
                // Notification après plusieurs échecs
                if (reconnectAttempts >= 3) {
                    notifyWarning('Problème de connexion détecté');
                }
            });
        
        // Recharger les infos de salle périodiquement
        if (Date.now() % 20000 < 3000) {
            loadRoomInfo();
        }
    }, 3000);
    
    console.log('🔄 Mises à jour temps réel démarrées');
}

function processRoomUpdates(data) {
    if (isHost) {
        // Interface hôte : afficher les réponses des participants
        if (data.original && !data.show_translation) {
            if (hostResponsesText) {
                hostResponsesText.textContent = data.original;
                hostResponsesText.classList.remove('empty-translation');
                animateElement(hostResponsesText, 'pulse');
            }
        }
    } else {
        // Interface participant : afficher les messages de l'hôte traduits
        if (data.original && data.show_translation) {
            if (participantOriginalText) {
                participantOriginalText.textContent = data.original;
                participantOriginalText.classList.remove('empty-translation');
            }
            
            if (data.translated && participantTranslatedText) {
                participantTranslatedText.textContent = data.translated;
                participantTranslatedText.classList.remove('empty-translation');
                animateElement(participantTranslatedText, 'pulse');
                
                // Synthèse vocale avec ID unique pour éviter les répétitions
                if (data.enable_speech) {
                    const translationId = `${data.timestamp}_${data.translated.substring(0, 20)}`;
                    console.log('🎵 Lecture traduction:', data.translated.substring(0, 30) + '...');
                    speakText(data.translated, userData.language, translationId);
                }
            }
        }
    }
}

function startHeartbeat() {
    heartbeatInterval = setInterval(() => {
        const url = `/api/room/${userData.room_id}/heartbeat`;
        const requestData = { user_id: userData.user_id };
        
        makeApiRequest(url, 'POST', requestData)
            .catch(error => {
                console.warn('⚠️ Heartbeat échoué:', error);
                reconnectAttempts++;
                updateConnectionStatus(false);
            });
    }, 10000);
    
    console.log('💓 Heartbeat démarré');
}

/* ========================================
   FONCTIONS UTILITAIRES - FINALISÉES
======================================== */
function setupButtonListeners() {
    console.log('🔧 Configuration des événements boutons...');

    // DIAGNOSTIC : Vérifier si les boutons existent
    //console.log('micButton:', micButton);
    //console.log('textModeButton:', textModeButton);
    //console.log('participantMicButton:', participantMicButton);
    //console.log('participantTextButton:', participantTextButton);

    // DIAGNOSTIC DIRECT : Chercher les éléments dans le DOM
    //console.log('Direct mic-button:', document.getElementById('mic-button'));
    //console.log('Direct text-mode-button:', document.getElementById('text-mode-button'));
    //console.log('Direct participant-mic-button:', document.getElementById('participant-mic-button'));
    //console.log('Direct participant-text-button:', document.getElementById('participant-text-button'));

       // SOLUTION : Utiliser directement getElementById
    const micBtn = document.getElementById('mic-button');
    const textBtn = document.getElementById('text-mode-button');
    const partMicBtn = document.getElementById('participant-mic-button');
    const partTextBtn = document.getElementById('participant-text-button');
    
    // Debouncing pour éviter les clics multiples
    const debouncedToggleHost = debounce(toggleHostListening, 300);
    const debouncedToggleParticipant = debounce(toggleParticipantListening, 300);
    
    // Boutons hôte
    addEventListenerOnce(micButton, 'click', debouncedToggleHost);
    addEventListenerOnce(textModeButton, 'click', showTextInput);
    
    // Boutons participant
    addEventListenerOnce(participantMicButton, 'click', debouncedToggleParticipant);
    addEventListenerOnce(participantTextButton, 'click', showParticipantTextInput);
    
    console.log('✅ Événements boutons configurés');
}

function addEventListenerOnce(element, event, handler) {
    if (element && !element.hasAttribute('data-listener')) {
        element.addEventListener(event, handler);
        element.setAttribute('data-listener', 'true');
    }
}

function updateQRCode() {
    if (!qrCodeImage) return;
    
    const roomUrl = `${window.location.origin}/room/${userData.room_id}?auto_join=true`;
    // SUPPRESSION du timestamp qui causait les rechargements
    qrCodeImage.src = `/qrcode?url=${encodeURIComponent(roomUrl)}`;
    
    qrCodeImage.onerror = function() {
        console.warn('⚠️ Erreur chargement QR code');
        this.style.display = 'none';
        
        const fallback = document.createElement('div');
        fallback.innerHTML = `
            <div style="padding: 20px; text-align: center; background: #f0f0f0; border-radius: 10px; color: #333;">
                <h3>🔗 Lien de partage</h3>
                <p style="font-family: monospace; word-break: break-all; font-size: 12px;">${roomUrl}</p>
            </div>
        `;
        this.parentNode.appendChild(fallback);
    };
}

function leaveRoom() {
    const confirmMessage = getTranslation('confirm_leave') || 
        'Êtes-vous sûr de vouloir quitter la salle ?';
    
    if (confirm(confirmMessage)) {
        console.log('🚪 Départ de la salle...');
        
        notifyInfo('Déconnexion en cours...');
        
        // Arrêter toutes les activités
        cleanup();
        
        // Émettre événement de départ
        emitEvent('room:leaving', {
            roomId: userData.room_id,
            userId: userData.user_id
        });
        
        // Notifier le serveur
        const requestData = { user_id: userData.user_id };
        makeApiRequest(`/api/room/${userData.room_id}/leave`, 'POST', requestData)
            .finally(() => {
                // Nettoyer le stockage et rediriger
                removeStorageItem('tradlive_user');
                window.location.href = '/rooms';
            });
    }
}

function cleanup() {
    console.log('🧹 Nettoyage des ressources...');
    
    // Arrêter les intervalles
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
    }
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
    }
    
    // Arrêter la reconnaissance vocale
    if (isListening) stopHostListening();
    if (isParticipantListening) stopParticipantListening();
    
    // Arrêter la synthèse vocale
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
}

/* ========================================
   FONCTIONS D'AIDE - FINALISÉES
======================================== */
function getTranslation(key, defaultValue = null) {
    if (window.TRADLIVE_TRANSLATIONS && window.interfaceLanguage) {
        return window.TRADLIVE_TRANSLATIONS[window.interfaceLanguage][key] || defaultValue || key;
    }
    return defaultValue || key;
}

function getStorageItem(key, defaultValue = null) {
    if (window.TradLive?.storage) {
        return window.TradLive.storage.get(key, defaultValue);
    }
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch {
        return defaultValue;
    }
}

function setStorageItem(key, value) {
    if (window.TradLive?.storage) {
        return window.TradLive.storage.set(key, value);
    }
    try {
        localStorage.setItem(key, JSON.stringify(value));
        return true;
    } catch {
        return false;
    }
}

function removeStorageItem(key) {
    if (window.TradLive?.storage) {
        return window.TradLive.storage.remove(key);
    }
    try {
        localStorage.removeItem(key);
        return true;
    } catch {
        return false;
    }
}

function makeApiRequest(url, method = 'GET', data = null) {
    if (window.TradLive?.network) {
        return method === 'GET' ? 
            window.TradLive.network.get(url) : 
            window.TradLive.network.post(url, data);
    }
    
    // Fallback sans TradLive
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    
    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }
    
    return fetch(url, options)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        });
}

function animateElement(element, animationType = 'fadeIn') {
    // Si c'est une string, récupérer l'élément par ID
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    
    if (!element) return;
    
    if (window.TradLive?.animations && window.TradLive.animations[animationType]) {
        window.TradLive.animations[animationType](element);
    } else {
        // Fallback CSS simple
        element.style.animation = `${animationType} 0.3s ease`;
        setTimeout(() => {
            element.style.animation = '';
        }, 300);
    }
}

function showElement(element, addClass = false) {
    // Si c'est une string, récupérer l'élément par ID
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    
    if (element) {
        element.style.display = 'block';
        if (addClass && element.classList) {
            element.classList.add('active');
        }
    }
}

function hideElement(element) {
    if (element) {
        element.style.display = 'none';
        if (element.classList) {
            element.classList.remove('active');
        }
    }
}

function showStatus(message, type = 'info') {
    if (!statusEl) return;
    
    statusEl.textContent = message;
    statusEl.className = `status ${type}`;
    statusEl.style.display = 'block';
    
    animateElement(statusEl, 'slideInUp');
}

function showError(message) {
    console.error('💥 Erreur:', message);
    showStatus(message, 'error');
    
    if (statusEl) {
        animateElement(statusEl, 'shake');
    }
    
    notifyError(message);
}

function notifySuccess(message) {
    if (window.TradLive?.notifications) {
        window.TradLive.notifications.show(message, 'success', { duration: 3000 });
    }
}

function notifyError(message) {
    if (window.TradLive?.notifications) {
        window.TradLive.notifications.show(message, 'error', { duration: 5000 });
    }
}

function notifyWarning(message) {
    if (window.TradLive?.notifications) {
        window.TradLive.notifications.show(message, 'warning', { duration: 5000 });
    }
}

function notifyInfo(message) {
    if (window.TradLive?.notifications) {
        window.TradLive.notifications.show(message, 'info', { duration: 2000 });
    }
}

function emitEvent(eventName, data = {}) {
    if (window.TradLive?.events) {
        window.TradLive.events.emit(eventName, data);
    }
}

function debounce(func, wait) {
    if (window.TradLive?.utils?.debounce) {
        return window.TradLive.utils.debounce(func, wait);
    }
    
    // Fallback simple
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

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/* ========================================
   GESTION DES ÉVÉNEMENTS GLOBAUX - FINALISÉE
======================================== */
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        if (document.getElementById('text-input') === document.activeElement) {
            e.preventDefault();
            sendHostText();
        } else if (document.getElementById('participant-text') === document.activeElement) {
            e.preventDefault();
            sendParticipantText();
        }
    }
    
    // Raccourcis clavier avancés
    if (e.ctrlKey || e.metaKey) {
        switch(e.key) {
            case 'm': // Ctrl+M pour microphone
                e.preventDefault();
                isHost ? toggleHostListening() : toggleParticipantListening();
                break;
            case 't': // Ctrl+T pour mode texte
                e.preventDefault();
                isHost ? showTextInput() : showParticipantTextInput();
                break;
            case 'q': // Ctrl+Q pour quitter
                e.preventDefault();
                leaveRoom();
                break;
        }
    }
});

window.addEventListener('beforeunload', function(e) {
    cleanup();
    
    // Envoyer signal de déconnexion optimisé
    if (userData && navigator.sendBeacon) {
        const data = JSON.stringify({ user_id: userData.user_id });
        navigator.sendBeacon(`/api/room/${userData.room_id}/leave`, data);
    }
    
    emitEvent('room:beforeunload', {
        roomId: userData?.room_id,
        userId: userData?.user_id
    });
});

// Optimisation batterie pour mobile
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('📱 Page cachée, optimisation batterie');
        // CORRECTION : Bien nettoyer l'ancien interval
        if (updateInterval) {
            clearInterval(updateInterval);
            updateInterval = null;
        }
        // Créer un interval moins fréquent pour heartbeat seulement
        updateInterval = setInterval(() => {
            const requestData = { user_id: userData.user_id };
            makeApiRequest(`/api/room/${userData.room_id}/heartbeat`, 'POST', requestData)
                .catch(() => console.warn('⚠️ Heartbeat failed while hidden'));
        }, 10000);
    } else {
        console.log('📱 Page visible, restauration normale');
        // CORRECTION : Bien nettoyer avant de recréer
        if (updateInterval) {
            clearInterval(updateInterval);
            updateInterval = null;
        }
        // Redémarrer les mises à jour normales
        startRealTimeUpdates();
    }
});

/* ========================================
   INITIALISATION AUTOMATIQUE - FINALISÉE
======================================== */
document.addEventListener('DOMContentLoaded', function() {
    console.log('🏠 TradLive - Initialisation de la salle de traduction...');
    
    // Initialiser la langue d'interface
    window.interfaceLanguage = getStorageItem('tradlive_language', 'fr');
    
    // Appliquer les traductions immédiatement
    if (window.applyTranslations && window.interfaceLanguage) {
        applyTranslations(window.interfaceLanguage);
    }
    
    // Animation d'entrée de page
    setTimeout(() => {
        const container = document.querySelector('.room-container');
        if (container) {
            container.classList.add('loaded');
        }
    }, 100);
    
    // Initialiser la logique de la salle
    try {
        initializeRoom();
    } catch (error) {
        console.error('❌ Erreur critique lors de l\'initialisation:', error);
        showError('Erreur d\'initialisation. Veuillez recharger la page.');
    }
});

/* ========================================
   EXPORT DES FONCTIONS GLOBALES - FINALISÉ
======================================== */
// Export sécurisé des fonctions principales
const exportedFunctions = {
    initializeRoom,
    leaveRoom,
    showTextInput,
    hideTextInput,
    sendHostText,
    showParticipantTextInput,
    hideParticipantTextInput,
    sendParticipantText,
    toggleHostListening,
    toggleParticipantListening,
    showStatus,
    showError,
    getLanguageName,
    cleanup
};

Object.entries(exportedFunctions).forEach(([name, func]) => {
    if (typeof func === 'function') {
        window[name] = func;
    }
});

// Émettre événement de chargement
if (window.TradLive?.events) {
    window.TradLive.events.on('app:ready', function() {
        console.log('🎤 Room.js intégré avec le framework TradLive');
    });
}

console.log('✅ TradLive Room.js VERSION FINALE chargé - Production Ready');
console.log('🌐 Application déployée sur: https://tradlive-app.onrender.com');

// Vérification d'intégration finale
setTimeout(() => {
    const integrationCheck = {
        translations: !!window.TRADLIVE_TRANSLATIONS,
        common: !!window.TradLive,
        roomLogic: typeof initializeRoom === 'function',
        voiceRecognition: 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window,
        speechSynthesis: 'speechSynthesis' in window
    };
    
    console.log('🔍 Vérification intégration finale:', integrationCheck);
    
    const score = Object.values(integrationCheck).filter(Boolean).length;
    console.log(`📊 Score d'intégration: ${score}/5 (${score >= 4 ? '✅ Excellent' : score >= 3 ? '⚠️ Bon' : '❌ Problème'})`);
}, 1000);
