import socket  # Import socket au tout début du fichier, avant tout autre code
from room_manager import room_manager
from translation_manager import translation_manager
import sys
import os
import tempfile
import time
import datetime
import ssl
import threading
import webbrowser
import atexit
import logging
import re
import json
import subprocess
import requests
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from deep_translator import GoogleTranslator, MyMemoryTranslator
from OpenSSL import crypto
import qrcode
from io import BytesIO

# Optimisation: préchargement pour accélérer l'exécution
import gc
gc.disable()  # Désactiver temporairement le garbage collector pour accélérer le démarrage

try:
    from pyngrok import ngrok, conf
    PYNGROK_AVAILABLE = True
except ImportError:
    PYNGROK_AVAILABLE = False

# ============================================================
# GÉNÉRATION DE CERTIFICAT SSL AUTO-SIGNÉ
# ============================================================

def create_self_signed_cert(cert_file="cert.pem", key_file="key.pem"):
    """
    Crée un certificat SSL auto-signé amélioré pour le développement local.
    """
    # Création du répertoire certs s'il n'existe pas
    certs_dir = 'certs'
    if not os.path.exists(certs_dir):
        os.makedirs(certs_dir)
    
    cert_path = os.path.join(certs_dir, cert_file)
    key_path = os.path.join(certs_dir, key_file)
    
    # Si les fichiers existent déjà, pas besoin de les recréer
    if os.path.exists(cert_path) and os.path.exists(key_path):
        # Optimisation: pas besoin d'afficher le message, juste retourner les chemins
        return cert_path, key_path
    
    # Créer une paire de clés plus forte
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 4096)  # Clé RSA de 4096 bits au lieu de 2048
    
    # Créer un certificat auto-signé
    cert = crypto.X509()
    cert.get_subject().C = "FR"  # Pays
    cert.get_subject().ST = "France"  # État/Région
    cert.get_subject().L = "Local"  # Ville
    cert.get_subject().O = "TradLive"  # Organisation
    cert.get_subject().OU = "Development"  # Unité d'organisation
    cert.get_subject().CN = "TradLive Local"  # Common Name plus explicite
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)  # Valide pour 10 ans au lieu de 1
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')
    
    # Écrire le certificat et la clé dans des fichiers
    with open(cert_path, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    
    with open(key_path, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))
    
    print(f"Certificat SSL auto-signé créé avec succès dans le dossier '{certs_dir}'")
    print(f"Ce certificat est valide pour 10 ans et devrait être installé sur tous vos appareils")
    return cert_path, key_path

# ============================================================
# VARIABLES GLOBALES
# ============================================================

# Verrou pour la synthèse vocale
speech_lock = threading.Lock()
# Variable pour indiquer si une synthèse vocale est en cours
speaking_in_progress = False

# Variables pour le heartbeat et le statut du client
last_heartbeat = datetime.datetime.now()
heartbeat_lock = threading.Lock()
server_running = True
shutdown_timer = None
heartbeat_thread = None

# Variable pour le tunnel
tunnel_process = None
tunnel_url = None
using_tunnel = False
tunnel_lock = threading.Lock()

# Variables pour ngrok
ngrok_tunnel = None
ngrok_start_time = None
ngrok_reconnect_timer = None
ngrok_mode = False

# Cache pour les traductions (pour éviter de re-traduire les mêmes phrases)
translation_cache = {}
MAX_CACHE_SIZE = 200  # Nombre maximum d'entrées dans le cache

# ============================================================
# INITIALISATION DE L'APPLICATION FLASK
# ============================================================

app = Flask(__name__, template_folder='templates')

# Fonction pour précharger les templates
def preload_templates_function():
    # Précharger les templates pour accélérer les premières requêtes
    try:
        app.jinja_env.cache = {}  # Vider le cache existant
        # Préchauffer le cache avec les templates principaux
        render_template('index.html', translated="", original="", lang="en")
        render_template('phone.html', translated="", original="", lang="en")
        render_template('desktop.html', translated="", original="", lang="en")
    except Exception as e:
        print(f"Erreur lors du préchargement des templates: {str(e)}")
        pass  # Continuer malgré les erreurs

# Dans Flask 2.0+, we utilisons before_request avec un drapeau pour exécuter le code une seule fois
_templates_preloaded = False

@app.before_request
def preload_templates():
    global _templates_preloaded
    if not _templates_preloaded:
        with app.app_context():
            preload_templates_function()
        _templates_preloaded = True

# Variable globale pour stocker la dernière traduction
last_translation = {"original": "", "translated": "", "language": ""}

# Configuration de pygame pour la lecture audio
pygame.mixer.init()

# Variable globale pour le port
port = 443

# ============================================================
# SURVEILLANCE DU HEARTBEAT
# ============================================================

def check_heartbeat():
    """Vérifie régulièrement si le client est toujours connecté via le heartbeat"""
    global server_running
    
    while server_running:
        try:
            time.sleep(5)  # Vérifier toutes les 5 secondes
            
            with heartbeat_lock:
                time_since_last_heartbeat = (datetime.datetime.now() - last_heartbeat).total_seconds()
                
                # Si pas de heartbeat depuis plus de 15 secondes, on considère que le client est déconnecté
                if time_since_last_heartbeat > 15:
                    print("\nAucune activité client détectée depuis 15 secondes. Arrêt du serveur...")
                    server_running = False
                    
                    # Utiliser os._exit() directement au lieu de schedule_shutdown
                    # Cela est plus direct et évite certains problèmes
                    print("Fermeture du programme...")
                    os._exit(0)
        except Exception as e:
            print(f"Erreur dans la vérification du heartbeat: {str(e)}")
            # Continuer malgré les erreurs

def schedule_shutdown():
    """Programme l'arrêt du serveur après un court délai"""
    global shutdown_timer
    
    if shutdown_timer:
        shutdown_timer.cancel()
    
    # Terminer le processus directement
    print("Fermeture du programme...")
    time.sleep(0.5)  # Optimisation: réduit le délai à 0.5 seconde
    os._exit(0)

def shutdown_server():
    """Arrête le serveur Flask et termine le processus"""
    print("Fermeture du programme...")
    # Arrêt du serveur
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        # Si nous ne pouvons pas arrêter le serveur proprement, on force l'arrêt du programme
        os._exit(0)
    else:
        func()

def cleanup():
    """Fonction de nettoyage exécutée à la sortie du programme"""
    global server_running
    
    server_running = False
    
    # Arrêter tous les threads en cours
    if heartbeat_thread and heartbeat_thread.is_alive():
        heartbeat_thread.join(timeout=0.5)  # Optimisation: réduit le timeout à 0.5 seconde
    
    if shutdown_timer:
        shutdown_timer.cancel()
    
    # Arrêter ngrok si nécessaire
    if ngrok_mode:
        stop_ngrok()
    
    # Arrêter pygame
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        pygame.mixer.quit()
        pygame.quit()
    except:
        pass
    
    # Réactiver le garbage collector
    gc.enable()
    
    print("Nettoyage effectué, fermeture du programme.")

# Enregistrer la fonction de nettoyage à exécuter lors de la sortie du programme
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
    
    # Créer une image QR code
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Créer un buffer pour l'image
    buffer = BytesIO()
    img.save(buffer)
    buffer.seek(0)
    return buffer

# Fonction pour afficher un QR code dans le terminal
def display_terminal_qr(url):
    """Affiche un QR code ASCII dans le terminal"""
    try:
        import qrcode.console
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.make()
        qrcode.console.print_ascii(qr)
        print(f"\nScannez ce QR code avec votre téléphone pour accéder à l'application")
        print(f"ou entrez l'URL manuellement: {url}")
    except ImportError:
        print(f"URL de l'application: {url}")
        print("Installez 'qrcode' pour afficher un QR code dans le terminal")

# ============================================================
# DICTIONNAIRES DE TRADUCTION
# ============================================================

# Dictionnaire complet des expressions courantes françaises et leurs traductions
common_phrases = {
    # Phrases existantes
    "salut": {
        "en": "hello",
        "es": "hola",
        "de": "hallo",
        "it": "ciao",
        "pt": "olá",
        "ru": "привет",
        "uk": "привіт",
        "zh-CN": "你好",
        "ja": "こんにちは",
        "ar": "مرحبا",
        "hi": "नमस्ते",
        "bn": "হ্যালো",
        "te": "హలో",
        "mr": "हॅलो",
        "fa": "سلام"
    },
    "bonjour": {
        "en": "good morning",
        "es": "buenos días",
        "de": "guten morgen",
        "it": "buongiorno",
        "pt": "bom dia",
        "ru": "доброе утро",
        "uk": "доброго ранку",
        "zh-CN": "早上好",
        "ja": "おはようございます",
        "ar": "صباح الخير",
        "hi": "सुप्रभात",
        "bn": "সুপ্রভাত",
        "te": "శుభోదయం",
        "mr": "सुप्रभात",
        "fa": "صبح بخیر"
    },
    "ca va": {
        "en": "how are you",
        "es": "cómo estás",
        "de": "wie geht es dir",
        "it": "come stai",
        "pt": "como vai",
        "ru": "как дела",
        "uk": "як справи",
        "zh-CN": "你好吗",
        "ja": "お元気ですか",
        "ar": "كيف حالك",
        "hi": "आप कैसे हैं",
        "bn": "আপনি কেমন আছেন",
        "te": "మీరు ఎలా ఉన్నారు",
        "mr": "तू कसा आहेस",
        "fa": "حال شما چطور است"
    },
    "ça va": {
        "en": "how are you",
        "es": "cómo estás",
        "de": "wie geht es dir",
        "it": "come stai",
        "pt": "como vai",
        "ru": "как дела",
        "uk": "як справи",
        "zh-CN": "你好吗",
        "ja": "お元気ですか",
        "ar": "كيف حالك",
        "hi": "आप कैसे हैं",
        "bn": "আপনি কেমন আছেন",
        "te": "మీరు ఎలా ఉన్నారు",
        "mr": "तू कसा आहेस",
        "fa": "حال شما چطور است"
    },
    "salut ça va": {
        "en": "hello how are you",
        "es": "hola cómo estás",
        "de": "hallo wie geht es dir",
        "it": "ciao come stai",
        "pt": "olá como vai",
        "ru": "привет как дела",
        "uk": "привіт як справи",
        "zh-CN": "你好吗",
        "ja": "こんにちは、お元気ですか",
        "ar": "مرحبا كيف حالك",
        "hi": "नमस्ते आप कैसे हैं",
        "bn": "হ্যালো আপনি কেমন আছেন",
        "te": "హలో మీరు ఎలా ఉన్నారు",
        "mr": "हॅलो तू कसा आहेस",
        "fa": "سلام حال شما چطور است"
    },
    "comment allez-vous": {
        "en": "how are you",
        "es": "cómo está usted",
        "de": "wie geht es Ihnen",
        "it": "come sta",
        "pt": "como está",
        "ru": "как вы поживаете",
        "uk": "як ви",
        "zh-CN": "您好吗",
        "ja": "お元気ですか",
        "ar": "كيف حالك",
        "hi": "आप कैसे हैं",
        "bn": "আপনি কেমন আছেন",
        "te": "మీరు ఎలా ఉన్నారు",
        "mr": "तुम्ही कसे आहात",
        "fa": "حال شما چطور است"
    },
    "bonne journée": {
        "en": "have a good day",
        "es": "que tengas un buen día",
        "de": "einen schönen Tag noch",
        "it": "buona giornata",
        "pt": "tenha um bom dia",
        "ru": "хорошего дня",
        "uk": "гарного дня",
        "zh-CN": "祝你有美好的一天",
        "ja": "良い一日を",
        "ar": "يوم سعيد",
        "hi": "आपका दिन शुभ हो",
        "bn": "শুভ দিন",
        "te": "శుభదినం",
        "mr": "शुभ दिवस",
        "fa": "روز خوبی داشته باشید"
    },
    "au revoir": {
        "en": "goodbye",
        "es": "adiós",
        "de": "auf wiedersehen",
        "it": "arrivederci",
        "pt": "adeus",
        "ru": "до свидания",
        "uk": "до побачення",
        "zh-CN": "再见",
        "ja": "さようなら",
        "ar": "وداعا",
        "hi": "अलविदा",
        "bn": "বিদায়",
        "te": "వీడ్కోలు",
        "mr": "निरोप",
        "fa": "خداحافظ"
    },
    "merci": {
        "en": "thank you",
        "es": "gracias",
        "de": "danke",
        "it": "grazie",
        "pt": "obrigado",
        "ru": "спасибо",
        "uk": "дякую",
        "zh-CN": "谢谢",
        "ja": "ありがとう",
        "ar": "شكرا لك",
        "hi": "धन्यवाद",
        "bn": "ধন্যবাদ",
        "te": "ధన్యవాదాలు",
        "mr": "धन्यवाद",
        "fa": "متشکرم"
    },
    
    # Nouvelles phrases
    "excusez-moi": {
        "en": "excuse me",
        "es": "disculpe",
        "de": "entschuldigung",
        "it": "scusi",
        "pt": "com licença",
        "ru": "извините",
        "uk": "вибачте",
        "zh-CN": "对不起",
        "ja": "すみません",
        "ar": "عذرا",
        "hi": "क्षमा करें",
        "bn": "ক্ষমা করুন",
        "te": "క్షమించండి",
        "mr": "क्षमा करा",
        "fa": "ببخشید"
    },
    "je ne comprends pas": {
        "en": "I don't understand",
        "es": "no entiendo",
        "de": "ich verstehe nicht",
        "it": "non capisco",
        "pt": "eu não entendo",
        "ru": "я не понимаю",
        "uk": "я не розумію",
        "zh-CN": "我不明白",
        "ja": "わかりません",
        "ar": "أنا لا أفهم",
        "hi": "मैं समझ नहीं पा रहा हूँ",
        "bn": "আমি বুঝতে পারছি না",
        "te": "నాకు అర్థం కాలేదు",
        "mr": "मला समजत नाही",
        "fa": "من نمی فهمم"
    },
    "parlez-vous français": {
        "en": "do you speak French",
        "es": "hablas francés",
        "de": "sprechen Sie Französisch",
        "it": "parli francese",
        "pt": "você fala francês",
        "ru": "вы говорите по-французски",
        "uk": "ви говорите французькою",
        "zh-CN": "你会说法语吗",
        "ja": "フランス語を話せますか",
        "ar": "هل تتكلم الفرنسية",
        "hi": "क्या आप फ्रेंच बोलते हैं",
        "bn": "আপনি কি ফরাসি বলতে পারেন",
        "te": "మీరు ఫ్రెంచ్ మాట్లాడతారా",
        "mr": "तुम्ही फ्रेंच बोलता का",
        "fa": "آیا فرانسوی صحبت می کنید"
    },
    "je m'appelle": {
        "en": "my name is",
        "es": "me llamo",
        "de": "ich heiße",
        "it": "mi chiamo",
        "pt": "meu nome é",
        "ru": "меня зовут",
        "uk": "мене звати",
        "zh-CN": "我的名字是",
        "ja": "私の名前は",
        "ar": "اسمي",
        "hi": "मेरा नाम है",
        "bn": "আমার নাম",
        "te": "నా పేరు",
        "mr": "माझे नाव आहे",
        "fa": "اسم من است"
    },
    "où sont les toilettes": {
        "en": "where is the bathroom",
        "es": "dónde está el baño",
        "de": "wo ist die toilette",
        "it": "dove sono i bagni",
        "pt": "onde fica o banheiro",
        "ru": "где туалет",
        "uk": "де туалет",
        "zh-CN": "洗手间在哪里",
        "ja": "お手洗いはどこですか",
        "ar": "أين المرحاض",
        "hi": "शौचालय कहाँ है",
        "bn": "টয়লেট কোথায়",
        "te": "మరుగుదొడ్డి ఎక్కడ ఉంది",
        "mr": "शौचालय कुठे आहे",
        "fa": "سرویس بهداشتی کجاست"
    },
    "je voudrais": {
        "en": "I would like",
        "es": "me gustaría",
        "de": "ich möchte",
        "it": "vorrei",
        "pt": "eu gostaria",
        "ru": "я хотел бы",
        "uk": "я хотів би",
        "zh-CN": "我想要",
        "ja": "私は～が欲しいです",
        "ar": "أود أن",
        "hi": "मैं चाहूंगा",
        "bn": "আমি চাই",
        "te": "నేను కోరుకుంటున్నాను",
        "mr": "मला हवे आहे",
        "fa": "من می خواهم"
    },
    "s'il vous plaît": {
        "en": "please",
        "es": "por favor",
        "de": "bitte",
        "it": "per favore",
        "pt": "por favor",
        "ru": "пожалуйста",
        "uk": "будь ласка",
        "zh-CN": "请",
        "ja": "お願いします",
        "ar": "من فضلك",
        "hi": "कृपया",
        "bn": "দয়া করে",
        "te": "దయచేసి",
        "mr": "कृपया",
        "fa": "لطفا"
    },
    "combien ça coûte": {
        "en": "how much does it cost",
        "es": "cuánto cuesta",
        "de": "wie viel kostet es",
        "it": "quanto costa",
        "pt": "quanto custa",
        "ru": "сколько это стоит",
        "uk": "скільки це коштує",
        "zh-CN": "这个多少钱",
        "ja": "いくらですか",
        "ar": "كم يكلف هذا",
        "hi": "यह कितने का है",
        "bn": "এর দাম কত",
        "te": "ఇది ఎంత ఖర్చు",
        "mr": "याची किंमत किती आहे",
        "fa": "چقدر هزینه دارد"
    },
    
    # Vocabulaire pour l'apprentissage du numérique
    "ordinateur": {
        "en": "computer",
        "es": "ordenador",
        "de": "computer",
        "it": "computer",
        "pt": "computador",
        "ru": "компьютер",
        "uk": "комп'ютер",
        "zh-CN": "电脑",
        "ja": "コンピューター",
        "ar": "كمبيوتر",
        "hi": "कंप्यूटर",
        "bn": "কম্পিউটার",
        "te": "కంప్యూటర్",
        "mr": "संगणक",
        "fa": "کامپیوتر"
    },
    "internet": {
        "en": "internet",
        "es": "internet",
        "de": "internet",
        "it": "internet",
        "pt": "internet",
        "ru": "интернет",
        "uk": "інтернет",
        "zh-CN": "互联网",
        "ja": "インターネット",
        "ar": "إنترنت",
        "hi": "इंटरनेट",
        "bn": "ইন্টারনেট",
        "te": "ఇంటర్నెట్",
        "mr": "इंटरनेट",
        "fa": "اینترنت"
    },
    "mot de passe": {
        "en": "password",
        "es": "contraseña",
        "de": "passwort",
        "it": "password",
        "pt": "senha",
        "ru": "пароль",
        "uk": "пароль",
        "zh-CN": "密码",
        "ja": "パスワード",
        "ar": "كلمة المرور",
        "hi": "पासवर्ड",
        "bn": "পাসওয়ার্ড",
        "te": "పాస్వర్డ్",
        "mr": "पासवर्ड",
        "fa": "رمز عبور"
    },
    "cliquez ici": {
        "en": "click here",
        "es": "haga clic aquí",
        "de": "klicken Sie hier",
        "it": "clicca qui",
        "pt": "clique aqui",
        "ru": "нажмите здесь",
        "uk": "натисніть тут",
        "zh-CN": "点击这里",
        "ja": "ここをクリック",
        "ar": "انقر هنا",
        "hi": "यहां क्लिक करें",
        "bn": "এখানে ক্লিক করুন",
        "te": "ఇక్కడ క్లిక్ చేయండి",
        "mr": "येथे क्लिक करा",
        "fa": "اینجا کلیک کنید"
    },
    "télécharger": {
        "en": "download",
        "es": "descargar",
        "de": "herunterladen",
        "it": "scaricare",
        "pt": "baixar",
        "ru": "скачать",
        "uk": "завантажити",
        "zh-CN": "下载",
        "ja": "ダウンロード",
        "ar": "تحميل",
        "hi": "डाउनलोड",
        "bn": "ডাউনলোড",
        "te": "డౌన్లోడ్",
        "mr": "डाउनलोड",
        "fa": "دانلود"
    },
    "enregistrer": {
        "en": "save",
        "es": "guardar",
        "de": "speichern",
        "it": "salvare",
        "pt": "salvar",
        "ru": "сохранить",
        "uk": "зберегти",
        "zh-CN": "保存",
        "ja": "保存",
        "ar": "حفظ",
        "hi": "सहेजें",
        "bn": "সংরক্ষণ",
        "te": "సేవ్",
        "mr": "जतन करा",
        "fa": "ذخیره"
    },
    "email": {
        "en": "email",
        "es": "correo electrónico",
        "de": "e-mail",
        "it": "email",
        "pt": "email",
        "ru": "электронная почта",
        "uk": "електронна пошта",
        "zh-CN": "电子邮件",
        "ja": "メール",
        "ar": "البريد الإلكتروني",
        "hi": "ईमेल",
        "bn": "ইমেল",
        "te": "ఇమెయిల్",
        "mr": "ईमेल",
        "fa": "ایمیل"
    },
    "smartphone": {
        "en": "smartphone",
        "es": "smartphone",
        "de": "smartphone",
        "it": "smartphone",
        "pt": "smartphone",
        "ru": "смартфон",
        "uk": "смартфон",
        "zh-CN": "智能手机",
        "ja": "スマートフォン",
        "ar": "هاتف ذكي",
        "hi": "स्मार्टफोन",
        "bn": "স্মার্টফোন",
        "te": "స్మార్ట్ఫోన్",
        "mr": "स्मार्टफोन",
        "fa": "گوشی هوشمند"
    },
    "application": {
        "en": "application",
        "es": "aplicación",
        "de": "anwendung",
        "it": "applicazione",
        "pt": "aplicativo",
        "ru": "приложение",
        "uk": "додаток",
        "zh-CN": "应用程序",
        "ja": "アプリケーション",
        "ar": "تطبيق",
        "hi": "एप्लिकेशन",
        "bn": "অ্যাপ্লিকেশন",
        "te": "అప్లికేషన్",
        "mr": "अॅप्लिकेशन",
        "fa": "برنامه کاربردی"
    },
    "wifi": {
        "en": "wifi",
        "es": "wifi",
        "de": "wlan",
        "it": "wifi",
        "pt": "wifi",
        "ru": "вай-фай",
        "uk": "вай-фай",
        "zh-CN": "无线网络",
        "ja": "ワイファイ",
        "ar": "واي فاي",
        "hi": "वाईफाई",
        "bn": "ওয়াইফাই",
        "te": "వైఫై",
        "mr": "वायफाय",
        "fa": "وای فای"
    },
    "comment ça marche": {
        "en": "how does it work",
        "es": "cómo funciona",
        "de": "wie funktioniert das",
        "it": "come funziona",
        "pt": "como funciona",
        "ru": "как это работает",
        "uk": "як це працює",
        "zh-CN": "这个怎么用",
        "ja": "これはどう動作しますか",
        "ar": "كيف يعمل هذا",
        "hi": "यह कैसे काम करता है",
        "bn": "এটা কিভাবে কাজ করে",
        "te": "ఇది ఎలా పనిచేస్తుంది",
        "mr": "हे कसे कार्य करते",
        "fa": "این چگونه کار می کند"
    },
    "ouvrir un fichier": {
        "en": "open a file",
        "es": "abrir un archivo",
        "de": "eine datei öffnen",
        "it": "aprire un file",
        "pt": "abrir um arquivo",
        "ru": "открыть файл",
        "uk": "відкрити файл",
        "zh-CN": "打开文件",
        "ja": "ファイルを開く",
        "ar": "فتح ملف",
        "hi": "फाइल खोलें",
        "bn": "একটি ফাইল খুলুন",
        "te": "ఫైల్ తెరవండి",
        "mr": "फाईल उघडा",
        "fa": "باز کردن فایل"
    },
    "créer un compte": {
        "en": "create an account",
        "es": "crear una cuenta",
        "de": "ein konto erstellen",
        "it": "creare un account",
        "pt": "criar uma conta",
        "ru": "создать учетную запись",
        "uk": "створити обліковий запис",
        "zh-CN": "创建账户",
        "ja": "アカウントを作成する",
        "ar": "إنشاء حساب",
        "hi": "खाता बनाएं",
        "bn": "একটি অ্যাকাউন্ট তৈরি করুন",
        "te": "ఖాతాను సృష్టించండి",
        "mr": "खाते तयार करा",
        "fa": "ایجاد حساب کاربری"
    },
    "se connecter": {
        "en": "log in",
        "es": "iniciar sesión",
        "de": "anmelden",
        "it": "accedere",
        "pt": "entrar",
        "ru": "войти",
        "uk": "увійти",
        "zh-CN": "登录",
        "ja": "ログイン",
        "ar": "تسجيل الدخول",
        "hi": "लॉग इन",
        "bn": "লগ ইন",
        "te": "లాగిన్",
        "mr": "लॉग इन",
        "fa": "ورود"
    },
    "problème technique": {
        "en": "technical issue",
        "es": "problema técnico",
        "de": "technisches problem",
        "it": "problema tecnico",
        "pt": "problema técnico",
        "ru": "техническая проблема",
        "uk": "технічна проблема",
        "zh-CN": "技术问题",
        "ja": "技術的な問題",
        "ar": "مشكلة تقنية",
        "hi": "तकनीकी समस्या",
        "bn": "প্রযুক্তিগত সমস্যা",
        "te": "సాంకేతిక సమస్య",
        "mr": "तांत्रिक समस्या",
        "fa": "مشکل فنی"
    },
    "faire une recherche": {
        "en": "do a search",
        "es": "hacer una búsqueda",
        "de": "eine suche durchführen",
        "it": "fare una ricerca",
        "pt": "fazer uma pesquisa",
        "ru": "выполнить поиск",
        "uk": "виконати пошук",
        "zh-CN": "进行搜索",
        "ja": "検索する",
        "ar": "إجراء بحث",
        "hi": "खोज करें",
        "bn": "অনুসন্ধান করুন",
        "te": "శోధన చేయండి",
        "mr": "शोध करा",
        "fa": "جستجو کنید"
    },
    "navigateur web": {
        "en": "web browser",
        "es": "navegador web",
        "de": "webbrowser",
        "it": "browser web",
        "pt": "navegador web",
        "ru": "веб-браузер",
        "uk": "веб-браузер",
        "zh-CN": "网页浏览器",
        "ja": "ウェブブラウザ",
        "ar": "متصفح الويب",
        "hi": "वेब ब्राउज़र",
        "bn": "ওয়েব ব্রাউজার",
        "te": "వెబ్ బ్రౌజర్",
        "mr": "वेब ब्राउझर",
        "fa": "مرورگر وب"
    },
    "cliquez sur le bouton": {
        "en": "click on the button",
        "es": "haga clic en el botón",
        "de": "klicken Sie auf die Schaltfläche",
        "it": "clicca sul pulsante",
        "pt": "clique no botão",
        "ru": "нажмите на кнопку",
        "uk": "натисніть на кнопку",
        "zh-CN": "点击按钮",
        "ja": "ボタンをクリックしてください",
        "ar": "انقر على الزر",
        "hi": "बटन पर क्लिक करें",
        "bn": "বাটনে ক্লিক করুন",
        "te": "బటన్‌పై క్లిక్ చేయండి",
        "mr": "बटणावर क्लिक करा",
        "fa": "روی دکمه کلیک کنید"
    },
    "cours en ligne": {
        "en": "online course",
        "es": "curso en línea",
        "de": "online-kurs",
        "it": "corso online",
        "pt": "curso online",
        "ru": "онлайн-курс",
        "uk": "онлайн-курс",
        "zh-CN": "在线课程",
        "ja": "オンラインコース",
        "ar": "دورة عبر الإنترنت",
        "hi": "ऑनलाइन कोर्स",
        "bn": "অনলাইন কোর্স",
        "te": "ఆన్‌లైన్ కోర్స్",
        "mr": "ऑनलाइन कोर्स",
        "fa": "دوره آنلاین"
    },
    "tutoriel": {
        "en": "tutorial",
        "es": "tutorial",
        "de": "tutorial",
        "it": "tutorial",
        "pt": "tutorial",
        "ru": "учебник",
        "uk": "посібник",
        "zh-CN": "教程",
        "ja": "チュートリアル",
        "ar": "البرنامج التعليمي",
        "hi": "ट्यूटोरियल",
        "bn": "টিউটোরিয়াল",
        "te": "ట్యుటోరియల్",
        "mr": "ट्युटोरियल",
        "fa": "آموزش"
    },
    "suivant": {
        "en": "next",
        "es": "siguiente",
        "de": "weiter",
        "it": "successivo",
        "pt": "próximo",
        "ru": "следующий",
        "uk": "далі",
        "zh-CN": "下一步",
        "ja": "次へ",
        "ar": "التالي",
        "hi": "अगला",
        "bn": "পরবর্তী",
        "te": "తరువాత",
        "mr": "पुढील",
        "fa": "بعدی"
    },
   "précédent": {
        "en": "previous",
        "es": "anterior",
        "de": "zurück",
        "it": "precedente",
        "pt": "anterior",
        "ru": "предыдущий",
        "uk": "назад",
        "zh-CN": "上一步",
        "ja": "前へ",
        "ar": "السابق",
        "hi": "पिछला",
        "bn": "পূর্ববর্তী",
        "te": "మునుపటి",
        "mr": "मागील",
        "fa": "قبلی"
    },
    "confirmer": {
        "en": "confirm",
        "es": "confirmar",
        "de": "bestätigen",
        "it": "confermare",
        "pt": "confirmar",
        "ru": "подтвердить",
        "uk": "підтвердити",
        "zh-CN": "确认",
        "ja": "確認",
        "ar": "تأكيد",
        "hi": "पुष्टि करें",
        "bn": "নিশ্চিত করুন",
        "te": "నిర్ధారించండి",
        "mr": "पुष्टी करा",
        "fa": "تایید"
    },
    "annuler": {
        "en": "cancel",
        "es": "cancelar",
        "de": "abbrechen",
        "it": "annullare",
        "pt": "cancelar",
        "ru": "отменить",
        "uk": "скасувати",
        "zh-CN": "取消",
        "ja": "キャンセル",
        "ar": "إلغاء",
        "hi": "रद्द करें",
        "bn": "বাতিল করুন",
        "te": "రద్దు చేయండి",
        "mr": "रद्द करा",
        "fa": "لغو"
    },
    "taper votre texte": {
        "en": "type your text",
        "es": "escriba su texto",
        "de": "geben Sie Ihren Text ein",
        "it": "digita il tuo testo",
        "pt": "digite seu texto",
        "ru": "введите свой текст",
        "uk": "введіть свій текст",
        "zh-CN": "输入您的文本",
        "ja": "テキストを入力してください",
        "ar": "اكتب النص الخاص بك",
        "hi": "अपना टेक्स्ट टाइप करें",
        "bn": "আপনার টেক্সট টাইপ করুন",
        "te": "మీ టెక్స్ట్‌ని టైప్ చేయండి",
        "mr": "तुमचा मजकूर टाइप करा",
        "fa": "متن خود را تایپ کنید"
    },
    "partager": {
        "en": "share",
        "es": "compartir",
        "de": "teilen",
        "it": "condividere",
        "pt": "compartilhar",
        "ru": "поделиться",
        "uk": "поділитися",
        "zh-CN": "分享",
        "ja": "共有",
        "ar": "مشاركة",
        "hi": "साझा करें",
        "bn": "শেয়ার করুন",
        "te": "షేర్ చేయండి",
        "mr": "शेअर करा",
        "fa": "اشتراک گذاری"
    },
    "fichier": {
        "en": "file",
        "es": "archivo",
        "de": "datei",
        "it": "file",
        "pt": "arquivo",
        "ru": "файл",
        "uk": "файл",
        "zh-CN": "文件",
        "ja": "ファイル",
        "ar": "ملف",
        "hi": "फ़ाइल",
        "bn": "ফাইল",
        "te": "ఫైల్",
        "mr": "फाईल",
        "fa": "فایل"
    },
    "dossier": {
        "en": "folder",
        "es": "carpeta",
        "de": "ordner",
        "it": "cartella",
        "pt": "pasta",
        "ru": "папка",
        "uk": "папка",
        "zh-CN": "文件夹",
        "ja": "フォルダ",
        "ar": "مجلد",
        "hi": "फ़ोल्डर",
        "bn": "ফোল্ডার",
        "te": "ఫోల్డర్",
        "mr": "फोल्डर",
        "fa": "پوشه"
    },
    "double-cliquez": {
        "en": "double-click",
        "es": "doble clic",
        "de": "doppelklicken",
        "it": "doppio clic",
        "pt": "clique duplo",
        "ru": "двойной щелчок",
        "uk": "подвійний клік",
        "zh-CN": "双击",
        "ja": "ダブルクリック",
        "ar": "انقر نقرًا مزدوجًا",
        "hi": "डबल-क्लिक",
        "bn": "ডাবল-ক্লিক",
        "te": "డబుల్-క్లిక్",
        "mr": "डबल-क्लिक",
        "fa": "دابل کلیک"
    },
    "écran tactile": {
        "en": "touchscreen",
        "es": "pantalla táctil",
        "de": "touchscreen",
        "it": "touchscreen",
        "pt": "tela sensível ao toque",
        "ru": "сенсорный экран",
        "uk": "сенсорний екран",
        "zh-CN": "触摸屏",
        "ja": "タッチスクリーン",
        "ar": "شاشة تعمل باللمس",
        "hi": "टचस्क्रीन",
        "bn": "টাচস্ক্রিন",
        "te": "టచ్‌స్క్రీన్",
        "mr": "टचस्क्रीन",
        "fa": "صفحه لمسی"
    },
    "glisser-déposer": {
        "en": "drag and drop",
        "es": "arrastrar y soltar",
        "de": "drag and drop",
        "it": "drag and drop",
        "pt": "arrastar e soltar",
        "ru": "перетащить",
        "uk": "перетягнути",
        "zh-CN": "拖放",
        "ja": "ドラッグアンドドロップ",
        "ar": "اسحب وأفلت",
        "hi": "ड्रैग एंड ड्रॉप",
        "bn": "টেনে ছাড়ুন",
        "te": "డ్రాగ్ అండ్ డ్రాప్",
        "mr": "ड्रॅग आणि ड्रॉप",
        "fa": "کشیدن و رها کردن"
    },
    "copier-coller": {
        "en": "copy-paste",
        "es": "copiar y pegar",
        "de": "kopieren und einfügen",
        "it": "copia e incolla",
        "pt": "copiar e colar",
        "ru": "копировать-вставить",
        "uk": "копіювати-вставити",
        "zh-CN": "复制粘贴",
        "ja": "コピー＆ペースト",
        "ar": "نسخ ولصق",
        "hi": "कॉपी-पेस्ट",
        "bn": "কপি-পেস্ট",
        "te": "కాపీ-పేస్ట్",
        "mr": "कॉपी-पेस्ट",
        "fa": "کپی-پیست"
    },
    "installer une application": {
        "en": "install an application",
        "es": "instalar una aplicación",
        "de": "eine Anwendung installieren",
        "it": "installare un'applicazione",
        "pt": "instalar um aplicativo",
        "ru": "установить приложение",
        "uk": "встановити додаток",
        "zh-CN": "安装应用程序",
        "ja": "アプリをインストールする",
        "ar": "تثبيت تطبيق",
        "hi": "एप्लिकेशन इंस्टॉल करें",
        "bn": "অ্যাপ্লিকেশন ইনস্টল করুন",
        "te": "అప్లికేషన్‌ని ఇన్‌స్టాల్ చేయండి",
        "mr": "अॅप्लिकेशन इन्स्टॉल करा",
        "fa": "نصب برنامه"
    },
    "supprimer": {
        "en": "delete",
        "es": "eliminar",
        "de": "löschen",
        "it": "eliminare",
        "pt": "excluir",
        "ru": "удалить",
        "uk": "видалити",
        "zh-CN": "删除",
        "ja": "削除",
        "ar": "حذف",
        "hi": "हटाएं",
        "bn": "মুছুন",
        "te": "తొలగించండి",
        "mr": "हटवा",
        "fa": "حذف"
    },
    "mettre à jour": {
        "en": "update",
        "es": "actualizar",
        "de": "aktualisieren",
        "it": "aggiornare",
        "pt": "atualizar",
        "ru": "обновить",
        "uk": "оновити",
        "zh-CN": "更新",
        "ja": "更新",
        "ar": "تحديث",
        "hi": "अपडेट करें",
        "bn": "আপডেট করুন",
        "te": "నవీకరించండి",
        "mr": "अपडेट करा",
        "fa": "به روز رسانی"
    },
    "appuyer sur entrée": {
        "en": "press enter",
        "es": "pulsar intro",
        "de": "drücken Sie Enter",
        "it": "premere invio",
        "pt": "pressione enter",
        "ru": "нажмите Enter",
        "uk": "натисніть Enter",
        "zh-CN": "按回车键",
        "ja": "エンターキーを押してください",
        "ar": "اضغط على Enter",
        "hi": "एंटर दबाएं",
        "bn": "এন্টার টিপুন",
        "te": "ఎంటర్ నొక్కండి",
        "mr": "एंटर दाबा",
        "fa": "دکمه اینتر را فشار دهید"
    },
    "je n'arrive pas à me connecter": {
        "en": "I can't log in",
        "es": "no puedo iniciar sesión",
        "de": "ich kann mich nicht anmelden",
        "it": "non riesco ad accedere",
        "pt": "não consigo fazer login",
        "ru": "я не могу войти",
        "uk": "я не можу увійти",
        "zh-CN": "我无法登录",
        "ja": "ログインできません",
        "ar": "لا يمكنني تسجيل الدخول",
        "hi": "मैं लॉग इन नहीं कर पा रहा हूं",
        "bn": "আমি লগইন করতে পারছি না",
        "te": "నేను లాగిన్ చేయలేకపోతున్నాను",
        "mr": "मला लॉग इन करता येत नाही",
        "fa": "نمی توانم وارد شوم"
    },
    "vidéo": {
        "en": "video",
        "es": "video",
        "de": "video",
        "it": "video",
        "pt": "vídeo",
        "ru": "видео",
        "uk": "відео",
        "zh-CN": "视频",
        "ja": "ビデオ",
        "ar": "فيديو",
        "hi": "वीडियो",
        "bn": "ভিডিও",
        "te": "వీడియో",
        "mr": "व्हिडिओ",
        "fa": "ویدیو"
    },
    "réseau social": {
        "en": "social network",
        "es": "red social",
        "de": "soziales netzwerk",
        "it": "social network",
        "pt": "rede social",
        "ru": "социальная сеть",
        "uk": "соціальна мережа",
        "zh-CN": "社交网络",
        "ja": "ソーシャルネットワーク",
        "ar": "شبكة اجتماعية",
        "hi": "सोशल नेटवर्क",
        "bn": "সোশ্যাল নেটওয়ার্ক",
        "te": "సోషల్ నెట్‌వర్క్",
        "mr": "सोशल नेटवर्क",
        "fa": "شبکه اجتماعی"
    }
}

# Corrections pour certaines erreurs de traduction courantes
translation_corrections = {
    "en": {
        "he'll": "how are you",
        "how it goes": "how are you",
        "it's going": "how are you"
    }
}

# ============================================================
# FONCTIONS DE SYNTHÈSE VOCALE
# ============================================================

# Fonction pour initialiser et configurer la voix pyttsx3 (pour langues limitées)
def init_voice():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    # Vérifier si nous avons au moins 2 voix avant d'essayer d'accéder à la voix d'index 1
    if len(voices) > 1:
        engine.setProperty('voice', voices[1].id)  # Voix féminine généralement
    
    # Obtenir la vitesse actuelle
    rate = engine.getProperty('rate')
    # Définir une vitesse plus lente
    engine.setProperty('rate', rate-50)  # Réduire de 50 pour ralentir
    
    return engine

# Mapper les codes de langue pour gTTS
def map_lang_code_for_gtts(lang_code):
    # Table de conversion des codes pour gTTS
    code_map = {
        'zh-CN': 'zh-cn',
        'ja': 'ja',
        'ar': 'ar',
        'ru': 'ru',
        'uk': 'uk',
        'hi': 'hi',
        'bn': 'bn',
        'te': 'te',
        'mr': 'mr',
        'fa': 'fa',
        'en': 'en',
        'es': 'es',
        'de': 'de',
        'it': 'it',
        'pt': 'pt',
        # Ajouter d'autres mappages si nécessaire
    }
    return code_map.get(lang_code, 'en')  # Par défaut en anglais si non trouvé

# Créer un dossier temporaire portable
def get_temp_directory():
    # Obtenir le répertoire de l'exécutable ou du script
    if getattr(sys, 'frozen', False):
        # Si exécuté en tant qu'exécutable
        app_dir = os.path.dirname(sys.executable)
    else:
        # Si exécuté en tant que script
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Créer un dossier 'temp' dans le répertoire de l'application s'il n'existe pas
    temp_dir = os.path.join(app_dir, 'temp')
    if not os.path.exists(temp_dir):
        try:
            os.makedirs(temp_dir)
        except:
            # En cas d'échec, utiliser le dossier temporaire du système
            return tempfile.gettempdir()
    
    return temp_dir

# Fonction améliorée pour la synthèse vocale multilingue
def speak(text, lang='en'):
    """
    Version serveur : pas de synthèse vocale côté serveur
    L'audio est géré côté client dans le navigateur
    """
    print(f"Synthèse vocale demandée pour: {text[:50]}... (langue: {lang})")
    return  # Ne fait rien côté serveur
# ============================================================
# FONCTIONS DE TRADUCTION
# ============================================================

# Fonction de traduction améliorée
def translate_text(text, target_lang):
    try:
        # 0. Vérifier dans le cache d'abord (très rapide)
        cache_key = f"{text.lower()}|{target_lang}"
        if cache_key in translation_cache:
            print("Traduction trouvée dans le cache!")
            return translation_cache[cache_key]
        
        # 1. Normaliser le texte pour la recherche dans le dictionnaire
        text_normalized = text.lower().replace("'", " ").replace("-", " ").strip()
        
        # 2. Vérifier si le texte est dans notre dictionnaire de phrases communes
        if text_normalized in common_phrases and target_lang in common_phrases[text_normalized]:
            translation = common_phrases[text_normalized][target_lang]
            # Ajouter au cache
            translation_cache[cache_key] = translation
            return translation
        
        # 3. Essayer avec GoogleTranslator
        translator = GoogleTranslator(source='fr', target=target_lang)
        translated = translator.translate(text)
        
        # 4. Appliquer des corrections spécifiques à la langue
        if target_lang in translation_corrections:
            for wrong, correct in translation_corrections[target_lang].items():
                if wrong in translated.lower():
                    translated = translated.replace(wrong, correct)
        
        # 5. Ajouter au cache pour les futurs appels
        translation_cache[cache_key] = translated
        
        # 6. Limiter la taille du cache
        if len(translation_cache) > MAX_CACHE_SIZE:
            # Supprimer une entrée aléatoire
            translation_cache.pop(next(iter(translation_cache)))
        
        return translated
        
    except Exception as e:
        # 7. En cas d'échec, essayer avec MyMemoryTranslator
        try:
            translator = MyMemoryTranslator(source='fr', target=target_lang)
            translated = translator.translate(text)
            
            # Mettre en cache le résultat de la traduction de secours
            translation_cache[cache_key] = translated
            
            return translated
        except:
            # Si tout échoue, retourner un message d'erreur
            return f"Erreur de traduction: {str(e)}"

def translate_to_french(text, source_lang):
    """Fonction pour la traduction vers le français (langue étrangère -> français)"""
    try:
        # Utiliser le gestionnaire de traduction avec rotation
        translated = translation_manager.translate(text, source_lang, 'fr')
        return translated
    except Exception as e:
        # En cas d'échec, retourner un message d'erreur
        return f"Erreur de traduction: {str(e)}"


# ============================================================
# FONCTIONS POUR LE TUNNEL NGROK
# ============================================================

def setup_and_start_ngrok(port):
    """Configure et démarre un tunnel ngrok vers le port spécifié"""
    global ngrok_tunnel, ngrok_start_time, ngrok_mode
    
    if not PYNGROK_AVAILABLE:
        print("\nERREUR: Le module pyngrok n'est pas installé.")
        print("Pour l'installer, exécutez: pip install pyngrok")
        print("Impossible d'utiliser le mode tunnel.")
        return None
    
    try:
        # Configuration de ngrok
        conf.get_default().log_level = logging.ERROR  # Réduire la verbosité des logs
        conf.get_default().region = 'eu'  # Utiliser la région Europe pour de meilleures performances
        
        # Ouvrir un tunnel HTTP
        tunnel = ngrok.connect(port, 'http')
        
        # Extraire l'URL publique
        public_url = tunnel.public_url.replace('http://', 'https://')
        
        # Enregistrer l'heure de démarrage
        ngrok_start_time = datetime.datetime.now()
        ngrok_mode = True
        
        print(f"\nTunnel ngrok démarré avec succès!")
        print(f"URL externe: {public_url}")
        print(f"La session ngrok expirera dans 2 heures. Une reconnexion automatique sera tentée.")
        
        # Programmer une reconnexion avant l'expiration (après 1h55)
        schedule_ngrok_reconnect()
        
        return public_url
    except Exception as e:
        print(f"\nErreur lors du démarrage du tunnel ngrok: {str(e)}")
        return None

def schedule_ngrok_reconnect():
    """Programme une reconnexion du tunnel ngrok avant l'expiration de 2 heures"""
    global ngrok_reconnect_timer
    
    # Annuler tout timer existant
    if ngrok_reconnect_timer:
        ngrok_reconnect_timer.cancel()
    
    # Programmer une reconnexion après 1h55m (avant l'expiration de 2h)
    reconnect_delay = 115 * 60  # 1h55m en secondes
    
    def reconnect_ngrok():
        global ngrok_tunnel, ngrok_start_time
        
        if not ngrok_mode:
            return
            
        print("\nReconnexion automatique du tunnel ngrok avant expiration...")
        
        try:
            # Fermer le tunnel existant
            if ngrok_tunnel:
                ngrok.disconnect(ngrok_tunnel.public_url)
            
            # Ouvrir un nouveau tunnel
            new_tunnel = ngrok.connect(port, 'http')
            ngrok_tunnel = new_tunnel
            ngrok_start_time = datetime.datetime.now()
            
            # Programmer la prochaine reconnexion
            schedule_ngrok_reconnect()
            
            print(f"Tunnel ngrok reconnecté avec succès!")
            print(f"Nouvelle URL externe: {new_tunnel.public_url.replace('http://', 'https://')}")
            
        except Exception as e:
            print(f"Erreur lors de la reconnexion du tunnel ngrok: {str(e)}")
            
            # Tenter à nouveau dans 1 minute
            ngrok_reconnect_timer = threading.Timer(60, reconnect_ngrok)
            ngrok_reconnect_timer.daemon = True
            ngrok_reconnect_timer.start()
    
    # Créer et démarrer le timer
    ngrok_reconnect_timer = threading.Timer(reconnect_delay, reconnect_ngrok)
    ngrok_reconnect_timer.daemon = True
    ngrok_reconnect_timer.start()

def stop_ngrok():
    """Arrête le tunnel ngrok et annule le timer de reconnexion"""
    global ngrok_tunnel, ngrok_reconnect_timer, ngrok_mode
    
    # Annuler le timer de reconnexion
    if ngrok_reconnect_timer:
        ngrok_reconnect_timer.cancel()
        ngrok_reconnect_timer = None
    
    # Fermer le tunnel
    if ngrok_tunnel:
        try:
            ngrok.disconnect(ngrok_tunnel.public_url)
            print("Tunnel ngrok arrêté avec succès.")
        except:
            print("Erreur lors de l'arrêt du tunnel ngrok.")
        finally:
            ngrok_tunnel = None
            ngrok_mode = False
            
    # Arrêter tous les tunnels restants
    try:
        ngrok.kill()
    except:
        pass

def get_ngrok_time_left():
    """Retourne le temps restant avant l'expiration du tunnel ngrok"""
    if not ngrok_start_time:
        return None
    
    elapsed = (datetime.datetime.now() - ngrok_start_time).total_seconds()
    total_seconds = 2 * 60 * 60  # 2 heures en secondes
    remaining = total_seconds - elapsed
    
    if remaining <= 0:
        return 0
    
    # Convertir en heures:minutes:secondes
    hours = int(remaining // 3600)
    minutes = int((remaining % 3600) // 60)
    seconds = int(remaining % 60)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# ============================================================
# FONCTIONS RÉSEAU ET UTILITAIRES
# ============================================================

# Fonction optimisée pour obtenir l'adresse IP locale
def get_local_ip():
    try:
        # Méthode optimisée sans connexion externe
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)  # Timeout court
        try:
            # En utilisant une adresse de diffusion du réseau local
            s.connect(('10.255.255.255', 1))
            local_ip = s.getsockname()[0]
        except:
            local_ip = '127.0.0.1'
        finally:
            s.close()
        return local_ip
    except Exception:
        # En cas d'échec, essayer avec hostname
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except:
            return "127.0.0.1"  # Fallback en cas d'erreur

# Affiche les instructions pour installer le certificat sur les téléphones
def print_certificate_instructions(cert_path, local_ip, port):
    print("\n" + "="*70)
    print("IMPORTANT - INSTRUCTIONS POUR LES TÉLÉPHONES MOBILES:")
    print("="*70)
    print(f"\nPour utiliser le microphone sur les téléphones, le certificat doit être installé sur")
    print(f"chaque appareil mobile qui se connectera à votre serveur.")
    print("\nSuivez ces étapes:")
    print("\n1. Sur chaque téléphone, ouvrez l'URL suivante dans le navigateur:")
    print(f"   https://{local_ip}:{port}")
    print("\n2. Le navigateur affichera un avertissement de sécurité.")
    print("   Cliquez sur 'Avancé' puis 'Continuer vers le site'")
    print("   (les termes exacts peuvent varier selon le navigateur).")
    print("\n3. Pour une installation permanente du certificat (recommandé):")
    print("   - Sur Android: allez dans Paramètres > Sécurité > Chiffrement")
    print("     et identifiants > Installer un certificat > Certificat CA")
    print("   - Sur iOS: le certificat sera détecté automatiquement dans Réglages")
    print("     après la visite sur le site.")
    print("\nATTENTION: Ce certificat est uniquement pour le développement local.")
    print("="*70 + "\n")
    print(f"Vous pouvez aussi scanner ce QR code pour accéder à l'application: https://{local_ip}:{port}/qrcode")
    print(f"Ou télécharger directement le certificat: https://{local_ip}:{port}/certificate")
    print(f"\nNote: L'application s'arrêtera automatiquement lorsque vous fermerez la page web.")
    print("="*70 + "\n")

# Fonction optimisée pour vérifier la connexion
def check_connection(ip, port, timeout=0.5):  # Optimisation: timeout réduit à 0.5 seconde
    """Vérifie si une connexion à l'adresse IP et au port spécifiés est possible"""
    try:
        socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_obj.settimeout(timeout)
        socket_obj.connect((ip, port))
        socket_obj.close()
        return True
    except:
        return False

# ============================================================
# ROUTES FLASK
# ============================================================

# Nouvelles routes pour les interfaces spécifiques - optimisées pour être plus rapides
@app.route("/phone")
def phone_interface():
    """Interface simplifiée pour le téléphone - uniquement le mode parler"""
    # Mettre à jour le heartbeat
    update_heartbeat()
    
    # Retourner le template avec la langue par défaut (anglais)
    return render_template("phone.html", lang="en")  # Optimisation: moins de paramètres

@app.route("/desktop")
def desktop_interface():
    """Interface simplifiée pour l'ordinateur - uniquement le mode répondre"""
    # Mettre à jour le heartbeat
    update_heartbeat()
    
    # Retourner le template avec la langue par défaut (anglais)
    return render_template("desktop.html", lang="en")  # Optimisation: moins de paramètres

# Route d'accueil optimisée pour une redirection plus rapide
@app.route("/", methods=["GET", "POST"])
def index():
    # Mettre à jour le heartbeat
    update_heartbeat()
    
    # Pour une requête POST, traiter comme avant
    if request.method == "POST":
        lang = "en"  # Langue par défaut (anglais)
        translated_text = ""  # Texte traduit, vide par défaut
        original_text = ""  # Texte original
        
        if "text" in request.form:  # Si un texte est soumis manuellement
            text = request.form["text"].strip()
            lang = request.form["lang"]
            original_text = text
            
            if text:
                translated_text = translate_text(text, lang)
                # Lancer la synthèse vocale dans un thread séparé avec la langue cible
                threading.Thread(target=speak, args=(translated_text, lang)).start()
        
        # Retourner le template standard pour les requêtes POST
        return render_template("index.html", 
                            translated=translated_text, 
                            original=original_text,
                            lang=lang)
    
    # Optimisation: redirection plus directe pour GET
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(device in user_agent for device in ['mobile', 'android', 'iphone', 'ipad'])
    
    # Redirection directe selon le type d'appareil
    if is_mobile:
        return redirect(url_for('phone_interface'))
    else:
        return redirect(url_for('desktop_interface'))

# Route API pour la traduction depuis JavaScript
@app.route('/translate', methods=['POST'])
def translate():
    # Mettre à jour le heartbeat
    update_heartbeat()
    
    global last_translation
    data = request.json
    text = data.get('text', '')
    lang = data.get('lang', 'en')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    # Annuler toute synthèse vocale en cours
    with speech_lock:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    
    translated = translate_text(text, lang)
    
    # Stocker la dernière traduction
    last_translation = {
        'original': text,
        'translated': translated,
        'language': lang
    }
    
    # Lancer la synthèse vocale dans un thread séparé avec la langue cible
    threading.Thread(target=speak, args=(translated, lang)).start()
    
    return jsonify(last_translation)

# Route API pour la traduction inverse (langue étrangère vers français)
@app.route('/translate-to-french', methods=['POST'])
def translate_to_french_route():
    # Mettre à jour le heartbeat
    update_heartbeat()
    
    global last_translation
    data = request.json
    text = data.get('text', '')
    source_lang = data.get('source_lang', 'en')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    translated = translate_to_french(text, source_lang)
    
    # Créer un objet réponse similaire à celui de la traduction standard
    response = {
        'original': text,
        'translated': translated,
        'language': 'fr',  # La langue cible est toujours le français
        'source_language': source_lang  # Ajouter la langue source
    }
    
    # Mettre à jour la dernière traduction
    last_translation = response
    
    # Lancer la synthèse vocale en français seulement si elle n'est pas désactivée
    if not data.get('disable_speech', False):
        threading.Thread(target=speak, args=(translated, 'fr')).start()
    
    return jsonify(response)

# Nouvelle route pour mettre à jour directement la dernière traduction - CORRIGÉE
@app.route('/update-last-translation', methods=['POST'])
def update_last_translation():
    """Route pour mettre à jour explicitement la dernière traduction affichée sur téléphone"""
    # Mettre à jour le heartbeat
    update_heartbeat()
    
    global last_translation
    data = request.json
    
    # Vérifier que toutes les données nécessaires sont présentes
    if 'original' not in data or 'translated' not in data:
        return jsonify({'error': 'Missing data'}), 400
    
    # Ajouter des logs explicites pour le débogage
    print(f"Mise à jour dernière traduction: {data}")
    
    # S'assurer que les clés sont correctes et cohérentes
    last_translation = {
        'original': data.get('original', ''),
        'translated': data.get('translated', ''),
        'language': data.get('language', 'fr'),
        'source_language': data.get('source_language', 'auto')
    }
    
    # Ajout d'une vérification supplémentaire pour confirmer la mise à jour
    print(f"Nouvelle dernière traduction: {last_translation}")
    
    # Retourner une confirmation avec les données mises à jour
    return jsonify({
        'status': 'success', 
        'message': 'Translation updated successfully',
        'data': last_translation
    })

# Nouvelle route pour vérifier les mises à jour (pour le polling) - CORRIGÉE
@app.route('/check-updates', methods=['GET'])
def check_updates():
    # Mettre à jour le heartbeat
    update_heartbeat()
    
    global last_translation
    
    # Ajouter un log pour suivre les accès
    print(f"check-updates appelé: retourne {last_translation}")
    
    return jsonify(last_translation)

@app.route('/set-preferred-language', methods=['POST'])
def set_preferred_language():
    """Route pour définir la langue préférée à utiliser avec MyMemory quand 'auto' est détecté"""
    # Mettre à jour le heartbeat
    update_heartbeat()
    
    data = request.json
    lang = data.get('lang', 'en')
    
    # Ne pas définir 'auto' comme langue préférée
    if lang == 'auto':
        lang = 'en'  # Utiliser anglais par défaut dans ce cas
    
    # Définir la langue préférée dans le gestionnaire de traduction
    translation_manager.set_preferred_language(lang)
    
    return jsonify({
        'status': 'success',
        'message': f'Langue préférée définie sur: {lang}'
    })

# Nouvelle route pour le heartbeat
@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    update_heartbeat()
    return jsonify({'status': 'ok'})

# Nouvelle route pour gérer la fermeture explicite du navigateur
@app.route('/close', methods=['POST'])
def close_notification():
    """Route qui reçoit une notification lorsque le navigateur se ferme"""
    print("\nNotification de fermeture du navigateur reçue. Arrêt de l'application...")
    
    # Programmer l'arrêt immédiat avec un court délai
    threading.Thread(target=lambda: (time.sleep(0.5), os._exit(0))).start()  # Optimisation: délai réduit
    
    return jsonify({'status': 'shutting_down'})

# Route pour afficher le QR code
@app.route('/qrcode')
def display_qrcode():
    """Affiche un QR code pour se connecter facilement à l'application"""
    # Mettre à jour le heartbeat
    update_heartbeat()
    
    # Utiliser l'URL du tunnel si disponible, sinon l'URL locale
    if ngrok_mode and ngrok_tunnel:
        url = ngrok_tunnel.public_url.replace('http://', 'https://')
    else:
        url = f"https://{get_local_ip()}:{port}"
    
    buffer = generate_qr_code(url)
    return send_file(buffer, mimetype='image/png')

# Nouvelle route pour télécharger le certificat
@app.route('/certificate')
def download_certificate():
    """Permet aux utilisateurs de télécharger le certificat"""
    # Mettre à jour le heartbeat
    update_heartbeat()
    
    cert_path = os.path.join('certs', 'cert.pem')
    return send_file(cert_path, as_attachment=True, 
                    download_name='TradLive_Certificate.crt',
                    mimetype='application/x-x509-ca-cert')

# Nouvelle route pour récupérer l'URL du tunnel
@app.route('/tunnel-url')
def get_tunnel_url():
    """Retourne l'URL du tunnel si disponible"""
    # Mettre à jour le heartbeat
    update_heartbeat()
    
    if ngrok_mode and ngrok_tunnel:
        url = ngrok_tunnel.public_url.replace('http://', 'https://')
        remaining = get_ngrok_time_left()
        return jsonify({'url': url, 'mode': 'ngrok', 'remaining': remaining})
    else:
        return jsonify({'url': f"https://{get_local_ip()}:{port}", 'mode': 'direct', 'remaining': None})

# Nouvelle route pour obtenir les informations de statut du serveur
@app.route('/server-status')
def get_server_status():
    """Retourne les informations sur le statut du serveur"""
    # Mettre à jour le heartbeat
    update_heartbeat()
    
    status = {
        'mode': 'ngrok' if ngrok_mode else 'direct',
        'port': port,
        'local_ip': get_local_ip(),
    }
    
    if ngrok_mode and ngrok_tunnel:
        status['public_url'] = ngrok_tunnel.public_url.replace('http://', 'https://')
        status['remaining'] = get_ngrok_time_left()
    
    return jsonify(status)

@app.route('/rooms')
def rooms_page():
    """Page principale pour créer ou rejoindre une salle"""
    return render_template('rooms.html')

@app.route('/api/create-room', methods=['POST'])
def create_room():
    """Crée une nouvelle salle"""
    update_heartbeat()
    
    try:
        data = request.json
        host_nickname = data.get('nickname', '').strip()
        host_language = data.get('language', 'fr')
        room_name = data.get('room_name', '').strip()
        password = data.get('password', '').strip() or None
        
        # Validations
        if not host_nickname:
            return jsonify({'success': False, 'error': 'Pseudo requis'}), 400
        
        if not room_name:
            return jsonify({'success': False, 'error': 'Nom de salle requis'}), 400
        
        # Créer la salle
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
        room_id = data.get('room_id', '').strip()
        nickname = data.get('nickname', '').strip()
        language = data.get('language', 'fr')
        password = data.get('password', '').strip() or None
        
        # Validations
        if not room_id:
            return jsonify({'success': False, 'error': 'Code de salle requis'}), 400
        
        if not nickname:
            return jsonify({'success': False, 'error': 'Pseudo requis'}), 400
        
        # Rejoindre la salle
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
    
    # Vérifier que la salle existe
    room = room_manager.get_room(room_id)
    if not room:
        return redirect(url_for('rooms_page'))
    
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
        
        # Validations
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID requis'}), 400
        
        if not text:
            return jsonify({'success': False, 'error': 'Texte requis'}), 400
        
        # Vérifier que l'utilisateur est dans la salle
        room = room_manager.get_room(room_id)
        if not room or not room.get_user(user_id):
            return jsonify({'success': False, 'error': 'Utilisateur non autorisé'}), 403
        
        # Mettre à jour l'activité de l'utilisateur
        room_manager.update_user_activity(room_id, user_id)
        
        # Diffuser la traduction
        success = room_manager.broadcast_translation(room_id, text, source_language)
        
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
        
        # Mettre à jour l'activité de l'utilisateur
        room_manager.update_user_activity(room_id, user_id)
        
        # Récupérer la langue de l'utilisateur
        user = room.get_user(user_id)
        user_language = user.language
        
        # Retourner la traduction dans la langue de l'utilisateur
        last_translation = room.last_translation
        translated_text = last_translation['translated'].get(user_language, '')
        
        return jsonify({
            'success': True,
            'original': last_translation['original'],
            'translated': translated_text,
            'timestamp': last_translation['timestamp'].isoformat(),
            'user_language': user_language
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/stats')
def admin_stats():
    """Statistiques pour l'admin (optionnel)"""
    update_heartbeat()
    
    # Nettoyer les salles vides
    room_manager.cleanup_rooms()
    
    return jsonify(room_manager.get_stats())

# Modifier la route principale pour rediriger vers la page des salles
@app.route("/")
def index():
    """Route principale - redirige vers la sélection de salle"""
    update_heartbeat()
    return redirect(url_for('rooms_page'))
# ============================================================
# FONCTIONS DE GESTION DU HEARTBEAT
# ============================================================

def update_heartbeat():
    """Met à jour le timestamp du dernier heartbeat"""
    global last_heartbeat
    
    with heartbeat_lock:
        previous = last_heartbeat
        last_heartbeat = datetime.datetime.now()
        
        # Ajouter ce log uniquement pour les longues périodes d'inactivité
        if (last_heartbeat - previous).total_seconds() > 10:
            print(f"Heartbeat reçu après {(last_heartbeat - previous).total_seconds():.1f} secondes d'inactivité")

# ============================================================
# POINT D'ENTRÉE PRINCIPAL (OPTIMISÉ)
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
