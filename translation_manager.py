import os
import json
import threading
import time
import re
import queue
from datetime import datetime
from deep_translator import GoogleTranslator, MyMemoryTranslator, DeeplTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed

# 🔄 SYSTÈME DE FILE D'ATTENTE POUR TRADUCTIONS SÉQUENTIELLES
class TranslationQueue:
    def __init__(self, translation_manager):
        self.translation_manager = translation_manager
        self.queue = queue.Queue()
        self.is_processing = False
        self.processing_thread = None
        self.current_translation = None
        self.translation_counter = 0
        
        # Callbacks pour les résultats
        self.on_translation_complete = None
        self.on_translation_start = None
        
        print("🔄 Système de file d'attente initialisé")
    
    def add_translation(self, text, source_lang, target_lang='fr', forced_mode=None, priority='normal'):
        """Ajoute une traduction à la file d'attente"""
        if not text or text.strip() == "":
            return None
        
        self.translation_counter += 1
        translation_task = {
            'id': self.translation_counter,
            'text': text,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'forced_mode': forced_mode,
            'priority': priority,
            'timestamp': time.time(),
            'status': 'queued'
        }
        
        # Ajouter à la queue
        self.queue.put(translation_task)
        
        print(f"📝 Traduction #{translation_task['id']} ajoutée à la file: '{text[:30]}...'")
        print(f"📊 File d'attente: {self.queue.qsize()} traduction(s) en attente")
        
        # Démarrer le traitement si pas déjà en cours
        if not self.is_processing:
            self.start_processing()
        
        return translation_task['id']
    
    def start_processing(self):
        """Démarre le thread de traitement de la file"""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processing_thread.start()
        print("🚀 Traitement de la file d'attente démarré")
    
    def _process_queue(self):
        """Traite les traductions une par une, dans l'ordre"""
        while self.is_processing:
            try:
                # Récupérer la prochaine traduction (bloquant avec timeout)
                translation_task = self.queue.get(timeout=1.0)
                
                print(f"🔄 Début traitement #{translation_task['id']}: '{translation_task['text'][:30]}...'")
                
                # Marquer comme en cours
                translation_task['status'] = 'processing'
                translation_task['start_time'] = time.time()
                self.current_translation = translation_task
                
                # Callback de début (optionnel)
                if self.on_translation_start:
                    self.on_translation_start(translation_task)
                
                # TRADUCTION EFFECTIVE (sans interruption possible)
                try:
                    result = self.translation_manager.translate(
                        translation_task['text'],
                        translation_task['source_lang'],
                        translation_task['target_lang'],
                        translation_task['forced_mode']
                    )
                    
                    # Marquer comme terminé
                    translation_task['status'] = 'completed'
                    translation_task['result'] = result
                    translation_task['end_time'] = time.time()
                    translation_task['duration'] = translation_task['end_time'] - translation_task['start_time']
                    
                    print(f"✅ Traduction #{translation_task['id']} terminée en {translation_task['duration']:.2f}s")
                    print(f"📤 Résultat: '{result[:50]}...'")
                    
                    # Callback de fin
                    if self.on_translation_complete:
                        self.on_translation_complete(translation_task)
                
                except Exception as e:
                    # Erreur de traduction
                    translation_task['status'] = 'error'
                    translation_task['error'] = str(e)
                    translation_task['end_time'] = time.time()
                    
                    print(f"❌ Erreur traduction #{translation_task['id']}: {e}")
                    
                    if self.on_translation_complete:
                        self.on_translation_complete(translation_task)
                
                # Marquer la tâche comme terminée dans la queue
                self.queue.task_done()
                self.current_translation = None
                
                # Petite pause entre les traductions pour fluidité
                time.sleep(0.1)
                
            except queue.Empty:
                # Pas de nouvelles traductions, continuer à attendre
                continue
            except Exception as e:
                print(f"❌ Erreur dans le traitement de la file: {e}")
                continue
        
        print("🛑 Traitement de la file d'attente arrêté")
    
    def stop_processing(self):
        """Arrête le traitement (après avoir terminé la traduction en cours)"""
        print("🛑 Arrêt demandé du traitement de la file...")
        self.is_processing = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=10)  # Attendre max 10s
        
        print("✅ Traitement de la file arrêté")
    
    def clear_queue(self):
        """Vide la file d'attente (garde la traduction en cours)"""
        cleared_count = 0
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                cleared_count += 1
            except queue.Empty:
                break
        
        print(f"🗑️ {cleared_count} traduction(s) supprimée(s) de la file")
        return cleared_count
    
    def get_queue_status(self):
        """Retourne l'état de la file d'attente"""
        return {
            'is_processing': self.is_processing,
            'queue_size': self.queue.qsize(),
            'current_translation': self.current_translation,
            'total_processed': self.translation_counter
        }
    
    def set_callbacks(self, on_start=None, on_complete=None):
        """Configure les callbacks pour les événements"""
        if on_start:
            self.on_translation_start = on_start
        if on_complete:
            self.on_translation_complete = on_complete

# 🧠 DÉTECTEUR DE DOMAINE (identique à avant)
class DomainDetector:
    def __init__(self):
        # 🚨 Domaines CRITIQUES (Mode Précision Obligatoire)
        self.critical_domains = {
            'medical': {
                'keywords': {
                    'fr': ['patient', 'diagnostic', 'symptôme', 'maladie', 'médicament', 'traitement', 'douleur', 'fièvre', 'consultation', 'ordonnance', 'allergie', 'infection', 'chirurgie', 'urgence', 'hôpital', 'mal'],
                    'en': ['patient', 'diagnosis', 'symptom', 'disease', 'medication', 'treatment', 'pain', 'fever', 'consultation', 'prescription', 'allergy', 'infection', 'surgery', 'emergency', 'hospital', 'hurt', 'ache']
                },
                'mode': 'precision',
                'confidence_threshold': 0.25
            },
            'legal': {
                'keywords': {
                    'fr': ['contrat', 'clause', 'juridique', 'tribunal', 'avocat', 'procédure', 'droit', 'loi', 'responsabilité', 'litige'],
                    'en': ['contract', 'clause', 'legal', 'court', 'lawyer', 'procedure', 'law', 'statute', 'liability', 'litigation']
                },
                'mode': 'precision',
                'confidence_threshold': 0.25
            },
            'financial': {
                'keywords': {
                    'fr': ['investissement', 'crédit', 'prêt', 'assurance', 'hypothèque', 'placement', 'épargne', 'impôt', 'banque', 'compte'],
                    'en': ['investment', 'credit', 'loan', 'insurance', 'mortgage', 'investment', 'savings', 'tax', 'bank', 'account']
                },
                'mode': 'precision',
                'confidence_threshold': 0.3
            }
        }
        
        # 🟢 Domaines SÛRS (Mode Pipeline OK)
        self.safe_domains = {
            'digital_training': {
                'keywords': {
                    'fr': ['cliquez', 'menu', 'ordinateur', 'souris', 'clavier', 'internet', 'email', 'mot de passe', 'fichier', 'dossier', 'télécharger', 'sauvegarder', 'copier', 'coller', 'wifi'],
                    'en': ['click', 'menu', 'computer', 'mouse', 'keyboard', 'internet', 'email', 'password', 'file', 'folder', 'download', 'save', 'copy', 'paste', 'wifi']
                },
                'mode': 'pipeline',
                'confidence_threshold': 0.4
            }
        }
        
        self.current_domain = None
        self.current_mode = 'precision'
        self.forced_mode = None
    
    def detect_domain(self, text, source_lang='auto', forced_mode=None):
        """Détecte le domaine (version simplifiée)"""
        if forced_mode:
            return {
                'domain': 'user_forced',
                'mode': forced_mode,
                'confidence': 1.0,
                'source': 'user_override',
                'safe_for_pipeline': forced_mode == 'pipeline'
            }
        
        text_lower = text.lower()
        
        # Vérifier domaines critiques
        for domain_name, domain_info in self.critical_domains.items():
            for lang, keywords in domain_info['keywords'].items():
                for keyword in keywords:
                    if keyword in text_lower:
                        return {
                            'domain': domain_name,
                            'mode': 'precision',
                            'confidence': 1.0,
                            'source': 'critical_detection',
                            'safe_for_pipeline': False,
                            'warning': f"⚠️ Domaine {domain_name} détecté - Mode précision activé"
                        }
        
        # Vérifier domaines sûrs
        for domain_name, domain_info in self.safe_domains.items():
            score = 0
            for lang, keywords in domain_info['keywords'].items():
                for keyword in keywords:
                    if keyword in text_lower:
                        score += 1
            
            if score >= 2:
                return {
                    'domain': domain_name,
                    'mode': 'pipeline',
                    'confidence': score,
                    'source': 'safe_detection',
                    'safe_for_pipeline': True,
                    'info': f"🚀 {domain_name} détecté - Mode rapide activé"
                }
        
        # Par défaut
        return {
            'domain': 'general',
            'mode': 'precision',
            'confidence': 0.0,
            'source': 'default_safe',
            'safe_for_pipeline': False
        }

# 🚀 TRANSLATION MANAGER AVEC FILE D'ATTENTE
class TranslationManager:
    def __init__(self):
        self.domain_detector = DomainDetector()
        
        # Services et limites (identiques)
        self.limits = {
            'google': 500000,
            'mymemory': 500000,
            'deepl': 500000
        }
        
        # Cache intelligent (simplifié pour focus sur file d'attente)
        self.translation_cache = {}
        self.smart_cache = {}
        
        self.preferred_lang = 'en'
        self.translation_timeout = 8
        
        # Mappings (identiques)
        self.mymemory_lang_map = {
            'zh-CN': 'zh-CN', 'en': 'en-GB', 'es': 'es-ES', 'de': 'de-DE',
            'it': 'it-IT', 'pt': 'pt-PT', 'ru': 'ru-RU', 'ja': 'ja-JP',
            'ar': 'ar-SA', 'uk': 'uk-UA', 'fa': 'fa-IR', 'hi': 'hi-IN',
            'bn': 'bn-IN', 'te': 'te-IN', 'mr': 'mr-IN', 'fr': 'fr-FR'
        }
        
        self.deepl_lang_map = {
            'zh-CN': 'ZH', 'en': 'EN-US', 'es': 'ES', 'de': 'DE',
            'it': 'IT', 'pt': 'PT-PT', 'ru': 'RU', 'ja': 'JA', 'fr': 'FR'
        }
        
        # 🆕 NOUVEAU : File d'attente pour traductions séquentielles
        self.translation_queue = TranslationQueue(self)
        
        # Initialiser les systèmes
        self.init_counters()
        self.init_basic_cache()
        
        print("🚀 TranslationManager avec file d'attente initialisé")
    
    # 🆕 FONCTION PRINCIPALE : Ajouter à la file au lieu de traduire directement
    def translate_async(self, text, source_lang, target_lang='fr', forced_mode=None, priority='normal'):
        """Ajoute une traduction à la file d'attente (non-bloquant)"""
        return self.translation_queue.add_translation(text, source_lang, target_lang, forced_mode, priority)
    
    # FONCTION DE TRADUCTION DIRECTE (pour la file d'attente)
    def translate(self, text, source_lang, target_lang='fr', forced_mode=None):
        """Traduit directement (utilisé par la file d'attente)"""
        if not text or text.strip() == "":
            return ""
        
        # Détection du domaine
        domain_analysis = self.domain_detector.detect_domain(text, source_lang, forced_mode)
        
        # Vérifier cache
        cached_translation = self.check_cache(text, source_lang, target_lang)
        if cached_translation:
            print(f"⚡ Cache hit pour: '{text[:30]}...'")
            return cached_translation
        
        # Services disponibles
        available_services = self.get_available_services()
        
        if 'deepl' in available_services and not self.can_use_deepl(source_lang, target_lang):
            available_services.remove('deepl')
        
        print(f"🔄 Traduction avec {len(available_services)} services (Mode: {domain_analysis['mode']})")
        
        # Traduction parallèle
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=len(available_services)) as executor:
            future_to_service = {
                executor.submit(self.translate_with_service, text, source_lang, target_lang, service): service
                for service in available_services
            }
            
            for future in as_completed(future_to_service, timeout=self.translation_timeout):
                service = future_to_service[future]
                try:
                    translation, used_service = future.result()
                    elapsed = time.time() - start_time
                    
                    print(f"✅ Résultat de {used_service} en {elapsed:.2f}s")
                    
                    # Post-traitement et cache
                    translation = self.post_process_translation(translation, target_lang)
                    self.add_to_cache(text, source_lang, target_lang, translation)
                    
                    return translation
                    
                except Exception as e:
                    print(f"❌ Échec {service}: {str(e)}")
                    continue
        
        return f"Erreur de traduction: tous les services ont échoué"
    
    # 🆕 FONCTIONS DE CONTRÔLE DE LA FILE
    def get_queue_status(self):
        """Retourne l'état de la file d'attente"""
        return self.translation_queue.get_queue_status()
    
    def clear_queue(self):
        """Vide la file d'attente"""
        return self.translation_queue.clear_queue()
    
    def stop_queue(self):
        """Arrête le traitement de la file"""
        self.translation_queue.stop_processing()
    
    def set_translation_callbacks(self, on_start=None, on_complete=None):
        """Configure les callbacks pour les événements de traduction"""
        self.translation_queue.set_callbacks(on_start, on_complete)
    
    # TOUTES LES AUTRES FONCTIONS (identiques à avant)
    def init_counters(self):
        now = datetime.now()
        current_month = f"{now.year}-{now.month}"
        
        counter_file = "translation_counters.json"
        self.counters = {'google': 0, 'mymemory': 0, 'deepl': 0}
        self.month = current_month
        
        if os.path.exists(counter_file):
            try:
                with open(counter_file, 'r') as f:
                    data = json.load(f)
                    
                if data.get('month') != current_month:
                    print(f"Nouveau mois détecté: réinitialisation des compteurs")
                else:
                    saved_counters = data.get('counters', {})
                    self.counters.update(saved_counters)
                    if 'deepl' not in self.counters:
                        self.counters['deepl'] = 0
                    self.month = data.get('month')
            except Exception as e:
                print(f"Erreur lors du chargement des compteurs: {e}")
        
        self.save_counters()
    
    def save_counters(self):
        try:
            with open("translation_counters.json", 'w') as f:
                json.dump({
                    'month': self.month,
                    'counters': self.counters
                }, f)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des compteurs: {e}")
    
    def update_counter(self, service, char_count):
        self.counters[service] += char_count
        self.save_counters()
        
        usage_percent = (self.counters[service] / self.limits.get(service, 1000000)) * 100
        print(f"Service {service}: {self.counters[service]}/{self.limits[service]} caractères ({usage_percent:.2f}%)")
    
    def get_available_services(self):
        available_services = []
        for service, limit in self.limits.items():
            if self.counters.get(service, 0) < limit:
                available_services.append(service)
        
        if not available_services:
            print("ATTENTION: Tous les services ont atteint leur limite!")
            return ['google']
        
        return available_services
    
    def init_basic_cache(self):
        """Cache basique pour cette version"""
        phrases_communes = {
            'bonjour|auto|en': 'hello',
            'merci|auto|en': 'thank you',
            'au revoir|auto|en': 'goodbye',
            'cliquez|auto|en': 'click',
            'menu|auto|en': 'menu',
            'ordinateur|auto|en': 'computer'
        }
        
        self.smart_cache.update(phrases_communes)
        print(f"💾 Cache basique initialisé: {len(self.smart_cache)} entrées")
    
    def check_cache(self, text, source_lang, target_lang):
        cache_key = f"{text.lower()}|{source_lang}|{target_lang}"
        return self.smart_cache.get(cache_key)
    
    def add_to_cache(self, text, source_lang, target_lang, translation):
        cache_key = f"{text.lower()}|{source_lang}|{target_lang}"
        self.smart_cache[cache_key] = translation
    
    def post_process_translation(self, translation, target_lang):
        # Post-traitement basique
        return translation
    
    def can_use_deepl(self, source_lang, target_lang):
        supported_langs = ['fr', 'en', 'de', 'es', 'it', 'pt', 'ru', 'ja', 'zh-CN']
        return (source_lang in supported_langs or source_lang == 'auto') and target_lang in supported_langs
    
    def translate_with_service(self, text, source_lang, target_lang, service):
        try:
            if service == 'google':
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                translation = translator.translate(text)
                self.update_counter('google', len(text))
                return translation, 'google'
                
            elif service == 'mymemory':
                source = self.map_lang_code(source_lang, True)
                target = self.map_lang_code(target_lang, True)
                
                translator = MyMemoryTranslator(source=source, target=target)
                translation = translator.translate(text)
                self.update_counter('mymemory', len(text))
                return translation, 'mymemory'
                
            elif service == 'deepl':
                if not self.can_use_deepl(source_lang, target_lang):
                    raise Exception("Langues non supportées par DeepL")
                
                source_deepl = self.deepl_lang_map.get(source_lang, source_lang.upper()) if source_lang != 'auto' else 'auto'
                target_deepl = self.deepl_lang_map.get(target_lang, target_lang.upper())
                
                translator = DeeplTranslator(api_key=None, source=source_deepl, target=target_deepl, use_free_api=True)
                translation = translator.translate(text)
                self.update_counter('deepl', len(text))
                return translation, 'deepl'
                
        except Exception as e:
            print(f"Erreur service {service}: {str(e)}")
            raise e
    
    def map_lang_code(self, lang_code, for_mymemory=False):
        if not for_mymemory:
            return lang_code
            
        if lang_code == 'auto':
            preferred = self.preferred_lang
            if preferred in self.mymemory_lang_map:
                mapped_code = self.mymemory_lang_map[preferred]
            else:
                mapped_code = f"{preferred}-{preferred.upper()}" if len(preferred) == 2 else preferred
            
            return mapped_code
        
        if lang_code in self.mymemory_lang_map:
            return self.mymemory_lang_map[lang_code]
        
        if len(lang_code) == 2:
            return f"{lang_code}-{lang_code.upper()}"
        
        return lang_code

# Créer une instance globale
translation_manager = TranslationManager()
