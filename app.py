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
    return render_template('index.html')

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
    """Traduction avec cache isolé par room - Version simplifiée"""
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
        
        user = room.get_user(user_id)
        actual_source_language = user.language if user else source_language
        
        room_manager.update_user_activity(room_id, user_id)
        
        # 🆕 SIMPLE : Laisser broadcast_translation faire tout le travail avec room_id
        sender_id = data.get('sender_id', user_id)
        success = room_manager.broadcast_translation(
            room_id, 
            text, 
            actual_source_language,
            sender_id, 
            enable_speech=True
            # room_id est passé automatiquement via le premier paramètre
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Traduction diffusée à toute la salle'
            })
        else:
            return jsonify({'success': False, 'error': 'Erreur de diffusion'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/api/room/<room_id>/cache-stats')
def room_cache_stats(room_id):
    """Statistiques du cache pour une room spécifique"""
    update_heartbeat()
    
    try:
        user_id = request.args.get('user_id')
        
        room = room_manager.get_room(room_id)
        if not room or not room.get_user(user_id):
            return jsonify({'success': False, 'error': 'Non autorisé'}), 403
        
        # Obtenir stats cache de cette room
        stats = translation_manager.get_cache_stats(room_id)
        
        return jsonify({
            'success': True,
            'room_id': room_id,
            'cache_stats': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
# 🆕 FONCTION DE NETTOYAGE ÉTENDUE dans cleanup()
def cleanup():
    """Fonction de nettoyage étendue"""
    global server_running
    
    server_running = False
    
    # Sauvegarder les caches des rooms avant fermeture
    try:
        translation_manager.save_smart_cache()
        print("💾 Caches des rooms sauvegardés")
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde caches: {e}")
    
    if heartbeat_thread and heartbeat_thread.is_alive():
        heartbeat_thread.join(timeout=0.5)
    
    print("Nettoyage effectué, fermeture du programme.")

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
        last_translation = room.last_translation
        
        # Récupérer l'utilisateur actuel pour connaître sa langue
        current_user = room.get_user(user_id)
        user_language = current_user.language if current_user else 'fr'
        
        # Identifier qui a envoyé le dernier message
        sender = room.get_user(last_translation.get('sender_id')) if last_translation.get('sender_id') else None
        is_host_message = sender and sender.is_host
        
        if user.is_host:
            # Pour l'hôte : voir les réponses des participants dans sa langue
            if not is_host_message:  # Message d'un participant
                participant_response = last_translation['translated'].get(user_language, '')
                return jsonify({
                    'success': True,
                    'original': participant_response,
                    'translated': '',
                    'timestamp': last_translation['timestamp'].isoformat(),
                    'is_host': True,
                    'show_translation': False,
                    'sender_id': last_translation.get('sender_id')
                })
            else:  # Propre message de l'hôte
                return jsonify({
                    'success': True,
                    'original': last_translation['original'],
                    'translated': '',
                    'timestamp': last_translation['timestamp'].isoformat(),
                    'is_host': True,
                    'show_translation': False,
                    'sender_id': last_translation.get('sender_id')
                })
        
        else:
            # Pour les participants : voir les messages de l'hôte traduits
            if is_host_message:  # Message de l'hôte
                translated_text = last_translation['translated'].get(user_language, '')
                
                return jsonify({
                    'success': True,
                    'original': last_translation['original'],
                    'translated': translated_text,
                    'timestamp': last_translation['timestamp'].isoformat(),
                    'is_host': False,
                    'show_translation': True,
                    'enable_speech': last_translation.get('enable_speech', False),
                    'sender_id': last_translation.get('sender_id')
                })
                
            elif last_translation.get('source_language') == user_language:  # Son propre message
                # Le participant voit sa propre traduction vers la langue de l'hôte
                host_user = None
                for u in room.users.values():
                    if u.is_host:
                        host_user = u
                        break
                host_language = host_user.language if host_user else 'fr'
                host_translation = last_translation['translated'].get(host_language, '')
                return jsonify({
                    'success': True,
                    'original': last_translation['original'],  # Son texte original
                    'translated': host_translation,  # Traduction vers langue hôte
                    'timestamp': last_translation['timestamp'].isoformat(),
                    'is_host': False,
                    'show_own_message': True,
                    'show_translation': False,
                    'sender_id': last_translation.get('sender_id')
                })
            else:  # Message d'un autre utilisateur
                return jsonify({
                    'success': True,
                    'original': '',
                    'translated': '',
                    'timestamp': last_translation['timestamp'].isoformat(),
                    'is_host': False,
                    'show_translation': False,
                    'sender_id': last_translation.get('sender_id')
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


