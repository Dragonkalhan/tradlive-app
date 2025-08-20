import os
import json
import threading
import time
import re
from datetime import datetime
from deep_translator import GoogleTranslator, MyMemoryTranslator, DeeplTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed

# 🧠 SYSTÈME DE DÉTECTION DE DOMAINE INTÉGRÉ
class DomainDetector:
    def __init__(self):
        # 🚨 Domaines CRITIQUES (Mode Précision Obligatoire) - 16 LANGUES
        self.critical_domains = {
            'medical': {
                'keywords': {
                    'fr': ['patient', 'diagnostic', 'symptôme', 'maladie', 'médicament', 'traitement', 'douleur', 'fièvre', 'consultation', 'ordonnance', 'allergie', 'infection', 'chirurgie', 'urgence', 'hôpital', 'mal'],
                    'en': ['patient', 'diagnosis', 'symptom', 'disease', 'medication', 'treatment', 'pain', 'fever', 'consultation', 'prescription', 'allergy', 'infection', 'surgery', 'emergency', 'hospital', 'hurt', 'ache'],
                    'es': ['paciente', 'diagnóstico', 'síntoma', 'enfermedad', 'medicamento', 'tratamiento', 'dolor', 'fiebre', 'consulta', 'receta', 'alergia', 'infección', 'cirugía', 'urgencia', 'hospital', 'mal', 'duele'],
                    'de': ['patient', 'diagnose', 'symptom', 'krankheit', 'medikament', 'behandlung', 'schmerz', 'fieber', 'beratung', 'rezept', 'allergie', 'infektion', 'chirurgie', 'notfall', 'krankenhaus', 'weh', 'schmerzt'],
                    'it': ['paziente', 'diagnosi', 'sintomo', 'malattia', 'farmaco', 'trattamento', 'dolore', 'febbre', 'consultazione', 'prescrizione', 'allergia', 'infezione', 'chirurgia', 'emergenza', 'ospedale', 'male', 'fa male'],
                    'pt': ['paciente', 'diagnóstico', 'sintoma', 'doença', 'medicamento', 'tratamento', 'dor', 'febre', 'consulta', 'receita', 'alergia', 'infecção', 'cirurgia', 'emergência', 'hospital', 'mal', 'dói'],
                    'ru': ['пациент', 'диагноз', 'симптом', 'болезнь', 'лекарство', 'лечение', 'боль', 'лихорадка', 'консультация', 'рецепт', 'аллергия', 'инфекция', 'хирургия', 'скорая', 'больница', 'болит', 'больно'],
                    'zh-CN': ['病人', '诊断', '症状', '疾病', '药物', '治疗', '疼痛', '发烧', '咨询', '处方', '过敏', '感染', '手术', '急诊', '医院', '疼', '痛'],
                    'ja': ['患者', '診断', '症状', '病気', '薬', '治療', '痛み', '熱', '相談', '処方箋', 'アレルギー', '感染', '手術', '救急', '病院', '痛い', '具合'],
                    'ar': ['مريض', 'تشخيص', 'عرض', 'مرض', 'دواء', 'علاج', 'ألم', 'حمى', 'استشارة', 'وصفة', 'حساسية', 'عدوى', 'جراحة', 'طوارئ', 'مستشفى', 'يؤلم', 'وجع'],
                    'uk': ['пацієнт', 'діагноз', 'симптом', 'хвороба', 'ліки', 'лікування', 'біль', 'гарячка', 'консультація', 'рецепт', 'алергія', 'інфекція', 'хірургія', 'швидка', 'лікарня', 'болить', 'боляче'],
                    'fa': ['بیمار', 'تشخیص', 'علامت', 'بیماری', 'دارو', 'درمان', 'درد', 'تب', 'مشاوره', 'نسخه', 'حساسیت', 'عفونت', 'جراحی', 'اورژانس', 'بیمارستان', 'درد دارد', 'درد می‌کند'],
                    'hi': ['मरीज', 'निदान', 'लक्षण', 'बीमारी', 'दवा', 'इलाज', 'दर्द', 'बुखार', 'सलाह', 'नुस्खा', 'एलर्जी', 'संक्रमण', 'सर्जरी', 'आपातकाल', 'अस्पताल', 'दर्द', 'दुख'],
                    'bn': ['রোগী', 'নির্ণয়', 'লক্ষণ', 'রোগ', 'ওষুধ', 'চিকিৎসা', 'ব্যথা', 'জ্বর', 'পরামর্শ', 'প্রেসক্রিপশন', 'অ্যালার্জি', 'সংক্রমণ', 'অস্ত্রোপচার', 'জরুরি', 'হাসপাতাল', 'ব্যথা', 'কষ্ট'],
                    'te': ['రోగి', 'నిర్ధారణ', 'లక్షణం', 'వ్యాధి', 'మందు', 'చికిత్స', 'నొప్పి', 'జ్వరం', 'సలహా', 'ప్రిస్క్రిప్షన్', 'అలెర్జీ', 'ఇన్ఫెక్షన్', 'శస్త్రచికిత్స', 'అత్యవసర', 'ఆసుపత్రి', 'నొప్పి', 'బాధ'],
                    'mr': ['रुग्ण', 'निदान', 'लक्षण', 'आजार', 'औषध', 'उपचार', 'वेदना', 'ताप', 'सल्ला', 'प्रिस्क्रिप्शन', 'ऍलर्जी', 'संसर्ग', 'शस्त्रक्रिया', 'आपत्कालीन', 'रुग्णालय', 'दुखते', 'वेदना']
                },
                'mode': 'precision',
                'confidence_threshold': 0.25  # Plus sensible pour sécurité
            },
            'legal': {
                'keywords': {
                    'fr': ['contrat', 'clause', 'juridique', 'tribunal', 'avocat', 'procédure', 'droit', 'loi', 'responsabilité', 'litige'],
                    'en': ['contract', 'clause', 'legal', 'court', 'lawyer', 'procedure', 'law', 'statute', 'liability', 'litigation'],
                    'es': ['contrato', 'cláusula', 'jurídico', 'tribunal', 'abogado', 'procedimiento', 'derecho', 'ley', 'responsabilidad', 'litigio'],
                    'de': ['vertrag', 'klausel', 'rechtlich', 'gericht', 'anwalt', 'verfahren', 'recht', 'gesetz', 'haftung', 'rechtsstreit'],
                    'it': ['contratto', 'clausola', 'legale', 'tribunale', 'avvocato', 'procedura', 'diritto', 'legge', 'responsabilità', 'contenzioso'],
                    'pt': ['contrato', 'cláusula', 'jurídico', 'tribunal', 'advogado', 'procedimento', 'direito', 'lei', 'responsabilidade', 'litígio'],
                    'ru': ['контракт', 'условие', 'юридический', 'суд', 'адвокат', 'процедура', 'право', 'закон', 'ответственность', 'спор'],
                    'zh-CN': ['合同', '条款', '法律', '法院', '律师', '程序', '权利', '法律', '责任', '诉讼'],
                    'ja': ['契約', '条項', '法的', '裁判所', '弁護士', '手続き', '権利', '法律', '責任', '訴訟'],
                    'ar': ['عقد', 'شرط', 'قانوني', 'محكمة', 'محامي', 'إجراء', 'حق', 'قانون', 'مسؤولية', 'نزاع'],
                    'uk': ['контракт', 'умова', 'юридичний', 'суд', 'адвокат', 'процедура', 'право', 'закон', 'відповідальність', 'спір'],
                    'fa': ['قرارداد', 'شرط', 'حقوقی', 'دادگاه', 'وکیل', 'روند', 'حق', 'قانون', 'مسئولیت', 'دعوا'],
                    'hi': ['अनुबंध', 'खंड', 'कानूनी', 'अदालत', 'वकील', 'प्रक्रिया', 'अधिकार', 'कानून', 'जिम्मेदारी', 'मुकदमा'],
                    'bn': ['চুক্তি', 'ধারা', 'আইনি', 'আদালত', 'আইনজীবী', 'প্রক্রিয়া', 'অধিকার', 'আইন', 'দায়বদ্ধতা', 'মামলা'],
                    'te': ['ఒప్పందం', 'నిబంధన', 'చట్టపరమైన', 'కోర్టు', 'లాయర్', 'విధానం', 'హక్కు', 'చట్టం', 'బాధ్యత', 'వ్యాజ్యం'],
                    'mr': ['करार', 'कलम', 'कायदेशीर', 'न्यायालय', 'वकील', 'प्रक्रिया', 'हक्क', 'कायदा', 'जबाबदारी', 'खटला']
                },
                'mode': 'precision',
                'confidence_threshold': 0.25
            },
            'financial': {
                'keywords': {
                    'fr': ['investissement', 'crédit', 'prêt', 'assurance', 'hypothèque', 'placement', 'épargne', 'impôt', 'banque', 'compte'],
                    'en': ['investment', 'credit', 'loan', 'insurance', 'mortgage', 'investment', 'savings', 'tax', 'bank', 'account'],
                    'es': ['inversión', 'crédito', 'préstamo', 'seguro', 'hipoteca', 'inversión', 'ahorro', 'impuesto', 'banco', 'cuenta'],
                    'de': ['investition', 'kredit', 'darlehen', 'versicherung', 'hypothek', 'anlage', 'sparen', 'steuer', 'bank', 'konto'],
                    'it': ['investimento', 'credito', 'prestito', 'assicurazione', 'ipoteca', 'investimento', 'risparmio', 'tassa', 'banca', 'conto'],
                    'pt': ['investimento', 'crédito', 'empréstimo', 'seguro', 'hipoteca', 'investimento', 'poupança', 'imposto', 'banco', 'conta'],
                    'ru': ['инвестиция', 'кредит', 'займ', 'страхование', 'ипотека', 'размещение', 'сбережения', 'налог', 'банк', 'счет'],
                    'zh-CN': ['投资', '信贷', '贷款', '保险', '抵押', '投资', '储蓄', '税收', '银行', '账户'],
                    'ja': ['投資', 'クレジット', 'ローン', '保険', '住宅ローン', '投資', '貯蓄', '税金', '银行', '口座'],
                    'ar': ['استثمار', 'ائتمان', 'قرض', 'تأمين', 'رهن', 'استثمار', 'ادخار', 'ضريبة', 'بنك', 'حساب'],
                    'uk': ['інвестиція', 'кредит', 'позика', 'страхування', 'іпотека', 'розміщення', 'заощадження', 'податок', 'банк', 'рахунок'],
                    'fa': ['سرمایه گذاری', 'اعتبار', 'وام', 'بیمه', 'رهن', 'سرمایه گذاری', 'پس انداز', 'مالیات', 'بانک', 'حساب'],
                    'hi': ['निवेश', 'क्रेडिट', 'ऋण', 'बीमा', 'गिरवी', 'निवेश', 'बचत', 'कर', 'बैंक', 'खाता'],
                    'bn': ['বিনিয়োগ', 'ঋণ', 'ঋণ', 'বীমা', 'বন্ধক', 'বিনিয়োগ', 'সঞ্চয়', 'কর', 'ব্যাংক', 'অ্যাকাউন্ট'],
                    'te': ['పెట్టుబడి', 'క్రెడిట్', 'రుణం', 'భీమా', 'తనఖా', 'పెట్టుబడి', 'పొదుపు', 'పన్ను', 'బ్యాంక్', 'ఖాతా'],
                    'mr': ['गुंतवणूक', 'कर्ज', 'कर्ज', 'विमा', 'गहाण', 'गुंतवణूक', 'बचत', 'कर', 'बँक', 'खाते']
                },
                'mode': 'precision',
                'confidence_threshold': 0.3
            }
        }
        
        # 🟢 Domaines SÛRS (Mode Pipeline OK) - 16 LANGUES
        self.safe_domains = {
            'digital_training': {
                'keywords': {
                    'fr': ['cliquez', 'menu', 'ordinateur', 'souris', 'clavier', 'internet', 'email', 'mot de passe', 'fichier', 'dossier', 'télécharger', 'sauvegarder', 'copier', 'coller', 'wifi'],
                    'en': ['click', 'menu', 'computer', 'mouse', 'keyboard', 'internet', 'email', 'password', 'file', 'folder', 'download', 'save', 'copy', 'paste', 'wifi'],
                    'es': ['hacer clic', 'menú', 'ordenador', 'ratón', 'teclado', 'internet', 'email', 'contraseña', 'archivo', 'carpeta', 'descargar', 'guardar', 'copiar', 'pegar', 'wifi'],
                    'de': ['klicken', 'menü', 'computer', 'maus', 'tastatur', 'internet', 'email', 'passwort', 'datei', 'ordner', 'herunterladen', 'speichern', 'kopieren', 'einfügen', 'wifi'],
                    'it': ['fare clic', 'menu', 'computer', 'mouse', 'tastiera', 'internet', 'email', 'password', 'file', 'cartella', 'scaricare', 'salvare', 'copiare', 'incollare', 'wifi'],
                    'pt': ['clicar', 'menu', 'computador', 'mouse', 'teclado', 'internet', 'email', 'senha', 'arquivo', 'pasta', 'baixar', 'salvar', 'copiar', 'colar', 'wifi'],
                    'ru': ['нажать', 'меню', 'компьютер', 'мышь', 'клавиатура', 'интернет', 'email', 'пароль', 'файл', 'папка', 'скачать', 'сохранить', 'копировать', 'вставить', 'wifi'],
                    'zh-CN': ['点击', '菜单', '电脑', '鼠标', '键盘', '互联网', '邮件', '密码', '文件', '文件夹', '下载', '保存', '复制', '粘贴', '无线网络'],
                    'ja': ['クリック', 'メニュー', 'コンピュータ', 'マウス', 'キーボード', 'インターネット', 'メール', 'パスワード', 'ファイル', 'フォルダ', 'ダウンロード', '保存', 'コピー', '貼り付け', 'wifi'],
                    'ar': ['انقر', 'قائمة', 'كمبيوتر', 'فأرة', 'لوحة المفاتيح', 'إنترنت', 'بريد إلكتروني', 'كلمة مرور', 'ملف', 'مجلد', 'تحميل', 'حفظ', 'نسخ', 'لصق', 'واي فاي'],
                    'uk': ['клікнути', 'меню', 'комп\'ютер', 'миша', 'клавіатура', 'інтернет', 'email', 'пароль', 'файл', 'папка', 'завантажити', 'зберегти', 'копіювати', 'вставити', 'wifi'],
                    'fa': ['کلیک', 'منو', 'کامپیوتر', 'ماوس', 'کیبورد', 'اینترنت', 'ایمیل', 'رمز عبور', 'فایل', 'پوشه', 'دانلود', 'ذخیره', 'کپی', 'چسباندن', 'وای فای'],
                    'hi': ['क्लिक', 'मेनू', 'कंप्यूटर', 'माउस', 'कीबोर्ड', 'इंटरनेट', 'ईमेल', 'पासवर्ड', 'फ़ाइल', 'फ़ोल्डर', 'डाउनलोड', 'सेव', 'कॉपी', 'पेस्ट', 'वाईफाई'],
                    'bn': ['ক্লিক', 'মেনু', 'কম্পিউটার', 'মাউস', 'কিবোর্ড', 'ইন্টারনেট', 'ইমেইল', 'পাসওয়ার্ড', 'ফাইল', 'ফোল্ডার', 'ডাউনলোড', 'সেভ', 'কপি', 'পেস্ট', 'ওয়াইফাই'],
                    'te': ['క్లిక్', 'మెనూ', 'కంప్యూటర్', 'మౌస్', 'కీబోర్డ్', 'ఇంటర్నెట్', 'ఇమెయిల్', 'పాస్‌వర్డ్', 'ఫైల్', 'ఫోల్డర్', 'డౌన్‌లోడ్', 'సేవ్', 'కాపీ', 'పేస్ట్', 'వైఫై'],
                    'mr': ['क्लिक', 'मेनू', 'संगणक', 'माऊस', 'कीबोर्ड', 'इंटरनेट', 'ईमेल', 'पासवर्ड', 'फाइल', 'फोल्डर', 'डाउनलोड', 'सेव्ह', 'कॉपी', 'पेस्ट', 'वायफाय']
                },
                'mode': 'pipeline',
                'confidence_threshold': 0.4
            }
        }
        
        # État actuel
        self.current_domain = None
        self.current_mode = 'precision'  # Par défaut : sécurité max
        self.forced_mode = None  # Mode forcé par l'utilisateur
        
    def detect_domain(self, text, source_lang='auto', forced_mode=None):
        """🧠 Détecte le domaine et recommande un mode de traduction"""
        
        # 1. Mode forcé par l'utilisateur (priorité absolue)
        if forced_mode:
            self.forced_mode = forced_mode
            self.current_mode = forced_mode
            return {
                'domain': 'user_forced',
                'mode': forced_mode,
                'confidence': 1.0,
                'source': 'user_override',
                'safe_for_pipeline': forced_mode == 'pipeline'
            }
        
        # 2. Analyser le texte pour détecter un domaine critique
        text_lower = text.lower()
        
        # Vérifier d'abord les domaines CRITIQUES (priorité absolue)
        for domain_name, domain_info in self.critical_domains.items():
            score = self._calculate_domain_score(text_lower, domain_info, source_lang)
            
            if score > 0:  # Même 1 seul mot critique = mode précision
                self.current_domain = domain_name
                self.current_mode = 'precision'
                
                return {
                    'domain': domain_name,
                    'mode': 'precision',
                    'confidence': score,
                    'source': 'critical_detection',
                    'safe_for_pipeline': False,
                    'warning': f"⚠️ Domaine {domain_name} détecté - Mode précision activé pour votre sécurité"
                }
        
        # 3. Vérifier les domaines SÛRS (formation numérique)
        for domain_name, domain_info in self.safe_domains.items():
            score = self._calculate_domain_score(text_lower, domain_info, source_lang)
            
            if score >= 2:  # Au moins 2 mots = domaine sûr détecté
                self.current_domain = domain_name
                self.current_mode = 'pipeline'
                
                return {
                    'domain': domain_name,
                    'mode': 'pipeline',
                    'confidence': score,
                    'source': 'safe_detection',
                    'safe_for_pipeline': True,
                    'info': f"🚀 {domain_name} détecté - Mode rapide activé pour plus de fluidité"
                }
        
        # 4. Aucun domaine spécifique détecté = mode sécurisé par défaut
        self.current_domain = 'general'
        self.current_mode = 'precision'
        
        return {
            'domain': 'general',
            'mode': 'precision',
            'confidence': 0.0,
            'source': 'default_safe',
            'safe_for_pipeline': False,
            'info': "ℹ️ Mode précision activé par sécurité"
        }
    
    def _calculate_domain_score(self, text_lower, domain_info, source_lang):
        """Calcule le score d'un domaine pour un texte donné"""
        score = 0
        
        # Langues à vérifier
        languages_to_check = []
        if source_lang != 'auto' and source_lang in domain_info['keywords']:
            languages_to_check = [source_lang]
        else:
            languages_to_check = domain_info['keywords'].keys()
        
        for lang in languages_to_check:
            if lang in domain_info['keywords']:
                for keyword in domain_info['keywords'][lang]:
                    if keyword in text_lower:
                        score += 1
        
        return score

class TranslationManager:
    def __init__(self):
        # 🆕 NOUVEAU : Détecteur de domaine intégré
        self.domain_detector = DomainDetector()
        
        # Limites mensuelles avec DeepL inclus (INCHANGÉ)
        self.limits = {
            'google': 500000,    # 500K caractères/mois
            'mymemory': 500000,  # 500K caractères/mois
            'deepl': 500000      # 500K caractères/mois
        }
        
        # Cache intelligent étendu (CONSERVÉ)
        self.translation_cache = {}
        self.smart_cache = {}
        self.phrase_frequency = {}
        self.sector_cache = {}
        
        self.max_cache_size = 100
        self.max_smart_cache_size = 500
        self.max_phrase_frequency = 200
        
        # Langue préférée (INCHANGÉ)
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
        
        # Dictionnaires pré-remplis par secteur professionnel (CONSERVÉS)
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
            'numerique': {
                'fr': ['cliquez', 'ouvrez', 'tapez', 'avez-vous compris', 'essayez', 'parfait', 'recommencez', 'sauvegardez'],
                'en': ['click', 'open', 'type', 'do you understand', 'try', 'perfect', 'try again', 'save'],
                'es': ['hagan clic', 'abran', 'escriban', 'han entendido', 'prueben', 'perfecto', 'inténtenlo', 'guarden'],
                'de': ['klicken', 'öffnen', 'geben sie ein', 'haben sie verstanden', 'versuchen', 'perfekt', 'nochmal', 'speichern'],
                'it': ['cliccate', 'aprite', 'digitate', 'avete capito', 'provate', 'perfetto', 'riprovate', 'salvate'],
                'pt': ['cliquem', 'abram', 'digitem', 'entenderam', 'tentem', 'perfeito', 'novamente', 'salvem'],
                'zh-CN': ['点击', '打开', '输入', '您明白了吗', '试试', '完美', '再试', '保存'],
                'ar': ['انقروا', 'افتحوا', 'اكتبوا', 'هل فهمتم', 'جربوا', 'مثالي', 'مرة أخرى', 'احفظوا']
            }
        }
        
        # Initialiser tous les systèmes
        self.init_counters()
        self.init_smart_cache()
    
    # 🆕 FONCTION PRINCIPALE AMÉLIORÉE : Traduction avec détection de domaine
    def translate(self, text, source_lang, target_lang='fr', forced_mode=None):
        """🧠 Traduit avec détection intelligente de domaine + cache + 3 services parallèles"""
        if not text or text.strip() == "":
            return ""
        
        if source_lang != 'auto':
            self.set_preferred_language(source_lang)
        
        # 🧠 NOUVEAU : Détection du domaine AVANT traduction
        domain_analysis = self.domain_detector.detect_domain(text, source_lang, forced_mode)
        translation_mode = domain_analysis['mode']
        
        # Afficher l'info de détection
        if 'warning' in domain_analysis:
            print(domain_analysis['warning'])
        elif 'info' in domain_analysis:
            print(domain_analysis['info'])
        
        # 1. Vérifier le cache intelligent d'abord
        cached_translation = self.check_cache(text, source_lang, target_lang)
        if cached_translation:
            print(f"⚡ Traduction trouvée dans le cache ! (Mode détecté: {translation_mode})")
            return cached_translation
        
        # 2. Obtenir les services disponibles
        available_services = self.get_available_services()
        
        if 'deepl' in available_services and not self.can_use_deepl(source_lang, target_lang):
            available_services.remove('deepl')
            print(f"ℹ️ DeepL retiré (langues {source_lang}->{target_lang} non supportées)")
        
        print(f"🚀 Traduction PARALLÈLE avec {len(available_services)} services: {available_services}")
        print(f"🧠 Mode détecté: {translation_mode.upper()} (domaine: {domain_analysis['domain']})")
        
        # 3. Afficher les stats du cache
        cache_stats = self.get_cache_stats()
        print(f"📊 Cache intelligent: {cache_stats['total']} entrées")
        
        # 4. Lancer tous les services en parallèle (IDENTIQUE)
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
                    
                    print(f"✅ PREMIER résultat reçu de {used_service} en {elapsed:.2f}s (Mode: {translation_mode})")
                    
                    # 5. Post-traitement et cache intelligent
                    translation = self.post_process_translation(translation, target_lang)
                    self.add_to_cache(text, source_lang, target_lang, translation)
                    
                    return translation
                    
                except Exception as e:
                    print(f"❌ Échec {service}: {str(e)}")
                    continue
        
        return f"Erreur de traduction: tous les services ont échoué"
    
    # 🆕 NOUVELLES FONCTIONS DE CONTRÔLE DU MODE
    def set_forced_mode(self, mode):
        """Force un mode de traduction spécifique"""
        valid_modes = ['precision', 'balanced', 'pipeline']
        if mode in valid_modes:
            self.domain_detector.forced_mode = mode
            print(f"🎯 Mode forcé: {mode.upper()}")
            return True
        return False
    
    def get_current_mode(self):
        """Retourne le mode de traduction actuel"""
        return {
            'current_mode': self.domain_detector.current_mode,
            'current_domain': self.domain_detector.current_domain,
            'forced_mode': self.domain_detector.forced_mode
        }
    
    def reset_forced_mode(self):
        """Remet la détection automatique"""
        self.domain_detector.forced_mode = None
        print("🤖 Détection automatique réactivée")
    
    # TOUTES LES FONCTIONS EXISTANTES CONSERVÉES (inchangées)
    def set_preferred_language(self, lang):
        if lang != 'auto':
            self.preferred_lang = lang
        print(f"Langue préférée définie sur: {self.preferred_lang}")
    
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
    
    def init_smart_cache(self):
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
        
        self.preload_professional_cache()
    
    def preload_professional_cache(self):
        for sector, languages in self.professional_phrases.items():
            for lang, phrases in languages.items():
                for phrase in phrases:
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
        
        print(f"🌍 Cache professionnel multilingue initialisé: {len(self.smart_cache)} phrases (8 langues x secteurs)")
    
    def save_smart_cache(self):
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
        text_clean = re.sub(r'[^\w\s]', '', text.lower()).strip()
        words = text_clean.split()
        
        fragments = []
        important_words = [word for word in words if len(word) > 2]
        fragments.extend(important_words)
        
        for i in range(len(words) - 1):
            fragments.append(' '.join(words[i:i+2]))
            if i < len(words) - 2:
                fragments.append(' '.join(words[i:i+3]))
        
        fragments.append(text_clean)
        return fragments
    
    def update_phrase_frequency(self, text):
        text_key = text.lower().strip()
        self.phrase_frequency[text_key] = self.phrase_frequency.get(text_key, 0) + 1
        
        if len(self.phrase_frequency) > self.max_phrase_frequency:
            sorted_phrases = sorted(self.phrase_frequency.items(), key=lambda x: x[1], reverse=True)
            self.phrase_frequency = dict(sorted_phrases[:self.max_phrase_frequency])
        
        if self.phrase_frequency[text_key] % 5 == 0:
            self.save_smart_cache()
    
    def check_smart_cache(self, text, source_lang, target_lang):
        exact_key = f"{text.lower()}|{source_lang}|{target_lang}"
        if exact_key in self.translation_cache:
            return self.translation_cache[exact_key], 'exact_cache'
        
        smart_key = f"{text.lower()}|{source_lang}|{target_lang}"
        if smart_key in self.smart_cache:
            return self.smart_cache[smart_key]['translation'], 'smart_cache'
        
        fragments = self.extract_fragments(text)
        for fragment in fragments:
            fragment_key = f"{fragment}|{source_lang}|{target_lang}"
            if fragment_key in self.smart_cache:
                confidence = self.smart_cache[fragment_key].get('confidence', 'fragment')
                if confidence in ['professional', 'frequent']:
                    return self.smart_cache[fragment_key]['translation'], f'fragment_cache:{fragment}'
        
        return None, None
    
    def add_to_smart_cache(self, text, source_lang, target_lang, translation):
        cache_key = f"{text.lower()}|{source_lang}|{target_lang}"
        if len(self.translation_cache) < self.max_cache_size:
            self.translation_cache[cache_key] = translation
        
        smart_key = f"{text.lower()}|{source_lang}|{target_lang}"
        
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
        
        if confidence in ['frequent', 'common']:
            fragments = self.extract_fragments(text)
            for fragment in fragments:
                if len(fragment.split()) <= 3:
                    fragment_key = f"{fragment}|{source_lang}|{target_lang}"
                    if fragment_key not in self.smart_cache:
                        fragment_translation = self.extract_fragment_translation(fragment, text, translation)
                        if fragment_translation:
                            self.smart_cache[fragment_key] = {
                                'translation': fragment_translation,
                                'confidence': 'fragment',
                                'parent': text,
                                'timestamp': time.time()
                            }
        
        if len(self.smart_cache) > self.max_smart_cache_size:
            self.cleanup_smart_cache()
        
        self.update_phrase_frequency(text)
    
    def extract_fragment_translation(self, fragment, original_text, original_translation):
        fragment_words = fragment.lower().split()
        
        if len(fragment_words) == 1:
            fragment_word = fragment_words[0]
            for sector, languages in self.professional_phrases.items():
                for lang, phrases in languages.items():
                    for i, phrase in enumerate(phrases):
                        if fragment_word in phrase.lower():
                            for target_lang, target_phrases in languages.items():
                                if target_lang != lang and i < len(target_phrases):
                                    if fragment_word in phrase.lower():
                                        return target_phrases[i]
        
        return None
    
    def cleanup_smart_cache(self):
        priority_order = ['professional', 'frequent', 'common', 'fragment', 'single']
        
        sorted_cache = []
        for key, value in self.smart_cache.items():
            confidence = value.get('confidence', 'single')
            priority = priority_order.index(confidence) if confidence in priority_order else 999
            sorted_cache.append((priority, key, value))
        
        sorted_cache.sort(key=lambda x: x[0])
        
        self.smart_cache = {}
        for priority, key, value in sorted_cache[:self.max_smart_cache_size]:
            self.smart_cache[key] = value
    
    def get_cache_stats(self):
        total_smart = len(self.smart_cache)
        
        stats = {'total': total_smart}
        for confidence in ['professional', 'frequent', 'common', 'fragment', 'single']:
            count = sum(1 for v in self.smart_cache.values() if v.get('confidence') == confidence)
            stats[confidence] = count
        
        return stats
    
    def check_cache(self, text, source_lang, target_lang):
        result, cache_type = self.check_smart_cache(text, source_lang, target_lang)
        if result:
            print(f"⚡ Traduction trouvée dans {cache_type}!")
            return result
        return None
    
    def add_to_cache(self, text, source_lang, target_lang, translation):
        self.add_to_smart_cache(text, source_lang, target_lang, translation)
    
    def map_lang_code(self, lang_code, for_mymemory=False):
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

# Créer une instance globale
translation_manager = TranslationManager()
