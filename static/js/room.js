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
let currentStream = null; // Pour stocker le stream audio
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

// Variables pour éviter la lecture en boucle (CRITIQUE - NE PAS MODIFIER)
let lastSpokenText = '';
let lastSpokenTimestamp = 0;
let lastTranslationId = null;
let networkErrorCount = 0;

// VARIABLES POUR AUTO-STOP 15S
let silenceTimer = null;
let audioContext = null;
let analyser = null;
let microphone = null;
let dataArray = null;
let silenceThreshold = 30; // Seuil de silence (0-255)
let silenceTimeout = 15000; // 15 secondes

// Éléments DOM (seront initialisés au chargement)
let statusEl, controlsEl, hostControlsEl, participantControlsEl;
let micButton, participantMicButton, textModeButton, participantTextButton;
let waveAnimation, participantWave, qrSection, qrCodeImage;
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
    // Système unifié avec translations.js pour traduire selon l'interface
    if (window.getTranslation && window.interfaceLanguage) {
        const langKey = `lang_${getLangKey(code)}`;
        const translatedName = window.getTranslation(langKey, window.interfaceLanguage);
        
        // Si la traduction existe, l'utiliser
        if (translatedName && translatedName !== langKey) {
            return translatedName;
        }
    }
    
    // Fallback robuste
    const languageNames = {
        fr: "Français", en: "English", es: "Español", 
        de: "Deutsch", it: "Italiano", pt: "Português",
        ru: "Русский", "zh-CN": "中文", ja: "日本語",
        ar: "العربية", uk: "Українська", fa: "فارسی",
        hi: "हिन्दी", bn: "বাংলা", te: "తেলুగు", mr: "मराठী"
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

function getParticipantName(senderId) {
    if (!roomData?.users || !senderId) {
        return 'Participant';
    }
    
    const sender = roomData.users.find(user => user.user_id === senderId);
    return sender ? sender.nickname : 'Participant';
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
   🆕 SYSTÈME AUTO-STOP 15S
======================================== */
function startVoiceDetection() {
    if (!navigator.mediaDevices || !window.AudioContext) {
        console.log('⚠️ Audio Context non disponible');
        return;
    }
    
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioContext.createAnalyser();
            microphone = audioContext.createMediaStreamSource(stream);
            
            analyser.fftSize = 512;
            const bufferLength = analyser.frequencyBinCount;
            dataArray = new Uint8Array(bufferLength);
            
            microphone.connect(analyser);
            
            console.log('🎤 Détection vocale auto-stop initialisée');
            monitorVoiceActivity();
        })
        .catch(error => {
            console.warn('⚠️ Erreur accès micro pour détection:', error);
        });
}

function monitorVoiceActivity() {
    if (!analyser || !dataArray) return;
    
    analyser.getByteFrequencyData(dataArray);
    
    // Calculer le niveau audio moyen
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i];
    }
    const average = sum / dataArray.length;
    
    // 🔧 LOGIQUE CORRIGÉE : Si du son est détecté
    if (average > silenceThreshold) {
        // Réinitialiser le timer de silence
        if (silenceTimer) {
            clearTimeout(silenceTimer);
            silenceTimer = null;
        }
        
        // Programmer l'arrêt automatique après 15s de silence
        silenceTimer = setTimeout(() => {
            console.log('🔇 15s de silence détectées - Arrêt automatique');
            
            if (isHost && isListening) {
                stopHostListening();
            } else if (!isHost && isParticipantListening) {
                stopParticipantListening();
            }
        }, silenceTimeout);
    }
    // 🆕 NOUVEAU : Si pas de timer en cours, en lancer un
    else if (!silenceTimer) {
        silenceTimer = setTimeout(() => {
            console.log('🔇 15s de silence détectées - Arrêt automatique');
            
            if (isHost && isListening) {
                stopHostListening();
            } else if (!isHost && isParticipantListening) {
                stopParticipantListening();
            }
        }, silenceTimeout);
    }
    
    // Continuer la surveillance si le micro est actif
    if ((isHost && isListening) || (!isHost && isParticipantListening)) {
        requestAnimationFrame(monitorVoiceActivity);
    }
}

function stopVoiceDetection() {
    if (silenceTimer) {
        clearTimeout(silenceTimer);
        silenceTimer = null;
    }
    
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
    
    analyser = null;
    microphone = null;
    dataArray = null;
    
    console.log('🔇 Détection vocale arrêtée');
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
   GESTION DES ÉLÉMENTS DOM - CORRIGÉE SANS CONNECTION-STATUS
======================================== */
function initializeDOMElements() {
    // CORRECTION : Suppression de 'connection-status' qui causait l'erreur
    const elementIds = [
        'status', 'controls', 'host-controls', 'participant-controls',
        'mic-button', 'participant-mic-button', 'text-mode-button', 'participant-text-button',
        'wave-animation', 'participant-wave', 'qr-section', 'qr-code-image',
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
    console.log('🔧 Configuration interface pour rôle:', isHost ? 'HÔTE' : 'PARTICIPANT');
    
    if (isHost) {
        // Interface hôte
        showElement('host-controls');
        showElement('host-interface');
        
        const qrSection = document.getElementById('qr-section');
        if (qrSection) {
            qrSection.classList.add('show');
        }
        
        // Initialiser le QR code
        qrCodeImage = document.getElementById('qr-code-image');
        updateQRCode();
        
        console.log('👑 Interface hôte configurée');
    } else {
        // Interface participant - LOGIQUE SIMPLE ET DIRECTE
        console.log('👤 Configuration interface participant...');
        
        // Force l'affichage direct avec JavaScript simple
        const participantControls = document.getElementById('participant-controls');
        const participantInterface = document.getElementById('participant-interface');
        
        if (participantControls) {
            participantControls.style.display = 'block';
            participantControls.style.visibility = 'visible';
            console.log('✅ participant-controls affiché');
        } else {
            console.error('❌ participant-controls non trouvé !');
        }
        
        if (participantInterface) {
            participantInterface.style.display = 'block';
            participantInterface.style.visibility = 'visible';
            console.log('✅ participant-interface affiché');
        } else {
            console.error('❌ participant-interface non trouvé !');
        }
        
        console.log('👤 Interface participant configurée');
    }
    
    // Afficher les contrôles communs
    showElement('controls');
    animateElement('controls', 'slideInUp');

   // Masquer la section "Traduction vers..." côté participant
    if (!isHost) {
        const translationSection = document.getElementById('participant-translation-section');
        if (translationSection) {
            translationSection.style.display = 'none';
            console.log('✅ Section "Traduction vers..." masquée via JavaScript');
        } else {
            console.log('❌ Section participant-translation-section non trouvée');
        }
    }
    
    console.log('✅ Configuration interface terminée');
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
    const mainStatus = document.getElementById('status');
    
    if (connected) {
        const message = getTranslation('connected') || 'Connecté ✅';
        
        // Gros statut principal
        if (mainStatus) {
            mainStatus.textContent = message;
            mainStatus.className = 'status connected show';
        }
        
    } else {
        const message = getTranslation('reconnecting') || 
            `Reconnexion... (${reconnectAttempts}/${maxReconnectAttempts})`;
            
        // Gros statut principal  
        if (mainStatus) {
            mainStatus.textContent = message;
            mainStatus.className = 'status error show';
        }
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
    recognition.lang = getRecognitionLanguageCode(userData.language);
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
    
    participantRecognition.onstart = function() {
        console.log('🎤 Reconnaissance démarrée');
    };
    
    participantRecognition.onaudiostart = function() {
        console.log('🔊 Audio détecté !');
    };
    
    participantRecognition.onsoundstart = function() {
        console.log('🎵 Son détecté !');
    };
    
    participantRecognition.onspeechstart = function() {
        console.log('🗣️ Parole détectée !');
    };
    
    participantRecognition.onresult = function(event) {
        console.log('📝 Résultat reçu:', event.results);
        
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
       .then((stream) => {  // ← AJOUT (stream) ici !
           try {
               currentStream = stream;  // ← NOUVEAU : sauvegarder le stream
               recognition.start();
               isListening = true;
               networkErrorCount = 0;
               
              const micButton = document.getElementById('mic-button');
              console.log('🔍 DEBUG micButton:', micButton); 
              updateMicButtonState(micButton, true, 'stop_button');
               showElement(waveAnimation, true);
               
               const message = getTranslation('listening_french') || 
                   'En écoute... Parlez en français.';
               showStatus(message, 'info');
               
               notifySuccess('🎤 Microphone activé');
               console.log('✅ Reconnaissance vocale hôte démarrée');
               startVoiceDetection();
              // 🎵 NOUVEAU - Démarrer les vagues audio
              if (initAudioAnalyser(stream)) {
                  startWaveAnimation(true); // true = hôte
                  console.log('🎵 Vagues hôte connectées au micro');
              }
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
    
   const micButton = document.getElementById('mic-button'); 
   updateMicButtonState(micButton, false, 'speak_french');
    hideElement(waveAnimation);
    
    const message = getTranslation('click_mic') || 
        'Cliquez sur le micro pour parler.';
    showStatus(message, 'connected');

   // 🆕 POP-UP ROUGE + ARRÊT DÉTECTION
   if (window.TradLive?.notifications) {
       window.TradLive.notifications.show(getTranslation('mic_closed', 'Microphone fermé'), 'error', { duration: 2000 });
   }
   stopVoiceDetection();
    
   console.log('🎤 Microphone hôte arrêté');
   // 🎵 NOUVEAU - Arrêter les vagues audio
stopWaveAnimation(true); // true = hôte

// 🎵 NOUVEAU - Fermer le stream audio
if (currentStream) {
    currentStream.getTracks().forEach(track => track.stop());
    currentStream = null;
}
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
        .then((stream) => {
            try {
                currentStream = stream;
                participantRecognition.start();
                isParticipantListening = true;
                
               const participantMicButton = document.getElementById('participant-mic-button'); 
               updateMicButtonState(participantMicButton, true, 'stop_button');
                showElement(participantWave, true);
                
                const langName = getLanguageName(userData.language);
                const message = getTranslation('listening_your_language') || 
                    `En écoute... Parlez en ${langName}.`;
                showStatus(message, 'info');
                
                notifySuccess('🎤 Microphone activé');
                console.log('✅ Reconnaissance vocale participant démarrée');
               // 🎵 NOUVEAU - Démarrer les vagues audio participant
               if (initAudioAnalyser(stream)) {
                   startWaveAnimation(false); // false = participant
                   console.log('🎵 Vagues participant connectées au micro');
               }

                startVoiceDetection();
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
    
   const participantMicButton = document.getElementById('participant-mic-button'); 
   updateMicButtonState(participantMicButton, false, 'speak_your_language');
    hideElement(participantWave);
    
    const message = getTranslation('click_mic') || 
        'Cliquez sur le micro pour parler.';
    showStatus(message, 'connected');

   // POP-UP ROUGE + ARRÊT DÉTECTION
   if (window.TradLive?.notifications) {
       window.TradLive.notifications.show(getTranslation('mic_closed', 'Microphone fermé'), 'error', { duration: 2000 });
   }
   stopVoiceDetection();
    
   console.log('🎤 Microphone participant arrêté');
// 🎵 NOUVEAU - Arrêter les vagues audio participant
stopWaveAnimation(false); // false = participant

// 🎵 NOUVEAU - Fermer le stream audio
if (currentStream) {
    currentStream.getTracks().forEach(track => track.stop());
    currentStream = null;
}
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
        source_language: userData.language,
        sender_id: userData.user_id
    };
    
    console.log('🟢 Données envoyées:', requestData);
    console.log('🟢 URL:', `/api/room/${userData.room_id}/translate`);
    
    makeApiRequest(`/api/room/${userData.room_id}/translate`, 'POST', requestData)
        .then(data => {
            console.log('🟢 Réponse API reçue:', data);
            
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
                console.log('🔴 API erreur:', data.error);
                throw new Error(data.error || 'Erreur de traduction');
            }
        })
        .catch(error => {
            console.error('🔴 Erreur complète:', error);
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
        sender_id: userData.user_id
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
    // Récupérer l'élément à chaque fois (plus sûr)
    const hostOriginalTextEl = document.getElementById('host-original-text');
    if (hostOriginalTextEl) {
        hostOriginalTextEl.textContent = text;
        hostOriginalTextEl.classList.remove('empty-translation');
        animateElement(hostOriginalTextEl, 'pulse');
        console.log('✅ Texte hôte affiché dans "What you say":', text.substring(0, 30) + '...');
    } else {
        console.log('❌ Élément host-original-text non trouvé !');
    }
}

function updateParticipantOwnText(text) {
    // Récupérer les éléments à chaque fois
    const participantOwnTextEl = document.getElementById('participant-own-text');
    const participantMessageAreaEl = document.getElementById('participant-message-area');
    
    if (participantOwnTextEl && participantMessageAreaEl) {
        participantOwnTextEl.textContent = text;
        participantMessageAreaEl.style.display = 'block';
        animateElement(participantMessageAreaEl, 'slideInUp');
        console.log('✅ Texte participant affiché dans "Votre message":', text.substring(0, 30) + '...');
    } else {
        console.log('❌ Éléments participant non trouvés !');
        console.log('participantOwnText:', participantOwnTextEl);
        console.log('participantMessageArea:', participantMessageAreaEl);
    }
}

function updateParticipantFrenchText() {
    const participantFrenchTextEl = document.getElementById('participant-french-text');
    if (participantFrenchTextEl) {
        const translatingMessage = getTranslation('translating') || 
            'Traduction en cours...';
        participantFrenchTextEl.textContent = translatingMessage;
        animateElement(participantFrenchTextEl, 'pulse');
    }
}

function buildParticipantResponseLabel(senderId, senderLanguage) {
    // Récupérer le nom du participant
    const participantName = getParticipantName(senderId);
    
    // Récupérer la langue du participant traduite dans la langue de l'interface
    const languageName = getLanguageName(senderLanguage);
    
    // Récupérer "Réponse de" / "Response from" / etc. selon la langue d'interface
    const responseFromText = getTranslation('response_from', 'Réponse de');
    
    // Construire le label final
    return `💬 ${responseFromText} ${participantName} (${languageName})`;
}

function updateParticipantResponseLabel(senderId) {
    // Trouver l'élément du label
    const labelElement = document.querySelector('#host-interface .translation-section:nth-child(2) .translation-label');
    
    if (!labelElement || !senderId) {
        console.log('❌ Impossible de mettre à jour le label');
        return;
    }
    
    // Récupérer la langue du participant qui a envoyé le message
    const sender = roomData.users.find(user => user.user_id === senderId);
    const senderLanguage = sender ? sender.language : 'fr';
    
    console.log('🏷️ Mise à jour label pour:', sender?.nickname, `(${senderLanguage})`);
    
    // Construire et appliquer le nouveau label
    const newLabel = buildParticipantResponseLabel(senderId, senderLanguage);
    labelElement.innerHTML = newLabel;
    
    // Animation pour indiquer le changement
    animateElement(labelElement, 'pulse');
}

/* ========================================
   MODE TEXTE - FINALISÉ
======================================== */
function showTextInput() {
    console.log('📝 Affichage mode texte hôte');
    const textInputFallback = document.getElementById('text-input-fallback');
    
    if (textInputFallback) {
        textInputFallback.classList.add('show');
        
        const textInput = document.getElementById('text-input');
        if (textInput) {
            setTimeout(() => {
             try {
                 textInput.focus();
             } catch (e) {
                 console.log('Focus interrompu par extension, pas grave');
             }
         }, 300);
        }
        
        animateElement(textInputFallback, 'slideInUp');
        console.log('✅ Mode texte hôte activé');
    } else {
        console.log('❌ Élément text-input-fallback introuvable');
    }
}

function hideTextInput() {
    console.log('📝 Masquage mode texte hôte');
    const textInputFallback = document.getElementById('text-input-fallback');
    if (textInputFallback) {
        textInputFallback.classList.remove('show');
        animateElement(textInputFallback, 'fadeOut');
    }
}

function sendHostText() {
    console.log('🟢 sendHostText() appelée');
    
    const textInput = document.getElementById('text-input');
    console.log('🟢 textInput trouvé:', textInput);
    
    if (!textInput) return;
    
    const text = textInput.value.trim();
    console.log('🟢 Texte récupéré:', text);
    
    if (text) {
        console.log('🟢 Appel sendHostTranslation avec:', text);
        sendHostTranslation(text);
        textInput.value = '';
        hideTextInput();
    } else {
        console.log('🔴 Texte vide !');
    }
}

function showParticipantTextInput() {
    console.log('📝 Affichage mode texte participant');
    const participantTextInput = document.getElementById('participant-text-input');
    
    if (participantTextInput) {
        participantTextInput.classList.add('show');
        
        const textInput = document.getElementById('participant-text');
        if (textInput) {
            setTimeout(() => {
                try {
                    textInput.focus();
                } catch (e) {
                    console.log('Focus interrompu par extension, pas grave');
                }
            }, 300);
        }
        
        animateElement(participantTextInput, 'slideInUp');
        console.log('✅ Mode texte participant activé');
    } else {
        console.log('❌ Élément participant-text-input introuvable');
    }
}

function hideParticipantTextInput() {
    console.log('📝 Masquage mode texte participant');
    const participantTextInput = document.getElementById('participant-text-input');
    if (participantTextInput) {
        participantTextInput.classList.remove('show');
        animateElement(participantTextInput, 'fadeOut');
    }
}

function sendParticipantText() {
    console.log('🟢 sendParticipantText() appelée');
    
    const textInput = document.getElementById('participant-text');
    console.log('🟢 textInput trouvé:', textInput);
    
    if (!textInput) return;
    
    const text = textInput.value.trim();
    console.log('🟢 Texte récupéré:', text);
    
    if (text) {
        console.log('🟢 Appel sendParticipantTranslation avec:', text);
        sendParticipantTranslation(text);
        textInput.value = '';
        hideParticipantTextInput();
    } else {
        console.log('🔴 Texte vide !');
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
    const actualData = data.data || data;
    
    if (isHost) {
        // Interface hôte : afficher SEULEMENT les réponses des participants
        if (actualData.original && !actualData.show_translation) {
            
            // 🔧 NOUVELLE LOGIQUE : Utiliser les vraies données du serveur
            const isMyMessage = actualData.sender_id === userData.user_id;
            
            console.log('🔍 DEBUG - actualData.sender_id:', actualData.sender_id);
            console.log('🔍 DEBUG - userData.user_id:', userData.user_id);
            console.log('🔍 DEBUG - isMyMessage:', isMyMessage);
            
            if (!isMyMessage) {
             // Ce n'est PAS mon message → C'est un participant qui répond
             console.log('👤 Message d\'un participant, affichage dans Participant responses');
             const hostResponsesText = document.getElementById('host-responses-text');
             if (hostResponsesText) {
                 hostResponsesText.textContent = actualData.original;
                 hostResponsesText.classList.remove('empty-translation');
                 animateElement(hostResponsesText, 'pulse');
             }
             
             // 🆕 NOUVEAU : Mettre à jour le label dynamiquement
             updateParticipantResponseLabel(actualData.sender_id);
             
         } else {
             // C'est MON message → Ignorer (déjà affiché dans "What you say")
             console.log('👑 Mon propre message, ignoré (déjà dans What you say)');
         }
         }  
    } else {
        // Interface participant : afficher les messages de l'hôte traduits
        if (actualData.original && actualData.show_translation) {
            const participantOriginalText = document.getElementById('participant-original-text');
            if (participantOriginalText) {
                participantOriginalText.textContent = actualData.original;
                participantOriginalText.classList.remove('empty-translation');
            }
            
            const participantTranslatedText = document.getElementById('participant-translated-text');
            if (actualData.translated && participantTranslatedText) {
                participantTranslatedText.textContent = actualData.translated;
                participantTranslatedText.classList.remove('empty-translation');
                animateElement(participantTranslatedText, 'pulse');
                
                // Synthèse vocale avec ID unique pour éviter les répétitions
                if (actualData.enable_speech) {
                    const translationId = `${actualData.timestamp}_${actualData.translated.substring(0, 20)}`;
                    console.log('🎵 Lecture traduction:', actualData.translated.substring(0, 30) + '...');
                    speakText(actualData.translated, userData.language, translationId);
                }
            }
        }
        
        // Affichage des propres messages du participant
        if (actualData.show_own_message) {
            const participantOwnText = document.getElementById('participant-own-text');
            const participantMessageArea = document.getElementById('participant-message-area');
            
            if (participantOwnText && actualData.original) {
                participantOwnText.textContent = actualData.original;
                if (participantMessageArea) {
                    participantMessageArea.style.display = 'block';
                    animateElement(participantMessageArea, 'slideInUp');
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

    // CORRECTION TIMING : Récupérer les boutons au bon moment
   let micBtn = null;
   let textBtn = null; 
   let partMicBtn = null;
   let partTextBtn = null;
   
   // Debouncing pour éviter les clics multiples
   const debouncedToggleHost = debounce(toggleHostListening, 300);
   const debouncedToggleParticipant = debounce(toggleParticipantListening, 300);
   
   // Attendre que l'interface soit affichée puis récupérer les boutons
   setTimeout(() => {
       micBtn = document.getElementById('mic-button');
       textBtn = document.getElementById('text-mode-button');
       partMicBtn = document.getElementById('participant-mic-button');
       partTextBtn = document.getElementById('participant-text-button');
       
       // DEBUG pour voir si c'est corrigé
       console.log('🔍 NOUVEAU DEBUG micBtn:', micBtn);
       console.log('🔍 NOUVEAU DEBUG partMicBtn:', partMicBtn);
       
       // MAINTENANT ajouter les événements (à l'intérieur du setTimeout !)
       if (micBtn) micBtn.addEventListener('click', debouncedToggleHost);
       if (textBtn) textBtn.addEventListener('click', showTextInput);
       
       // Boutons participant  
       if (partMicBtn) partMicBtn.addEventListener('click', debouncedToggleParticipant);
       if (partTextBtn) partTextBtn.addEventListener('click', showParticipantTextInput);
       
       console.log('✅ Événements boutons configurés');
   }, 500);
}
function updateQRCode() {
    console.log('🔍 updateQRCode() appelée');
    console.log('🔍 qrCodeImage:', qrCodeImage);
    console.log('🔍 userData:', userData);
    console.log('🔍 userData.room_id:', userData.room_id);
    if (!qrCodeImage) return;
    
    const roomUrl = `${window.location.origin}/?auto_join=true&room_id=${userData.room_id}`;
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

/* ========================================
   🎵 MISSION 13 - DIAGNOSTIC VAGUES AUDIO
======================================== */

// Test pour voir si les vagues s'affichent
function testWaveVisibility() {
    console.log('🔍 TEST - Vérification des vagues...');
    
    const hostWave = document.getElementById('wave-animation');
    const participantWave = document.getElementById('participant-wave');
    
    console.log('🎵 Vague hôte trouvée:', hostWave ? '✅' : '❌');
    console.log('🎵 Vague participant trouvée:', participantWave ? '✅' : '❌');
    
    if (hostWave) {
        console.log('🎵 Style vague hôte:', window.getComputedStyle(hostWave).display);
    }
    
    if (participantWave) {
        console.log('🎵 Style vague participant:', window.getComputedStyle(participantWave).display);
    }
}

// Test pour forcer l'affichage des vagues pendant 3 secondes
function testWaveAnimation() {
    console.log('🎵 TEST - Forçage animation vagues pendant 3s...');
    
    const hostWave = document.getElementById('wave-animation');
    const participantWave = document.getElementById('participant-wave');
    
    // Forcer l'affichage
    if (hostWave) {
        hostWave.style.display = 'flex';
        hostWave.classList.add('active');
    }
    
    if (participantWave) {
        participantWave.style.display = 'flex';  
        participantWave.classList.add('active');
    }
    
    // Cacher après 3 secondes
    setTimeout(() => {
        if (hostWave) {
            hostWave.style.display = 'none';
            hostWave.classList.remove('active');
        }
        
        if (participantWave) {
            participantWave.style.display = 'none';
            participantWave.classList.remove('active');
        }
        
        console.log('🎵 Test terminé');
    }, 3000);
}

// Ajouter les fonctions de test au window pour pouvoir les appeler
window.testWaveVisibility = testWaveVisibility;
window.testWaveAnimation = testWaveAnimation;

/* ========================================
   🎵 SYSTÈME VAGUES AUDIO TEMPS RÉEL
======================================== */

// Variables globales pour l'analyse audio
let audioAnalyser = null;
let audioDataArray = null;
let waveAnimationFrame = null;
let isWaveActive = false;

// Initialiser l'analyseur audio
function initAudioAnalyser(stream) {
    try {
        // Créer le contexte audio s'il n'existe pas déjà
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        
        // Créer l'analyseur
        audioAnalyser = audioContext.createAnalyser();
        audioAnalyser.fftSize = 256;
        audioAnalyser.smoothingTimeConstant = 0.8;
        
        // Connecter le microphone à l'analyseur
        const source = audioContext.createMediaStreamSource(stream);
        source.connect(audioAnalyser);
        
        // Préparer le buffer de données
        const bufferLength = audioAnalyser.frequencyBinCount;
        audioDataArray = new Uint8Array(bufferLength);
        
        console.log('🎵 Analyseur audio initialisé');
        return true;
    } catch (error) {
        console.error('❌ Erreur init analyseur audio:', error);
        return false;
    }
}

// Démarrer l'animation des vagues
function startWaveAnimation(isHost = true) {
    if (!audioAnalyser || !audioDataArray) {
        console.warn('⚠️ Analyseur audio non initialisé');
        return;
    }
    
    isWaveActive = true;
    const waveElement = isHost ? 
        document.getElementById('wave-animation') : 
        document.getElementById('participant-wave');
    
    if (!waveElement) {
        console.warn('⚠️ Élément vague non trouvé');
        return;
    }
    
    // Afficher les vagues
    waveElement.style.display = 'flex';
    waveElement.classList.add('active');
    
    console.log('🎵 Animation vagues démarrée:', isHost ? 'HÔTE' : 'PARTICIPANT');
    
    // Démarrer la boucle d'animation
    animateWaves(waveElement);
}

// Arrêter l'animation des vagues
function stopWaveAnimation(isHost = true) {
    isWaveActive = false;
    
    if (waveAnimationFrame) {
        cancelAnimationFrame(waveAnimationFrame);
        waveAnimationFrame = null;
    }
    
    const waveElement = isHost ? 
        document.getElementById('wave-animation') : 
        document.getElementById('participant-wave');
    
    if (waveElement) {
        waveElement.style.display = 'none';
        waveElement.classList.remove('active');
        
        // Remettre les barres à leur taille par défaut
        const bars = waveElement.querySelectorAll('.wave-bar');
        bars.forEach(bar => {
            bar.style.height = '10px';
            bar.style.opacity = '0.5';
        });
    }
    
    console.log('🔇 Animation vagues arrêtée:', isHost ? 'HÔTE' : 'PARTICIPANT');
}

// Animer les vagues en temps réel - VERSION COMPACTE
function animateWaves(waveElement) {
    if (!isWaveActive || !audioAnalyser || !audioDataArray) {
        return;
    }
    
    // Obtenir les données audio
    audioAnalyser.getByteFrequencyData(audioDataArray);
    
    // Calculer le niveau audio moyen
    let sum = 0;
    for (let i = 0; i < audioDataArray.length; i++) {
        sum += audioDataArray[i];
    }
    const average = sum / audioDataArray.length;
    
    // Seuils de sensibilité
    const baseLevel = 15;
    const normalizedLevel = Math.max(0, Math.min(1, (average - baseLevel) / 30));
    
    // 🎯 DEBUG (optionnel - retire si trop de logs)
    if (average > baseLevel) {
        console.log(`🎵 Audio: ${Math.round(average)} | Normalisé: ${normalizedLevel.toFixed(2)}`);
    }
    
    // Animer les barres avec les nouvelles classes CSS - VERSION COMPACTE
    const bars = waveElement.querySelectorAll('.wave-bar');
    bars.forEach((bar, index) => {
        // Nettoyer les anciennes classes
        bar.classList.remove('silence', 'low', 'medium', 'high');
        
        if (normalizedLevel > 0.02) {
            // Calcul de la hauteur avec variation fluide - ADAPTÉE POUR CONTAINER 40px
            const variation = Math.sin((Date.now() / 120) + (index * 0.8)) * 0.4 + 0.6;
            const baseHeight = 8;  // Plus petit
            const maxHeight = 28;  // Plus petit (était 55)
            const height = Math.max(baseHeight, baseHeight + (normalizedLevel * maxHeight * variation));
            
            // Animation fluide de la hauteur
            bar.style.height = `${height}px`;
            bar.style.transition = 'height 0.08s ease-out';
            
            // Classes selon l'intensité (couleurs automatiques via CSS)
            if (normalizedLevel > 0.6) {
                bar.classList.add('high');
            } else if (normalizedLevel > 0.25) {
                bar.classList.add('medium');
            } else if (normalizedLevel > 0.08) {
                bar.classList.add('low');
            } else {
                bar.classList.add('silence');
            }
        } else {
            // Silence - état de base compact
            bar.style.height = '8px';
            bar.style.transition = 'height 0.2s ease-out';
            bar.classList.add('silence');
        }
    });
    
    // Continuer l'animation
    waveAnimationFrame = requestAnimationFrame(() => animateWaves(waveElement));
}

// Test manuel des vagues avec micro
function testRealWaves() {
    console.log('🎵 TEST - Vagues avec micro réel...');
    
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            if (initAudioAnalyser(stream)) {
                startWaveAnimation(true);
                
                console.log('🎵 Test en cours... Parlez dans le micro !');
                
                // Arrêter après 10 secondes
                setTimeout(() => {
                    stopWaveAnimation(true);
                    stream.getTracks().forEach(track => track.stop());
                    console.log('🎵 Test terminé');
                }, 10000);
            }
        })
        .catch(error => {
            console.error('❌ Erreur accès micro pour test:', error);
        });
}

// Ajouter la fonction de test au window
window.testRealWaves = testRealWaves;





















