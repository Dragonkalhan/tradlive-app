import os
import json
from datetime import datetime
from deep_translator import GoogleTranslator, MyMemoryTranslator

class TranslationManager:
    def __init__(self):
        # Limites mensuelles des caractères (approximatives)
        self.limits = {
            'google': 500000,    # 500K caractères/mois
            'mymemory': 500000   # 500K caractères/mois
        }
        
        # Cache des traductions récentes (pour accélérer)
        self.translation_cache = {}
        self.max_cache_size = 100
        
        # Langue préférée à utiliser quand 'auto' est spécifié avec MyMemory
        self.preferred_lang = 'en'  # Anglais par défaut
        
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
        
        # Valeurs par défaut
        self.counters = {'google': 0, 'mymemory': 0}
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
                    self.counters = data.get('counters', self.counters)
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
    
    def get_best_service(self):
        """Détermine le meilleur service à utiliser"""
        # Vérifier quels services sont disponibles (n'ont pas atteint leur limite)
        available_services = []
        for service, limit in self.limits.items():
            if self.counters.get(service, 0) < limit:
                available_services.append(service)
        
        if not available_services:
            print("ATTENTION: Tous les services ont atteint leur limite!")
            return 'google'  # Par défaut
        
        # Choisir celui qui a le taux d'utilisation le plus bas
        best_service = min(
            available_services, 
            key=lambda s: self.counters.get(s, 0) / self.limits.get(s)
        )
        
        return best_service
    
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
    
    def translate(self, text, source_lang, target_lang='fr'):
        """Traduit un texte en utilisant le meilleur service"""
        if not text or text.strip() == "":
            return ""
        
        # Si source_lang n'est pas 'auto', mettre à jour la langue préférée
        if source_lang != 'auto':
            self.set_preferred_language(source_lang)
        
        # 1. Vérifier d'abord dans le cache (très rapide)
        cached_translation = self.check_cache(text, source_lang, target_lang)
        if cached_translation:
            print("Traduction trouvée dans le cache!")
            return cached_translation
        
        # 2. Obtenir le meilleur service
        service = self.get_best_service()
        print(f"Traduction avec le service: {service}")
        
        try:
            if service == 'google':
                # Utiliser Google Translate (supporte 'auto')
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                translation = translator.translate(text)
                self.update_counter('google', len(text))
            else:
                # Utiliser MyMemory avec les codes de langue appropriés
                source = self.map_lang_code(source_lang, True)
                target = self.map_lang_code(target_lang, True) 
                
                print(f"MyMemory utilise: source={source}, target={target}")
                translator = MyMemoryTranslator(source=source, target=target)
                translation = translator.translate(text)
                self.update_counter('mymemory', len(text))
            
            # 3. Appliquer les corrections post-traduction
            translation = self.post_process_translation(translation, target_lang)
            
            # 4. Ajouter au cache pour les futures utilisations
            self.add_to_cache(text, source_lang, target_lang, translation)
            
            return translation
                
        except Exception as e:
            print(f"Erreur avec {service}: {str(e)}")
            
            # Solution de secours: essayer l'autre service
            try:
                if service == 'google':
                    # En cas d'erreur avec Google, utiliser MyMemory
                    source = self.map_lang_code(source_lang, True)
                    target = self.map_lang_code(target_lang, True)
                    
                    print(f"MyMemory (secours) utilise: source={source}, target={target}")
                    translator = MyMemoryTranslator(source=source, target=target)
                else:
                    # En cas d'erreur avec MyMemory, utiliser Google
                    translator = GoogleTranslator(source=source_lang, target=target_lang)
                    
                translation = translator.translate(text)
                translation = self.post_process_translation(translation, target_lang)
                self.add_to_cache(text, source_lang, target_lang, translation)
                return translation
            except Exception as fallback_error:
                print(f"Erreur de secours: {str(fallback_error)}")
                return f"Erreur de traduction: {str(e)}"

# Créer une instance globale
translation_manager = TranslationManager()
