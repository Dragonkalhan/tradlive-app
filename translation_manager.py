import os
import json
import threading
import time
import re
from datetime import datetime
from deep_translator import GoogleTranslator, MyMemoryTranslator, DeeplTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed

class TranslationManager:
    def __init__(self):
        # Limites mensuelles avec DeepL inclus (INCHANGÉ)
        self.limits = {
            'google': 500000,    # 500K caractères/mois
            'mymemory': 500000,  # 500K caractères/mois
            'deepl': 500000      # 500K caractères/mois
        }
        
        # 🆕 NOUVEAU : Cache intelligent étendu
        self.translation_cache = {}  # Cache existant conservé
        self.smart_cache = {}        # Cache intelligent pour fragments
        self.phrase_frequency = {}   # Compteur de fréquence des phrases
        self.sector_cache = {}       # Cache spécialisé par secteur
        
        self.max_cache_size = 100
        # 🆕 NOUVEAU : Tailles étendues pour le cache intelligent
        self.max_smart_cache_size = 500  # Plus de place pour les fragments
        self.max_phrase_frequency = 200  # Phrases les plus utilisées
        
        # Langue préférée à utiliser quand 'auto' est spécifié avec MyMemory (INCHANGÉ)
        self.preferred_lang = 'en'
        
        # Timeout pour les traductions parallèles (INCHANGÉ)
        self.translation_timeout = 8
        
        # Dictionnaire de mappage pour MyMemory (INCHANGÉ)
        self.mymemory_lang_map = {
            'zh-CN': 'zh-CN', 'en': 'en-GB', 'es': 'es-ES', 'de': 'de-DE',
            'it': 'it-IT', 'pt': 'pt-PT', 'ru': 'ru-RU', 'ja': 'ja-JP',
            'ar': 'ar-SA', 'uk': 'uk-UA', 'fa': 'fa-IR', 'hi': 'hi-IN',
            'bn': 'bn-IN', 'te': 'te-IN', 'mr': 'mr-IN', 'fr': 'fr-FR'
        }
        
        # Mapping pour DeepL (INCHANGÉ)
        self.deepl_lang_map = {
            'zh-CN': 'ZH', 'en': 'EN-US', 'es': 'ES', 'de': 'DE',
            'it': 'IT', 'pt': 'PT-PT', 'ru': 'RU', 'ja': 'JA', 'fr': 'FR'
        }
        
        # 🆕 NOUVEAU : Dictionnaires pré-remplis par secteur professionnel (8 LANGUES)
        self.professional_phrases = {
            'accueil': {
                'fr': ['bonjour', 'bonsoir', 'puis-je vous aider', 'merci', 'au revoir', 'de rien', 'excusez-moi', 'pardon', 'comment allez-vous', 'très bien merci'],
                'en': ['hello', 'good evening', 'can I help you', 'thank you', 'goodbye', 'you\'re welcome', 'excuse me', 'sorry', 'how are you', 'very well thank you'],
                'es': ['hola', 'buenas tardes', 'puedo ayudarle', 'gracias', 'adiós', 'de nada', 'disculpe', 'perdón', 'cómo está usted', 'muy bien gracias'],
                'de': ['hallo', 'guten abend', 'kann ich ihnen helfen', 'danke', 'auf wiedersehen', 'gern geschehen', 'entschuldigung', 'verzeihung', 'wie geht es ihnen', 'sehr gut danke'],
                'it': ['ciao', 'buonasera', 'posso aiutarla', 'grazie', 'arrivederci', 'prego', 'mi scusi', 'scusi', 'come sta', 'molto bene grazie'],
                'pt': ['olá', 'boa tarde', 'posso ajudá-lo', 'obrigado', 'tchau', 'de nada', 'com licença', 'desculpe', 'como está', 'muito bem obrigado'],
                'zh-CN': ['你好', '晚上好', '我可以帮助您吗', '谢谢', '再见', '不客气', '对不起', '抱歉', '您好吗', '很好谢谢'],
                'ar': ['مرحبا', 'مساء الخير', 'هل يمكنني مساعدتك', 'شكرا', 'وداعا', 'عفوا', 'معذرة', 'آسف', 'كيف حالك', 'بخير شكرا']
            },
            'medical': {
                'fr': ['où avez-vous mal', 'depuis quand', 'prenez-vous des médicaments', 'avez-vous de la fièvre', 'sur une échelle de 1 à 10', 'respirez profondément', 'montrez-moi', 'très bien'],
                'en': ['where does it hurt', 'since when', 'do you take medications', 'do you have fever', 'on a scale of 1 to 10', 'breathe deeply', 'show me', 'very good'],
                'es': ['dónde le duele', 'desde cuándo', 'toma medicamentos', 'tiene fiebre', 'en una escala del 1 al 10', 'respire profundamente', 'muéstreme', 'muy bien'],
                'de': ['wo tut es weh', 'seit wann', 'nehmen sie medikamente', 'haben sie fieber', 'auf einer skala von 1 bis 10', 'tief einatmen', 'zeigen sie mir', 'sehr gut'],
                'it': ['dove fa male', 'da quando', 'prende farmaci', 'ha la febbre', 'su una scala da 1 a 10', 'respirare profondamente', 'mi mostri', 'molto bene'],
                'pt': ['onde dói', 'desde quando', 'toma medicamentos', 'tem febre', 'numa escala de 1 a 10', 'respire fundo', 'mostre-me', 'muito bem'],
                'zh-CN': ['哪里疼', '从什么时候开始', '您服药吗', '您发烧吗', '在1到10的范围内', '深呼吸', '让我看看', '很好'],
                'ar': ['أين يؤلمك', 'منذ متى', 'هل تتناول أدوية', 'هل لديك حمى', 'على مقياس من 1 إلى 10', 'تنفس بعمق', 'أرني', 'جيد جدا']
            },
            'education': {
                'fr': ['ouvrez la page', 'avez-vous des questions', 'très bien', 'pouvez-vous répéter', 'écoutez attentivement', 'regardez ici', 'excellent travail', 'continuez'],
                'en': ['open the page', 'do you have questions', 'very good', 'can you repeat', 'listen carefully', 'look here', 'excellent work', 'continue'],
                'es': ['abran la página', 'tienen preguntas', 'muy bien', 'pueden repetir', 'escuchen atentamente', 'miren aquí', 'excelente trabajo', 'continúen'],
                'de': ['öffnen sie die seite', 'haben sie fragen', 'sehr gut', 'können sie wiederholen', 'hören sie aufmerksam zu', 'schauen sie hier', 'ausgezeichnete arbeit', 'weiter'],
                'it': ['aprite la pagina', 'avete domande', 'molto bene', 'potete ripetere', 'ascoltate attentamente', 'guardate qui', 'ottimo lavoro', 'continuate'],
                'pt': ['abram a página', 'têm perguntas', 'muito bem', 'podem repetir', 'escutem atentamente', 'olhem aqui', 'excelente trabalho', 'continuem'],
                'zh-CN': ['打开页面', '你们有问题吗', '很好', '你们能重复吗', '仔细听', '看这里', '优秀的工作', '继续'],
                'ar': ['افتحوا الصفحة', 'هل لديكم أسئلة', 'جيد جدا', 'هل يمكنكم التكرار', 'استمعوا بانتباه', 'انظروا هنا', 'عمل ممتاز', 'تابعوا']
            },
            'numerique': {
                'fr': ['cliquez ici', 'ouvrez ce menu', 'tapez votre mot de passe', 'avez-vous compris', 'essayez maintenant', 'parfait', 'recommencez', 'sauvegardez'],
                'en': ['click here', 'open this menu', 'type your password', 'do you understand', 'try now', 'perfect', 'try again', 'save'],
                'es': ['hagan clic aquí', 'abran este menú', 'escriban su contraseña', 'han entendido', 'prueben ahora', 'perfecto', 'inténtenlo de nuevo', 'guarden'],
                'de': ['klicken sie hier', 'öffnen sie dieses menü', 'geben sie ihr passwort ein', 'haben sie verstanden', 'versuchen sie es jetzt', 'perfekt', 'versuchen sie es nochmal', 'speichern'],
                'it': ['cliccate qui', 'aprite questo menu', 'digitate la vostra password', 'avete capito', 'provate ora', 'perfetto', 'riprovate', 'salvate'],
                'pt': ['cliquem aqui', 'abram este menu', 'digitem sua senha', 'entenderam', 'tentem agora', 'perfeito', 'tentem novamente', 'salvem'],
                'zh-CN': ['点击这里', '打开这个菜单', '输入您的密码', '您明白了吗', '现在试试', '完美', '再试一次', '保存'],
                'ar': ['انقروا هنا', 'افتحوا هذه القائمة', 'اكتبوا كلمة المرور', 'هل فهمتم', 'جربوا الآن', 'مثالي', 'حاولوا مرة أخرى', 'احفظوا']
            },
            'journalisme': {
                'fr': ['pouvez-vous expliquer', 'que pensez-vous de', 'comment voyez-vous', 'merci pour cette interview', 'une dernière question', 'très intéressant'],
                'en': ['can you explain', 'what do you think about', 'how do you see', 'thank you for this interview', 'one last question', 'very interesting'],
                'es': ['pueden explicar', 'qué piensan de', 'cómo ven', 'gracias por esta entrevista', 'una última pregunta', 'muy interesante'],
                'de': ['können sie erklären', 'was denken sie über', 'wie sehen sie', 'danke für dieses interview', 'eine letzte frage', 'sehr interessant'],
                'it': ['potete spiegare', 'cosa pensate di', 'come vedete', 'grazie per questa intervista', 'un\'ultima domanda', 'molto interessante'],
                'pt': ['podem explicar', 'o que pensam sobre', 'como veem', 'obrigado por esta entrevista', 'uma última pergunta', 'muito interessante'],
                'zh-CN': ['您能解释吗', '您对什么看法', '您如何看待', '感谢这次采访', '最后一个问题', '非常有趣'],
                'ar': ['هل يمكنكم الشرح', 'ما رأيكم في', 'كيف ترون', 'شكرا لهذه المقابلة', 'سؤال أخير', 'مثير جدا للاهتمام']
            },
            'reunion': {
                'fr': ['point suivant', 'avez-vous des questions', 'qui peut prendre cette action', 'quand pouvons-nous', 'merci pour votre participation', 'récapitulons'],
                'en': ['next point', 'do you have questions', 'who can take this action', 'when can we', 'thank you for your participation', 'let\'s recap'],
                'es': ['siguiente punto', 'tienen preguntas', 'quién puede tomar esta acción', 'cuándo podemos', 'gracias por su participación', 'resumamos'],
                'de': ['nächster punkt', 'haben sie fragen', 'wer kann diese aktion übernehmen', 'wann können wir', 'danke für ihre teilnahme', 'fassen wir zusammen'],
                'it': ['punto successivo', 'avete domande', 'chi può prendere questa azione', 'quando possiamo', 'grazie per la vostra partecipazione', 'riassumiamo'],
                'pt': ['próximo ponto', 'têm perguntas', 'quem pode tomar esta ação', 'quando podemos', 'obrigado pela participação', 'vamos resumir'],
                'zh-CN': ['下一点', '你们有问题吗', '谁能采取这个行动', '我们什么时候能', '感谢您的参与', '让我们总结'],
                'ar': ['النقطة التالية', 'هل لديكم أسئلة', 'من يمكنه اتخاذ هذا الإجراء', 'متى يمكننا', 'شكرا لمشاركتكم', 'دعونا نلخص']
            }
        }
        
        # Initialiser les compteurs et caches (ÉTENDU)
        self.init_counters()
        self.init_smart_cache()
    
    # 🆕 NOUVELLE FONCTION : Initialisation du cache intelligent
    def init_smart_cache(self):
        """Initialise le cache intelligent et charge les données existantes"""
        smart_cache_file = "smart_cache.json"
        
        if os.path.exists(smart_cache_file):
            try:
                with open(smart_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.smart_cache = cache_data.get('smart_cache', {})
                    self.phrase_frequency = cache_data.get('phrase_frequency', {})
                    self.sector_cache = cache_data.get('sector_cache', {})
                    print(f"✅ Cache intelligent chargé: {len(self.smart_cache)} fragments")
            except Exception as e:
                print(f"⚠️ Erreur chargement cache intelligent: {e}")
        
        # Pré-remplir avec les phrases professionnelles
        self.preload_professional_cache()
    
    def preload_professional_cache(self):
        """Pré-remplit le cache avec les phrases professionnelles courantes"""
        for sector, languages in self.professional_phrases.items():
            for lang, phrases in languages.items():
                for phrase in phrases:
                    # Créer des traductions bidirectionnelles fr <-> autres langues
                    if lang == 'fr':
                        for target_lang, target_phrases in languages.items():
                            if target_lang != 'fr' and len(target_phrases) > phrases.index(phrase):
                                cache_key = f"{phrase.lower()}|auto|{target_lang}"
                                translation = target_phrases[phrases.index(phrase)]
                                self.smart_cache[cache_key] = {
                                    'translation': translation,
                                    'confidence': 'professional',
                                    'sector': sector,
                                    'timestamp': time.time()
                                }
        
        print(f"🌍 Cache professionnel multilingue initialisé: {len(self.smart_cache)} phrases (8 langues x 6 secteurs)")
    
    def save_smart_cache(self):
        """Sauvegarde le cache intelligent"""
        try:
            cache_data = {
                'smart_cache': self.smart_cache,
                'phrase_frequency': self.phrase_frequency,
                'sector_cache': self.sector_cache,
                'last_update': time.time()
            }
            
            with open("smart_cache.json", 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde cache intelligent: {e}")
    
    def extract_fragments(self, text):
        """Extrait des fragments significatifs d'un texte"""
        # Nettoyer et normaliser le texte
        text_clean = re.sub(r'[^\w\s]', '', text.lower()).strip()
        words = text_clean.split()
        
        fragments = []
        
        # Fragments de 1 mot (mots importants uniquement)
        important_words = [word for word in words if len(word) > 2]
        fragments.extend(important_words)
        
        # Fragments de 2-3 mots (très utiles)
        for i in range(len(words) - 1):
            fragments.append(' '.join(words[i:i+2]))
            if i < len(words) - 2:
                fragments.append(' '.join(words[i:i+3]))
        
        # La phrase complète
        fragments.append(text_clean)
        
        return fragments
    
    def update_phrase_frequency(self, text):
        """Met à jour la fréquence d'utilisation des phrases"""
        text_key = text.lower().strip()
        self.phrase_frequency[text_key] = self.phrase_frequency.get(text_key, 0) + 1
        
        # Nettoyer si trop de phrases
        if len(self.phrase_frequency) > self.max_phrase_frequency:
            # Garder les plus fréquentes
            sorted_phrases = sorted(self.phrase_frequency.items(), key=lambda x: x[1], reverse=True)
            self.phrase_frequency = dict(sorted_phrases[:self.max_phrase_frequency])
        
        # Sauvegarder périodiquement
        if self.phrase_frequency[text_key] % 5 == 0:  # Toutes les 5 utilisations
            self.save_smart_cache()
    
    def check_smart_cache(self, text, source_lang, target_lang):
        """Vérifie le cache intelligent pour des correspondances"""
        # 1. Vérifier le cache exact (ancien système conservé)
        exact_key = f"{text.lower()}|{source_lang}|{target_lang}"
        if exact_key in self.translation_cache:
            return self.translation_cache[exact_key], 'exact_cache'
        
        # 2. Vérifier le cache intelligent
        smart_key = f"{text.lower()}|{source_lang}|{target_lang}"
        if smart_key in self.smart_cache:
            return self.smart_cache[smart_key]['translation'], 'smart_cache'
        
        # 3. Vérifier les fragments
        fragments = self.extract_fragments(text)
        for fragment in fragments:
            fragment_key = f"{fragment}|{source_lang}|{target_lang}"
            if fragment_key in self.smart_cache:
                confidence = self.smart_cache[fragment_key].get('confidence', 'fragment')
                if confidence in ['professional', 'frequent']:
                    return self.smart_cache[fragment_key]['translation'], f'fragment_cache:{fragment}'
        
        return None, None
    
    def add_to_smart_cache(self, text, source_lang, target_lang, translation):
        """Ajoute une traduction au cache intelligent"""
        # 1. Ajouter à l'ancien cache (conservé pour compatibilité)
        cache_key = f"{text.lower()}|{source_lang}|{target_lang}"
        if len(self.translation_cache) < self.max_cache_size:
            self.translation_cache[cache_key] = translation
        
        # 2. Ajouter au cache intelligent
        smart_key = f"{text.lower()}|{source_lang}|{target_lang}"
        
        # Déterminer la confiance basée sur la fréquence
        frequency = self.phrase_frequency.get(text.lower(), 0)
        if frequency >= 5:
            confidence = 'frequent'
        elif frequency >= 2:
            confidence = 'common'
        else:
            confidence = 'single'
        
        self.smart_cache[smart_key] = {
            'translation': translation,
            'confidence': confidence,
            'frequency': frequency,
            'timestamp': time.time()
        }
        
        # 3. Ajouter les fragments utiles
        if confidence in ['frequent', 'common']:
            fragments = self.extract_fragments(text)
            for fragment in fragments:
                if len(fragment.split()) <= 3:  # Fragments courts seulement
                    fragment_key = f"{fragment}|{source_lang}|{target_lang}"
                    if fragment_key not in self.smart_cache:
                        # Essayer de deviner la traduction du fragment
                        fragment_translation = self.extract_fragment_translation(fragment, text, translation)
                        if fragment_translation:
                            self.smart_cache[fragment_key] = {
                                'translation': fragment_translation,
                                'confidence': 'fragment',
                                'parent': text,
                                'timestamp': time.time()
                            }
        
        # 4. Nettoyer si nécessaire
        if len(self.smart_cache) > self.max_smart_cache_size:
            self.cleanup_smart_cache()
        
        # 5. Mettre à jour la fréquence
        self.update_phrase_frequency(text)
    
    def extract_fragment_translation(self, fragment, original_text, original_translation):
        """Essaie d'extraire la traduction d'un fragment à partir de la traduction complète"""
        # Technique simple : chercher le fragment dans la traduction
        fragment_words = fragment.lower().split()
        translation_words = original_translation.lower().split()
        
        # Si le fragment fait 1 mot, chercher une correspondance approximative
        if len(fragment_words) == 1:
            fragment_word = fragment_words[0]
            # Chercher dans les dictionnaires pré-remplis
            for sector, languages in self.professional_phrases.items():
                for lang, phrases in languages.items():
                    for i, phrase in enumerate(phrases):
                        if fragment_word in phrase.lower():
                            # Trouver la traduction correspondante
                            for target_lang, target_phrases in languages.items():
                                if target_lang != lang and i < len(target_phrases):
                                    if fragment_word in phrase.lower():
                                        return target_phrases[i]
        
        return None
    
    def cleanup_smart_cache(self):
        """Nettoie le cache intelligent en gardant les plus utiles"""
        # Garder par priorité : professional > frequent > common > fragment > single
        priority_order = ['professional', 'frequent', 'common', 'fragment', 'single']
        
        sorted_cache = []
        for key, value in self.smart_cache.items():
            confidence = value.get('confidence', 'single')
            priority = priority_order.index(confidence) if confidence in priority_order else 999
            sorted_cache.append((priority, key, value))
        
        # Trier par priorité et garder les meilleurs
        sorted_cache.sort(key=lambda x: x[0])
        
        # Garder les plus utiles
        self.smart_cache = {}
        for priority, key, value in sorted_cache[:self.max_smart_cache_size]:
            self.smart_cache[key] = value
    
    def get_cache_stats(self):
        """Retourne des statistiques sur le cache intelligent"""
        total_smart = len(self.smart_cache)
        
        stats = {'total': total_smart}
        for confidence in ['professional', 'frequent', 'common', 'fragment', 'single']:
            count = sum(1 for v in self.smart_cache.values() if v.get('confidence') == confidence)
            stats[confidence] = count
        
        return stats

    # TOUTES LES FONCTIONS EXISTANTES CONSERVÉES IDENTIQUES
    def set_preferred_language(self, lang):
        """Définit la langue préférée à utiliser lorsque 'auto' est spécifié avec MyMemory"""
        if lang != 'auto':
            self.preferred_lang = lang
        print(f"Langue préférée définie sur: {self.preferred_lang}")
    
    def init_counters(self):
        """Initialise ou récupère les compteurs d'utilisation"""
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
            return ['google']
        
        return available_services
    
    def check_cache(self, text, source_lang, target_lang):
        """🆕 MODIFIÉ : Vérifie d'abord le cache intelligent, puis l'ancien"""
        result, cache_type = self.check_smart_cache(text, source_lang, target_lang)
        if result:
            print(f"⚡ Traduction trouvée dans {cache_type}!")
            return result
        return None
    
    def add_to_cache(self, text, source_lang, target_lang, translation):
        """🆕 MODIFIÉ : Ajoute au cache intelligent au lieu de l'ancien seulement"""
        self.add_to_smart_cache(text, source_lang, target_lang, translation)
    
    def map_lang_code(self, lang_code, for_mymemory=False):
        """Convertit les codes de langue au format approprié pour MyMemory si nécessaire"""
        if not for_mymemory:
            return lang_code
            
        if lang_code == 'auto':
            preferred = self.preferred_lang
            if preferred in self.mymemory_lang_map:
                mapped_code = self.mymemory_lang_map[preferred]
            else:
                mapped_code = f"{preferred}-{preferred.upper()}" if len(preferred) == 2 else preferred
            
            print(f"ATTENTION: 'auto' n'est pas supporté par MyMemory, utilisation de '{mapped_code}' à la place")
            return mapped_code
        
        if lang_code in self.mymemory_lang_map:
            return self.mymemory_lang_map[lang_code]
        
        if len(lang_code) == 2:
            return f"{lang_code}-{lang_code.upper()}"
        
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
        }
        
        if target_lang in corrections:
            for wrong, correct in corrections[target_lang].items():
                translation = translation.replace(wrong, correct)
        
        return translation
    
    def can_use_deepl(self, source_lang, target_lang):
        """Vérifie si DeepL peut traiter cette paire de langues"""
        supported_langs = ['fr', 'en', 'de', 'es', 'it', 'pt', 'ru', 'ja', 'zh-CN']
        return (source_lang in supported_langs or source_lang == 'auto') and target_lang in supported_langs
    
    def translate_with_service(self, text, source_lang, target_lang, service):
        """Traduit avec un service spécifique"""
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
    
    def translate(self, text, source_lang, target_lang='fr'):
        """🆕 AMÉLIORÉ : Traduit avec cache intelligent + 3 services parallèles"""
        if not text or text.strip() == "":
            return ""
        
        if source_lang != 'auto':
            self.set_preferred_language(source_lang)
        
        # 1. 🚀 NOUVEAU : Vérifier le cache intelligent d'abord
        cached_translation = self.check_cache(text, source_lang, target_lang)
        if cached_translation:
            return cached_translation
        
        # 2. Obtenir la liste des services disponibles (IDENTIQUE)
        available_services = self.get_available_services()
        
        if 'deepl' in available_services and not self.can_use_deepl(source_lang, target_lang):
            available_services.remove('deepl')
            print(f"ℹ️ DeepL retiré (langues {source_lang}->{target_lang} non supportées)")
        
        print(f"🚀 Traduction PARALLÈLE avec {len(available_services)} services: {available_services}")
        
        # 3. 🆕 STATISTIQUES : Afficher les stats du cache
        cache_stats = self.get_cache_stats()
        print(f"📊 Cache intelligent: {cache_stats['total']} entrées (pro: {cache_stats.get('professional', 0)}, fréq: {cache_stats.get('frequent', 0)})")
        
        # 4. Lancer TOUS les services en parallèle (IDENTIQUE)
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
                    
                    print(f"✅ PREMIER résultat reçu de {used_service} en {elapsed:.2f}s")
                    
                    # 5. Post-traitement et cache intelligent (AMÉLIORÉ)
                    translation = self.post_process_translation(translation, target_lang)
                    self.add_to_cache(text, source_lang, target_lang, translation)
                    
                    return translation
                    
                except Exception as e:
                    print(f"❌ Échec {service}: {str(e)}")
                    continue
        
        return f"Erreur de traduction: tous les services ont échoué"

# Créer une instance globale
translation_manager = TranslationManager()

