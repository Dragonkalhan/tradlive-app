import os
import sys
import json
import time
import datetime
import threading
import atexit
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from deep_translator import GoogleTranslator, MyMemoryTranslator
import qrcode
from io import BytesIO
from room_manager import room_manager
from translation_manager import translation_manager

# ============================================================
# SYSTÈME DE TRANSCRIPTION AUDIO (AZURE TEMPORAIRE)
# ============================================================

import azure.cognitiveservices.speech as speechsdk
import tempfile

class SpeechTranscriptionManager:
    """Gestionnaire de transcription - Azure temporaire, migration Whisper future"""
    
    def __init__(self):
        # Configuration Azure
        self.azure_key = os.environ.get('AZURE_SPEECH_KEY', 'not-configured')
        self.azure_region = os.environ.get('AZURE_SPEECH_REGION', 'westeurope')
        self.service_available = self.azure_key != 'not-configured'
        
        print(f"🎤 Speech Manager initialisé - Azure disponible: {self.service_available}")
    
    def transcribe_audio(self, audio_file, language='fr-FR'):
        """Transcrit un fichier audio avec Azure"""
        if not self.service_available:
            raise Exception("Azure Speech non configuré")
            
        try:
            # Sauvegarder temporairement
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
                audio_file.save(temp_path)
            
            # Configuration Azure
            speech_config = speechsdk.SpeechConfig(
                subscription=self.azure_key, 
                region=self.azure_region
            )
            speech_config.speech_recognition_language = language
            
            # Transcription
            audio_config = speechsdk.audio.AudioConfig(filename=temp_path)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config, 
                audio_config=audio_config
            )
            
            result = speech_recognizer.recognize_once()
            
            # Nettoyer
            os.unlink(temp_path)
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return {
                    'success': True,
                    'text': result.text.strip(),
                    'confidence': 0.9,
                    'service': 'azure'
                }
            else:
                raise Exception(f"Erreur Azure: {result.reason}")
                
        except Exception as e:
            print(f"❌ Erreur transcription Azure: {str(e)}")
            raise e

# Instance globale (remplace whisper_model)
speech_manager = SpeechTranscriptionManager()

# ============================================================
# CONFIGURATION ENVIRONNEMENT
# ============================================================

# Détecter l'environnement (production sur Render.com ou développement local)
IS_PRODUCTION = os.environ.get('RENDER') is not None
BASE_URL = "https://tradlive-app.onrender.com" if IS_PRODUCTION else "http://localhost:5000"

print(f"🌍 Environnement: {'PRODUCTION (Render.com)' if IS_PRODUCTION else 'DÉVELOPPEMENT (Local)'}")
print(f"🔗 URL de base: {BASE_URL}")

# ============================================================
# VARIABLES GLOBALES
# ============================================================

# Variables pour le heartbeat et le statut du client
last_heartbeat = datetime.datetime.now()
heartbeat_lock = threading.Lock()
server_running = True
heartbeat_thread = None

# Cache pour les traductions (pour éviter de re-traduire les mêmes phrases)
translation_cache = {}
MAX_CACHE_SIZE = 200

# ============================================================
# INITIALISATION DE L'APPLICATION FLASK
# ============================================================

app = Flask(__name__, template_folder='templates')

# ============================================================
# SURVEILLANCE DU HEARTBEAT
# ============================================================

def check_heartbeat():
    """Vérifie régulièrement si le client est toujours connecté via le heartbeat"""
    global server_running
    
    while server_running:
        try:
            time.sleep(5)
            
            with heartbeat_lock:
                time_since_last_heartbeat = (datetime.datetime.now() - last_heartbeat).total_seconds()
                
                if time_since_last_heartbeat > 30:  # 30 secondes en production
                    print("\nAucune activité client détectée. Nettoyage des salles...")
                    room_manager.cleanup_rooms()
                    
        except Exception as e:
            print(f"Erreur dans la vérification du heartbeat: {str(e)}")

def update_heartbeat():
    """Met à jour le timestamp du dernier heartbeat"""
    global last_heartbeat
    
    with heartbeat_lock:
        last_heartbeat = datetime.datetime.now()

def cleanup():
    """Fonction de nettoyage exécutée à la sortie du programme"""
    global server_running
    
    server_running = False
    
    if heartbeat_thread and heartbeat_thread.is_alive():
        heartbeat_thread.join(timeout=0.5)
    
    print("Nettoyage effectué, fermeture du programme.")

atexit.register(cleanup)

# ============================================================
# GÉNÉRATION DE QR CODE
# ============================================================

def generate_qr_code(url):
    """Génère un QR code pour l'URL du serveur"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer)
    buffer.seek(0)
    return buffer

# ============================================================
# FONCTIONS DE TRADUCTION (SIMPLIFIÉES)
# ============================================================

def translate_text(text, target_lang):
    """Fonction de traduction simplifiée utilisant le gestionnaire"""
    try:
        return translation_manager.translate(text, 'fr', target_lang)
    except Exception as e:
        return f"Erreur de traduction: {str(e)}"

def translate_to_french(text, source_lang):
    """Fonction pour la traduction vers le français"""
    try:
        return translation_manager.translate(text, source_lang, 'fr')
    except Exception as e:
        return f"Erreur de traduction: {str(e)}"

# ============================================================
# ROUTES FLASK - SYSTÈME DE SALLES UNIQUEMENT
# ============================================================

@app.route("/")
def index():
    """Route principale - redirige vers la page des salles"""
    update_heartbeat()
    return redirect(url_for('rooms_page'))

@app.route('/rooms')
def rooms_page():
    """Page principale pour créer ou rejoindre une salle"""
    update_heartbeat()
    return render_template('rooms.html')

@app.route('/api/create-room', methods=['POST'])
def create_room():
    """Crée une nouvelle salle"""
    update_heartbeat()
    
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'Données manquantes'}), 400
        
        host_nickname = data.get('nickname', '').strip() if data.get('nickname') else ''
        host_language = data.get('language', 'fr')
        room_name = data.get('room_name', '').strip() if data.get('room_name') else ''
        password = data.get('password', '').strip() if data.get('password') else None
        
        if not host_nickname:
            return jsonify({'success': False, 'error': 'Pseudo requis'}), 400
        
        if not room_name:
            return jsonify({'success': False, 'error': 'Nom de salle requis'}), 400
        
        room_id, user_id, success = room_manager.create_room(
            host_nickname, host_language, room_name, password
        )
        
        if success:
            return jsonify({
                'success': True,
                'room_id': room_id,
                'user_id': user_id,
                'message': f'Salle créée ! Code : {room_id}'
            })
        else:
            return jsonify({'success': False, 'error': 'Erreur création salle'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/join-room', methods=['POST'])
def join_room():
    """Rejoint une salle existante"""
    update_heartbeat()
    
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'Données manquantes'}), 400
        
        room_id = data.get('room_id', '').strip() if data.get('room_id') else ''
        nickname = data.get('nickname', '').strip() if data.get('nickname') else ''
        language = data.get('language', 'fr')
        password = data.get('password', '').strip() if data.get('password') else None
        
        if not room_id:
            return jsonify({'success': False, 'error': 'Code de salle requis'}), 400
        
        if not nickname:
            return jsonify({'success': False, 'error': 'Pseudo requis'}), 400
        
        user_id, success, error_message = room_manager.join_room(
            room_id, nickname, language, password
        )
        
        if success:
            return jsonify({
                'success': True,
                'room_id': room_id,
                'user_id': user_id,
                'message': f'Vous avez rejoint la salle !'
            })
        else:
            return jsonify({'success': False, 'error': error_message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/room/<room_id>')
def room_interface(room_id):
    """Interface de la salle pour un utilisateur"""
    update_heartbeat()
    
    room = room_manager.get_room(room_id)
    if not room:
        return redirect(url_for('rooms_page'))
    
    # Vérifier si c'est un auto-join via QR code
    auto_join = request.args.get('auto_join')
    if auto_join == 'true':
        # Rediriger vers la page de rejoindre avec le room_id pré-rempli
        return redirect(url_for('rooms_page') + f'?join={room_id}')
    
    return render_template('room.html', room_id=room_id)

@app.route('/api/room/<room_id>/info')
def room_info(room_id):
    """Informations sur une salle"""
    update_heartbeat()
    
    room = room_manager.get_room(room_id)
    if not room:
        return jsonify({'success': False, 'error': 'Salle introuvable'}), 404
    
    return jsonify({
        'success': True,
        'room': room.to_dict()
    })

@app.route('/api/room/<room_id>/leave', methods=['POST'])
def leave_room(room_id):
    """Quitte une salle"""
    update_heartbeat()
    
    try:
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID requis'}), 400
        
        success = room_manager.leave_room(room_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Vous avez quitté la salle'})
        else:
            return jsonify({'success': False, 'error': 'Erreur en quittant la salle'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/room/<room_id>/translate', methods=['POST'])
def room_translate(room_id):
    """Traduit un message pour toute la salle"""
    update_heartbeat()
    
    try:
        data = request.json
        user_id = data.get('user_id')
        text = data.get('text', '').strip()
        source_language = data.get('source_language', 'fr')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID requis'}), 400
        
        if not text:
            return jsonify({'success': False, 'error': 'Texte requis'}), 400
        
        room = room_manager.get_room(room_id)
        if not room or not room.get_user(user_id):
            return jsonify({'success': False, 'error': 'Utilisateur non autorisé'}), 403
        
        room_manager.update_user_activity(room_id, user_id)
        
        # Diffuser la traduction avec synthèse vocale côté client
        success = room_manager.broadcast_translation(room_id, text, source_language, enable_speech=True)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Traduction diffusée à toute la salle'
            })
        else:
            return jsonify({'success': False, 'error': 'Erreur de diffusion'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/room/<room_id>/updates')
def room_updates(room_id):
    """Récupère les dernières traductions pour une salle"""
    update_heartbeat()
    
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID requis'}), 400
        
        room = room_manager.get_room(room_id)
        if not room or not room.get_user(user_id):
            return jsonify({'success': False, 'error': 'Utilisateur non autorisé'}), 403
        
        room_manager.update_user_activity(room_id, user_id)
        
        user = room.get_user(user_id)
        user_language = user.language
        
        last_translation = room.last_translation
        
        # Interface différente selon le rôle (hôte vs participant)
        if user.is_host:
            # Pour l'hôte : voir les réponses des participants traduites en français
            if last_translation.get('source_language') != 'fr':  # C'est une réponse d'un utilisateur
                return jsonify({
                    'success': True,
                    'original': last_translation['translated'].get('fr', ''),
                    'translated': '',
                    'timestamp': last_translation['timestamp'].isoformat(),
                    'is_host': True,
                    'show_translation': False
                })
            else:  # C'est le message de l'hôte
                return jsonify({
                    'success': True,
                    'original': last_translation['original'],
                    'translated': '',
                    'timestamp': last_translation['timestamp'].isoformat(),
                    'is_host': True,
                    'show_translation': False
                })
        
        else:
            # Pour les participants : voir le français original + traduction dans leur langue
            if last_translation.get('source_language') == 'fr':  # Message de l'hôte
                translated_text = last_translation['translated'].get(user_language, '')
                
                return jsonify({
                    'success': True,
                    'original': last_translation['original'],
                    'translated': translated_text,
                    'timestamp': last_translation['timestamp'].isoformat(),
                    'is_host': False,
                    'show_translation': True,
                    'enable_speech': last_translation.get('enable_speech', False)
                })
            elif last_translation.get('source_language') == user_language:  # Son propre message
                # Le participant voit sa propre traduction française
                french_translation = last_translation['translated'].get('fr', '')
                return jsonify({
                    'success': True,
                    'original': last_translation['original'],  # Son texte original
                    'translated': french_translation,  # Traduction française
                    'timestamp': last_translation['timestamp'].isoformat(),
                    'is_host': False,
                    'show_own_message': True,
                    'show_translation': False
                })
            else:  # Message d'un autre utilisateur
                return jsonify({
                    'success': True,
                    'original': '',
                    'translated': '',
                    'timestamp': last_translation['timestamp'].isoformat(),
                    'is_host': False,
                    'show_translation': False
                })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/room/<room_id>/heartbeat', methods=['POST'])
def room_heartbeat(room_id):
    """Heartbeat pour une salle spécifique"""
    update_heartbeat()
    
    try:
        data = request.json
        user_id = data.get('user_id')
        
        if user_id:
            room_manager.update_user_activity(room_id, user_id)
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    """Heartbeat général"""
    update_heartbeat()
    return jsonify({'status': 'ok'})

@app.route('/qrcode')
def display_qrcode():
    """Affiche un QR code pour se connecter facilement à l'application"""
    update_heartbeat()
    
    # Utiliser l'URL appropriée selon l'environnement
    url = request.args.get('url', BASE_URL)
    
    buffer = generate_qr_code(url)
    return send_file(buffer, mimetype='image/png')

@app.route('/server-status')
def get_server_status():
    """Retourne les informations sur le statut du serveur"""
    update_heartbeat()
    
    status = {
        'mode': 'production' if IS_PRODUCTION else 'development',
        'base_url': BASE_URL,
        'environment': 'Render.com' if IS_PRODUCTION else 'Local'
    }
    
    return jsonify(status)

@app.route('/api/admin/stats')
def admin_stats():
    """Statistiques pour l'admin"""
    update_heartbeat()
    
    room_manager.cleanup_rooms()
    
    return jsonify(room_manager.get_stats())

@app.route('/set-preferred-language', methods=['POST'])
def set_preferred_language():
    """Route pour définir la langue préférée pour MyMemory"""
    update_heartbeat()
    
    data = request.json
    lang = data.get('lang', 'en')
    
    if lang == 'auto':
        lang = 'en'
    
    translation_manager.set_preferred_language(lang)
    
    return jsonify({
        'status': 'success',
        'message': f'Langue préférée définie sur: {lang}'
    })

# ============================================================
# NOUVELLES ROUTES AZURE (REMPLACENT WHISPER TEMPORAIREMENT)
# ============================================================

@app.route('/api/transcribe-audio', methods=['POST'])
def transcribe_audio():
    """Route pour transcrire l'audio avec Azure (compatible interface Whisper)"""
    update_heartbeat()
    
    if not speech_manager.service_available:
        return jsonify({'success': False, 'error': 'Azure Speech non configuré'}), 500
    
    try:
        # Vérifier qu'un fichier audio a été envoyé
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'Aucun fichier audio fourni'}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({'success': False, 'error': 'Nom de fichier audio vide'}), 400
        
        # Paramètres
        language = request.form.get('language', 'fr')
        azure_lang = 'fr-FR' if language == 'fr' else f'{language}-{language.upper()}'
        room_id = request.form.get('room_id')
        user_id = request.form.get('user_id')
        
        # Transcription avec Azure
        result = speech_manager.transcribe_audio(audio_file, azure_lang)
        
        transcribed_text = result['text']
        
        # Log pour débogage
        print(f"🎤 Azure transcription: '{transcribed_text}' (langue: {azure_lang})")
        
        # Si on a un room_id, diffuser automatiquement
        if room_id and user_id and transcribed_text:
            room = room_manager.get_room(room_id)
            if room and room.get_user(user_id):
                room_manager.update_user_activity(room_id, user_id)
                
                # Diffuser selon le rôle
                user = room.get_user(user_id)
                source_language = 'fr' if user.is_host else user.language
                
                success = room_manager.broadcast_translation(
                    room_id, 
                    transcribed_text, 
                    source_language, 
                    user_id, 
                    enable_speech=user.is_host
                )
                
                return jsonify({
                    'success': True,
                    'text': transcribed_text,
                    'detected_language': azure_lang,
                    'broadcast': success,
                    'service': 'azure',
                    'message': 'Transcription et diffusion réussies'
                })
        
        # Réponse simple sans diffusion
        return jsonify({
            'success': True,
            'text': transcribed_text,
            'detected_language': azure_lang,
            'confidence': result['confidence'],
            'service': 'azure'
        })
        
    except Exception as e:
        print(f"❌ Erreur transcription: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f'Erreur de transcription: {str(e)}'
        }), 500

@app.route('/api/simple-transcribe', methods=['POST'])
def simple_transcribe():
    """Route simplifiée pour transcription audio"""
    update_heartbeat()
    
    if not speech_manager.service_available:
        return jsonify({'error': 'Azure Speech non configuré'}), 500
    
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'Aucun fichier audio'}), 400
        
        audio_file = request.files['audio']
        target_language = request.form.get('target_language', 'en')
        
        # Transcription
        result = speech_manager.transcribe_audio(audio_file, 'fr-FR')
        french_text = result['text']
        
        if not french_text:
            return jsonify({'error': 'Aucun texte détecté'}), 400
        
        # Traduction avec votre système existant
        translated_text = translation_manager.translate(french_text, 'fr', target_language)
        
        return jsonify({
            'success': True,
            'original': french_text,
            'translated': translated_text,
            'detected_language': 'fr',
            'service': 'azure'
        })
        
    except Exception as e:
        print(f"❌ Erreur transcription simple: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/speech-status')
def speech_status():
    """Vérifie si Azure Speech est disponible (remplace whisper-status)"""
    update_heartbeat()
    
    if not speech_manager.service_available:
        return jsonify({
            'available': False,
            'error': 'Azure Speech non configuré'
        }), 500
    
    return jsonify({
        'available': True,
        'service': 'azure',
        'languages': ['fr', 'en', 'es', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ar'],
        'message': 'Azure Speech opérationnel',
        'quota_info': 'Service temporaire - migration Whisper prévue'
    })

# ============================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    
    # Démarrer le thread de surveillance du heartbeat
    heartbeat_thread = threading.Thread(target=check_heartbeat)
    heartbeat_thread.daemon = True
    heartbeat_thread.start()
    
    print(f"🚀 Démarrage du serveur sur le port {port}")
    print(f"🌐 URL d'accès: {BASE_URL}")
    
    app.run(debug=False, host='0.0.0.0', port=port)
