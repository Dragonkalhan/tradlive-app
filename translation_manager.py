import os
import json
import threading
import time
from datetime import datetime
from deep_translator import GoogleTranslator, MyMemoryTranslator, DeeplTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed

class TranslationManager:
    def __init__(self):
        # 🆕 NOUVEAU : Limites mensuelles avec DeepL inclus
        self.limits = {
            'google': 500000,    # 500K caractères/mois
            'mymemory': 500000,  # 500K caractères/mois
            'deepl': 500000      # 500K caractères/mois - NOUVEAU
        }
        
        # Cache des traductions récentes (pour accélérer)
        self.translation_cache = {}
        self.max_cache_size = 100
        
        # Langue préférée à utiliser quand 'auto' est spécifié avec MyMemory
        self.preferred_lang = 'en'  # Anglais par défaut
        
        # Timeout pour les traductions parallèles
        self.translation_timeout = 8  # 8 secondes max par service
        
        # Dictionnaire de mappage pour MyMemory (codes spécifiques pour toutes les langues de l'application)
        self.mymemory_lang_map = {
            # Langues qui ne suivent pas le modèle standard XX-XX ou qui nécessitent une variante spécifique
            'zh-CN': 'zh-CN',  # Chinois simplifié - format spécial
            'en': 'en-GB',     # Anglais - préférence pour britannique 
            'es': 'es-ES',     # Espagnol - variante européenne
            'de': 'de-DE',     # Allemand - Allemagne
            'it': 'it-IT',     # Italien - Italie
            'pt': 'pt-PT',     # Portugais européen
            'ru': 'ru-RU',     # Russe
            'ja': 'ja-JP',     # Japonais
            'ar': 'ar-SA',     # Arabe - Arabie Saoudite
            'uk': 'uk-UA',     # Ukrainien
            'fa': 'fa-IR',     # Persan/Farsi - Iran
            'hi': 'hi-IN',     # Hindi - Inde
            'bn': 'bn-IN',     # Bengali - Inde
            'te': 'te-IN',     # Télougou - Inde
            'mr': 'mr-IN',     # Marathi - Inde
            'fr': 'fr-FR'      # Français - France
        }
        
        # 🆕 NOUVEAU : Mapping pour DeepL (codes plus simples)
        self.deepl_lang_map = {
            'zh-CN': 'ZH',     # Chinois
            'en': 'EN-US',     # Anglais américain
            'es': 'ES',        # Espagnol
            'de': 'DE',        # Allemand
            'it': 'IT',        # Italien
            'pt': 'PT-PT',     # Portugais
            'ru': 'RU',        # Russe
            'ja': 'JA',        # Japonais
            'fr': 'FR'         # Français
            # Note: DeepL ne supporte pas toutes les langues
        }
        
        # Initialiser les compteurs
        self.init_counters()
    
    def set_preferred_language(self, lang):
        """Définit la langue préférée à utiliser lorsque 'auto' est spécifié avec MyMemory"""
        if lang != 'auto':
            self.preferred_lang = lang
        print(f"Langue préférée définie sur: {self.preferred_lang}")
    
    def init_counters(self):
        """Initialise ou récupère les compteurs d'utilisation"""
        now = datetime.now()
        current_month = f"{now.year}-{now.month}"
        
        # Chemin vers le fichier de compteurs
        counter_file = "translation_counters.json"
        
        # 🆕 NOUVEAU : Valeurs par défaut avec DeepL
        self.counters = {'google': 0, 'mymemory': 0, 'deepl': 0}
        self.month = current_month
        
        # Charger les compteurs existants si disponibles
        if os.path.exists(counter_file):
            try:
                with open(counter_file, 'r') as f:
                    data = json.load(f)
                    
                # Vérifier si nous sommes dans un nouveau mois
                if data.get('month') != current_month:
                    # Nouveau mois: réinitialiser les compteurs
                    print(f"Nouveau mois détecté: réinitialisation des compteurs")
                else:
                    # Même mois: utiliser les compteurs existants
                    saved_counters = data.get('counters', {})
                    # 🆕 S'assurer que DeepL est dans les compteurs
                    self.counters.update(saved_counters)
                    if 'deepl' not in self.counters:
                        self.counters['deepl'] = 0
                    self.month = data.get('month')
            except Exception as e:
                print(f"Erreur lors du chargement des compteurs: {e}")
        
        # Sauvegarder l'état initial
        self.save_counters()
    
    def save_counters(self):
        """Sauvegarde les compteurs dans un fichier"""
        try:
            with open("translation_counters.json", 'w') as f:
                json.dump({
                    'month': self.month,
                    'counters': self.counters
                }, f)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des compteurs: {e}")
    
    def update_counter(self, service, char_count):
        """Met à jour le compteur pour un service donné"""
        self.counters[service] += char_count
        self.save_counters()
        
        # Log pour suivre l'utilisation
        usage_percent = (self.counters[service] / self.limits.get(service, 1000000)) * 100
        print(f"Service {service}: {self.counters[service]}/{self.limits[service]} caractères ({usage_percent:.2f}%)")
    
    def get_available_services(self):
        """Récupère la liste des services disponibles (non limités)"""
        available_services = []
        for service, limit in self.limits.items():
            if self.counters.get(service, 0) < limit:
                available_services.append(service)
        
        if not available_services:
            print("ATTENTION: Tous les services ont atteint leur limite!")
            return ['google']  # Par défaut, au cas où
        
        return available_services
    
    def check_cache(self, text, source_lang, target_lang):
        """Vérifie si une traduction est déjà en cache"""
        cache_key = f"{text.lower()}|{source_lang}|{target_lang}"
        return self.translation_cache.get(cache_key)
    
    def add_to_cache(self, text, source_lang, target_lang, translation):
        """Ajoute une traduction au cache"""
        cache_key = f"{text.lower()}|{source_lang}|{target_lang}"
        
        # Limiter la taille du cache
        if len(self.translation_cache) >= self.max_cache_size:
            # Supprimer une entrée aléatoire
            self.translation_cache.pop(next(iter(self.translation_cache)))
        
        self.translation_cache[cache_key] = translation
    
    def map_lang_code(self, lang_code, for_mymemory=False):
        """Convertit les codes de langue au format approprié pour MyMemory si nécessaire"""
        # Si ce n'est pas pour MyMemory, renvoyer tel quel
        if not for_mymemory:
            return lang_code
            
        # IMPORTANT: MyMemory ne supporte pas 'auto' comme code de langue
        # Si 'auto' est spécifié, utiliser la langue préférée à la place
        if lang_code == 'auto':
            preferred = self.preferred_lang
            # Obtenir le code formaté pour la langue préférée
            if preferred in self.mymemory_lang_map:
                mapped_code = self.mymemory_lang_map[preferred]
            else:
                mapped_code = f"{preferred}-{preferred.upper()}" if len(preferred) == 2 else preferred
            
            print(f"ATTENTION: 'auto' n'est pas supporté par MyMemory, utilisation de '{mapped_code}' à la place")
            return mapped_code
        
        # Pour MyMemory, utiliser le mapping spécifique
        if lang_code in self.mymemory_lang_map:
            return self.mymemory_lang_map[lang_code]
        
        # Si le code n'est pas dans notre mapping, essayer d'ajouter un suffixe de région
        if len(lang_code) == 2:
            # Si simple code à 2 lettres, essayer d'ajouter un suffixe de région standard
            return f"{lang_code}-{lang_code.upper()}"
        
        # Fallback - retourner tel quel
        return lang_code
    
    def post_process_translation(self, translation, target_lang):
        """Applique des corrections post-traduction"""
        corrections = {
            'en': {
                'comment ça va tu': 'how are you',
                'comment vas-tu': 'how are you',
                'le le': 'the',
                'la la': 'the'
            },
            'es': {
                'el el': 'el',
                'la la': 'la',
                'como estas tu': 'cómo estás'
            },
            'de': {
                'wie geht es du': 'wie geht es dir',
                'der der': 'der',
                'die die': 'die'
            }
            # Ajoutez d'autres langues au besoin
        }
        
        # Appliquer les corrections pour la langue cible
        if target_lang in corrections:
            for wrong, correct in corrections[target_lang].items():
                translation = translation.replace(wrong, correct)
        
        return translation
    
    def can_use_deepl(self, source_lang, target_lang):
        """Vérifie si DeepL peut traiter cette paire de langues"""
        # DeepL ne supporte que certaines langues
        supported_langs = ['fr', 'en', 'de', 'es', 'it', 'pt', 'ru', 'ja', 'zh-CN']
        return (source_lang in supported_langs or source_lang == 'auto') and target_lang in supported_langs
    
    # 🆕 FONCTION MODIFIÉE : Traduction avec DeepL inclus
    def translate_with_service(self, text, source_lang, target_lang, service):
        """Traduit avec un service spécifique"""
        try:
            if service == 'google':
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                translation = translator.translate(text)
                self.update_counter('google', len(text))
                return translation, 'google'
                
            elif service == 'mymemory':  # MyMemory
                source = self.map_lang_code(source_lang, True)
                target = self.map_lang_code(target_lang, True)
                
                translator = MyMemoryTranslator(source=source, target=target)
                translation = translator.translate(text)
                self.update_counter('mymemory', len(text))
                return translation, 'mymemory'
                
            elif service == 'deepl':  # 🆕 NOUVEAU : DeepL
                # Vérifier si DeepL supporte ces langues
                if not self.can_use_deepl(source_lang, target_lang):
                    raise Exception("Langues non supportées par DeepL")
                
                # Mapper les codes de langue pour DeepL
                source_deepl = self.deepl_lang_map.get(source_lang, source_lang.upper()) if source_lang != 'auto' else 'auto'
                target_deepl = self.deepl_lang_map.get(target_lang, target_lang.upper())
                
                translator = DeeplTranslator(api_key=None, source=source_deepl, target=target_deepl, use_free_api=True)
                translation = translator.translate(text)
                self.update_counter('deepl', len(text))
                return translation, 'deepl'
                
        except Exception as e:
            print(f"Erreur service {service}: {str(e)}")
            raise e
    
    # FONCTION PRINCIPALE (inchangée, sauf le filtrage DeepL)
    def translate(self, text, source_lang, target_lang='fr'):
        """Traduit un texte en utilisant TOUS les services disponibles EN PARALLÈLE"""
        if not text or text.strip() == "":
            return ""
        
        # Si source_lang n'est pas 'auto', mettre à jour la langue préférée
        if source_lang != 'auto':
            self.set_preferred_language(source_lang)
        
        # 1. Vérifier d'abord dans le cache (très rapide)
        cached_translation = self.check_cache(text, source_lang, target_lang)
        if cached_translation:
            print("⚡ Traduction trouvée dans le cache!")
            return cached_translation
        
        # 2. Obtenir la liste des services disponibles
        available_services = self.get_available_services()
        
        # 🆕 NOUVEAU : Filtrer DeepL si langues non supportées
        if 'deepl' in available_services and not self.can_use_deepl(source_lang, target_lang):
            available_services.remove('deepl')
            print(f"ℹ️ DeepL retiré (langues {source_lang}->{target_lang} non supportées)")
        
        print(f"🚀 Traduction PARALLÈLE avec {len(available_services)} services: {available_services}")
        
        # 3. Lancer TOUS les services en parallèle
        translations = {}
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=len(available_services)) as executor:
            # Lancer toutes les traductions simultanément
            future_to_service = {
                executor.submit(self.translate_with_service, text, source_lang, target_lang, service): service
                for service in available_services
            }
            
            # Récupérer le PREMIER résultat qui arrive
            for future in as_completed(future_to_service, timeout=self.translation_timeout):
                service = future_to_service[future]
                try:
                    translation, used_service = future.result()
                    elapsed = time.time() - start_time
                    
                    print(f"✅ PREMIER résultat reçu de {used_service} en {elapsed:.2f}s")
                    
                    # Post-traitement et cache
                    translation = self.post_process_translation(translation, target_lang)
                    self.add_to_cache(text, source_lang, target_lang, translation)
                    
                    return translation
                    
                except Exception as e:
                    print(f"❌ Échec {service}: {str(e)}")
                    continue
        
        # 4. Si tous les services ont échoué (très rare maintenant)
        return f"Erreur de traduction: tous les services ont échoué"

# Créer une instance globale
translation_manager = TranslationManager()
