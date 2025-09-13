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
                'confidence_threshold': 0.25
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
                    'te': ['పెట్టుబడి', 'క্রেডিট্', 'రుణం', 'భీమా', 'తనఖా', 'పెట్టుబడి', 'పొదుపు', 'పన్ను', 'బ్యాంక్', 'ఖాతా'],
                    'mr': ['गुंतवणूक', 'कर्ज', 'कर्ज', 'विमा', 'गहाण', 'गुंतवणूक', 'बचत', 'कर', 'बँक', 'खाते']
                },
                'mode': 'precision',
                'confidence_threshold': 0.3
            }
        }
        
        # 🟢 Domaines SÛRS (Mode Pipeline OK) - Formation numérique étendue
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
        self.current_mode = 'precision'
        self.forced_mode = None
        
    def detect_domain(self, text, source_lang='auto', forced_mode=None):
        """Détecte le domaine et recommande un mode de traduction"""
        
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
        
        text_lower = text.lower()
        
        # Vérifier domaines CRITIQUES
        for domain_name, domain_info in self.critical_domains.items():
            score = self._calculate_domain_score(text_lower, domain_info, source_lang)
            
            if score > 0:
                self.current_domain = domain_name
                self.current_mode = 'precision'
                
                return {
                    'domain': domain_name,
                    'mode': 'precision',
                    'confidence': score,
                    'source': 'critical_detection',
                    'safe_for_pipeline': False,
                    'warning': f"Domaine {domain_name} détecté - Mode précision activé"
                }
        
        # Vérifier domaines SÛRS
        for domain_name, domain_info in self.safe_domains.items():
            score = self._calculate_domain_score(text_lower, domain_info, source_lang)
            
            if score >= 2:
                self.current_domain = domain_name
                self.current_mode = 'pipeline'
                
                return {
                    'domain': domain_name,
                    'mode': 'pipeline',
                    'confidence': score,
                    'source': 'safe_detection',
                    'safe_for_pipeline': True,
                    'info': f"{domain_name} détecté - Mode rapide activé"
                }
        
        # Aucun domaine spécifique détecté
        self.current_domain = 'general'
        self.current_mode = 'precision'
        
        return {
            'domain': 'general',
            'mode': 'precision',
            'confidence': 0.0,
            'source': 'default_safe',
            'safe_for_pipeline': False
        }
    
    def _calculate_domain_score(self, text_lower, domain_info, source_lang):
        """Calcule le score d'un domaine pour un texte donné"""
        score = 0
        
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
        # Détecteur de domaine intégré
        self.domain_detector = DomainDetector()
        
        # Limites mensuelles
        self.limits = {
            'google': 500000,
            'mymemory': 500000,
            'deepl': 500000
        }
        
        # Cache isolé par room
        self.room_caches = {}
        self.room_phrase_frequency = {}
        self.translation_cache = {}
        
        # Paramètres cache
        self.max_cache_size = 100
        self.max_smart_cache_size = 500
        self.max_phrase_frequency = 200
        
        # Configuration générale
        self.preferred_lang = 'en'
        self.translation_timeout = 8
        
        # Mappings langues
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
        
        # BIBLIOTHÈQUES PROFESSIONNELLES ÉTENDUES - MOTS/PHRASES SIMPLES UNIQUEMENT
        self.professional_phrases = {
            'accueil': {
                'fr': ['bonjour', 'bonsoir', 'merci', 'au revoir', 'de rien', 'excusez-moi', 'pardon', 'très bien merci'],
                'en': ['hello', 'good evening', 'thank you', 'goodbye', 'you\'re welcome', 'excuse me', 'sorry', 'very well thank you'],
                'es': ['hola', 'buenas tardes', 'gracias', 'adiós', 'de nada', 'disculpe', 'perdón', 'muy bien gracias'],
                'de': ['hallo', 'guten abend', 'danke', 'auf wiedersehen', 'gern geschehen', 'entschuldigung', 'verzeihung', 'sehr gut danke'],
                'it': ['ciao', 'buonasera', 'grazie', 'arrivederci', 'prego', 'mi scusi', 'scusi', 'molto bene grazie'],
                'pt': ['olá', 'boa tarde', 'obrigado', 'tchau', 'de nada', 'com licença', 'desculpe', 'muito bem obrigado'],
                'ru': ['привет', 'добрый вечер', 'спасибо', 'до свидания', 'пожалуйста', 'извините', 'простите', 'очень хорошо спасибо'],
                'zh-CN': ['你好', '晚上好', '谢谢', '再见', '不客气', '对不起', '抱歉', '很好谢谢'],
                'ja': ['こんにちは', 'こんばんは', 'ありがとう', 'さようなら', 'どういたしまして', 'すみません', 'ごめんなさい', 'とても元気です'],
                'ar': ['مرحبا', 'مساء الخير', 'شكرا', 'وداعا', 'عفوا', 'معذرة', 'آسف', 'بخير شكرا'],
                'uk': ['привіт', 'добрий вечір', 'дякую', 'до побачення', 'будь ласка', 'вибачте', 'пробачте', 'дуже добре дякую'],
                'fa': ['سلام', 'عصر بخیر', 'متشکرم', 'خداحافظ', 'خواهش می‌کنم', 'ببخشید', 'شرمنده', 'خیلی خوب متشکرم'],
                'hi': ['नमस्ते', 'शुभ संध्या', 'धन्यवाद', 'अलविदा', 'कृपया', 'माफ करें', 'क्षमा करें', 'बहुत अच्छा धन्यवाद'],
                'bn': ['নমস্কার', 'শুভ সন্ধ্যা', 'ধন্যবাদ', 'বিদায়', 'অনুগ্রহ করে', 'ক্ষমা করুন', 'দুঃখিত', 'খুব ভাল ধন্যবাদ'],
                'te': ['నమస్కారం', 'శుభ సాయంత్రం', 'ధన్యవాదాలు', 'వీడ్కోలు', 'దయచేసి', 'క్షమించండి', 'కేవలం', 'చాలా బాగా ধন্যবাদাలు'],
                'mr': ['नमस्कार', 'शुभ संध्याकाळ', 'धन्यवाद', 'निरोप', 'कृपया', 'माफ करा', 'क्षमा करा', 'खूप चांगले धन्यवाद']
            },
            'numerique': {
                'fr': ['cliquez', 'ouvrez', 'tapez', 'essayez', 'parfait', 'sauvegardez'],
                'en': ['click', 'open', 'type', 'try', 'perfect', 'save'],
                'es': ['hagan clic', 'abran', 'escriban', 'prueben', 'perfecto', 'guarden'],
                'de': ['klicken', 'öffnen', 'geben sie ein', 'versuchen', 'perfekt', 'speichern'],
                'it': ['cliccate', 'aprite', 'digitate', 'provate', 'perfetto', 'salvate'],
                'pt': ['cliquem', 'abram', 'digitem', 'tentem', 'perfeito', 'salvem'],
                'ru': ['нажмите', 'откройте', 'наберите', 'попробуйте', 'отлично', 'сохраните'],
                'zh-CN': ['点击', '打开', '输入', '试试', '完美', '保存'],
                'ja': ['クリック', '開く', '入力', '試す', '完璧', '保存'],
                'ar': ['انقروا', 'افتحوا', 'اكتبوا', 'جربوا', 'مثالي', 'احفظوا'],
                'uk': ['натисніть', 'відкрийте', 'введіть', 'спробуйте', 'ідеально', 'збережіть'],
                'fa': ['کلیک کنید', 'باز کنید', 'تایپ کنید', 'امتحان کنید', 'عالی', 'ذخیره کنید'],
                'hi': ['क्लिक करें', 'खोलें', 'टाइप करें', 'कोशिश करें', 'बेहतरीन', 'सेव करें'],
                'bn': ['ক্লিক করুন', 'খুলুন', 'টাইপ করুন', 'চেষ্টা করুন', 'নিখুঁত', 'সেভ করুন'],
                'te': ['క్లిక్ చేయండి', 'తెరవండి', 'టైప్ చేయండి', 'ప্রयত్নించండి', 'అద్భুতం', 'సేవ్ చেయండి'],
                'mr': ['क्लिक करा', 'उघडा', 'टाइप करा', 'प्रयत्न करा', 'उत्तम', 'सेव्ह करा']
            },
            'emotions': {
                'fr': ['super', 'génial', 'parfait', 'excellent', 'bravo', 'dommage', 'pas grave'],
                'en': ['great', 'awesome', 'perfect', 'excellent', 'well done', 'too bad', 'no problem'],
                'es': ['genial', 'increíble', 'perfecto', 'excelente', 'muy bien', 'qué pena', 'no hay problema'],
                'de': ['toll', 'fantastisch', 'perfekt', 'ausgezeichnet', 'gut gemacht', 'schade', 'kein problem'],
                'it': ['fantastico', 'incredibile', 'perfetto', 'eccellente', 'bravo', 'peccato', 'non c\'è problema'],
                'pt': ['ótimo', 'incrível', 'perfeito', 'excelente', 'muito bem', 'que pena', 'sem problema'],
                'ru': ['отлично', 'потрясающе', 'идеально', 'превосходно', 'молодец', 'жаль', 'не проблема'],
                'zh-CN': ['太好了', '令人惊叹', '完美', '优秀', '做得好', '可惜', '没问题'],
                'ja': ['素晴らしい', '驚くべき', '完璧', '優秀', 'よくできました', '残念', '問題ない'],
                'ar': ['رائع', 'مذهل', 'مثالي', 'ممتاز', 'أحسنت', 'يا للأسف', 'لا مشكلة'],
                'uk': ['чудово', 'дивовижно', 'ідеально', 'відмінно', 'молодець', 'шкода', 'без проблем'],
                'fa': ['عالی', 'شگفت‌انگیز', 'کامل', 'عالی', 'آفرین', 'حیف', 'مشکلی نیست'],
                'hi': ['शानदार', 'अद्भुत', 'परफेक्ट', 'बेहतरीन', 'शाबाش', 'अफसोस', 'कोई समस्या नहीं'],
                'bn': ['দুর্দান্ত', 'আশ্চর্যজনক', 'নিখুঁত', 'চমৎকার', 'বাহবা', 'দুঃখজনক', 'কোন সমস্যা নেই'],
                'te': ['అద্भুতं', 'ఆశ্চর্যকরমైன', 'పরিপূর্ణমైన', 'అద్ভুతমైన', 'బాగా చేసারు', 'దুরదృষ্টম', 'সমস্যা লেদু'],
                'mr': ['उत्तम', 'आश्चर्यकारक', 'परिपूर्ण', 'उत्कृष्ट', 'शाब्बास', 'खेद', 'समस्या नाही']
            }
        }
        
        # Initialiser systèmes
        self.init_counters()
        self.init_smart_cache()
    
    def normalize_text_for_cache(self, text):
        """Normalise le texte pour la recherche en cache"""
        if not text:
            return ""
        
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def get_room_cache(self, room_id):
        """Récupère ou crée le cache pour une room spécifique"""
        if room_id not in self.room_caches:
            self.room_caches[room_id] = {}
        return self.room_caches[room_id]
    
    def get_room_phrase_frequency(self, room_id):
        """Récupère ou crée le compteur de fréquence pour une room"""
        if room_id not in self.room_phrase_frequency:
            self.room_phrase_frequency[room_id] = {}
        return self.room_phrase_frequency[room_id]
    
    def translate(self, text, source_lang, target_lang='fr', forced_mode=None, room_id=None):
        """TRADUCTION SIMPLE ET FIABLE - Cache pour phrases complètes uniquement"""
        if not text or text.strip() == "":
            return ""
        
        if source_lang != 'auto':
            self.set_preferred_language(source_lang)
        
        print(f"TRADUCTION: '{text}' ({source_lang} → {target_lang})")
        
        # 1. Vérifier cache room pour phrase complète
        if room_id:
            room_cached = self.check_room_cache_only(text, source_lang, target_lang, room_id)
            if room_cached:
                print(f"CACHE ROOM: '{text}' → '{room_cached}'")
                return room_cached
        
        # 2. Vérifier cache professionnel pour phrase complète
        prof_cached = self.check_professional_cache(text, source_lang, target_lang)
        if prof_cached:
            print(f"CACHE PROFESSIONNEL: '{text}' → '{prof_cached}'")
            # Sauvegarder dans cache room
            if room_id:
                self.add_to_cache(text, source_lang, target_lang, prof_cached, room_id)
            return prof_cached
        
        # 3. Sinon : traduction par services (cohérence garantie)
        print(f"Traduction par services (phrase complète)")
        
        # Détection du domaine
        domain_analysis = self.domain_detector.detect_domain(text, source_lang, forced_mode)
        translation_mode = domain_analysis['mode']
        
        if 'warning' in domain_analysis:
            print(domain_analysis['warning'])
        elif 'info' in domain_analysis:
            print(domain_analysis['info'])
        
        # Services de traduction
        available_services = self.get_available_services()
        
        if 'deepl' in available_services and not self.can_use_deepl(source_lang, target_lang):
            available_services.remove('deepl')
            print(f"DeepL retiré (langues {source_lang}->{target_lang} non supportées)")
        
        print(f"Traduction avec {len(available_services)} services: {available_services}")
        print(f"Mode: {translation_mode.upper()} (domaine: {domain_analysis['domain']})")
        
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
                    
                    print(f"RÉSULTAT de {used_service} en {elapsed:.2f}s: '{translation}'")
                    
                    # Post-traitement et cache
                    translation = self.post_process_translation(translation, target_lang)
                    
                    # Sauvegarder dans cache room
                    if room_id:
                        self.add_to_cache(text, source_lang, target_lang, translation, room_id)
                    
                    return translation
                    
                except Exception as e:
                    print(f"Échec {service}: {str(e)}")
                    continue
        
        return f"Erreur de traduction: tous les services ont échoué"
    
    def check_professional_cache(self, text, source_lang, target_lang):
        """Vérifier cache professionnel pour phrase complète"""
        prof_cache = self.get_professional_cache()
        text_normalized = self.normalize_text_for_cache(text)
        
        # Stratégies de recherche (phrases complètes uniquement)
        search_strategies = [
            f"{text_normalized}|{source_lang}|{target_lang}",
            f"{text_normalized}|auto|{target_lang}",
        ]
        
        # Si source_lang est 'auto', essayer langues communes
        if source_lang == 'auto':
            common_langs = ['fr', 'en', 'es', 'de', 'it', 'pt', 'ru', 'zh-CN', 'ja', 'ar']
            for lang in common_langs:
                search_strategies.append(f"{text_normalized}|{lang}|{target_lang}")
        
        # Rechercher dans le cache professionnel
        for strategy_key in search_strategies:
            if strategy_key in prof_cache:
                base_translation = prof_cache[strategy_key]['translation']
                final_translation = self.restore_punctuation(text, base_translation, source_lang, target_lang)
                return final_translation
        
        return None
    
    def check_room_cache_only(self, text, source_lang, target_lang, room_id):
        """Vérifie seulement le cache de la room (phrases complètes)"""
        text_normalized = self.normalize_text_for_cache(text)
        room_cache = self.get_room_cache(room_id)
        
        exact_key = f"{text_normalized}|{source_lang}|{target_lang}"
        if exact_key in room_cache:
            stored_data = room_cache[exact_key]
            
            if 'original_text' in stored_data and 'original_translation' in stored_data:
                final_translation = self.restore_punctuation(text, stored_data['original_translation'], source_lang, target_lang)
            else:
                base_translation = stored_data['translation']
                final_translation = self.restore_punctuation(text, base_translation, source_lang, target_lang)
            
            return final_translation
        
        return None
    
    def restore_punctuation(self, original_text, base_translation, source_lang, target_lang):
        """Restaure la ponctuation du texte original sur la traduction"""
        original_normalized = self.normalize_text_for_cache(original_text)
        if original_text.lower().strip() == original_normalized:
            return base_translation
        
        # Extraire la ponctuation de fin
        end_punctuation = re.findall(r'[.!?]+\s*$', original_text)
        end_punct = end_punctuation[0] if end_punctuation else ''
        
        if end_punct:
            base_clean = re.sub(r'[.!?]+\s*$', '', base_translation).strip()
            final_translation = base_clean + end_punct
        else:
            final_translation = base_translation
        
        # Capitaliser le premier mot si l'original était capitalisé
        if original_text and original_text[0].isupper() and final_translation:
            final_translation = final_translation[0].upper() + final_translation[1:] if len(final_translation) > 1 else final_translation.upper()
        
        return final_translation

    def add_to_cache(self, text, source_lang, target_lang, translation, room_id=None):
        """Ajoute une traduction au cache (phrases complètes uniquement)"""
        text_normalized = self.normalize_text_for_cache(text)
        
        # Ajouter au cache de la room si room_id fourni
        if room_id:
            room_cache = self.get_room_cache(room_id)
            room_freq = self.get_room_phrase_frequency(room_id)
            
            # Mettre à jour fréquence
            room_freq[text_normalized] = room_freq.get(text_normalized, 0) + 1
            frequency = room_freq[text_normalized]
            
            # Déterminer niveau de confiance
            if frequency >= 5:
                confidence = 'frequent'
            elif frequency >= 2:
                confidence = 'common'
            else:
                confidence = 'single'
            
            cache_key = f"{text_normalized}|{source_lang}|{target_lang}"
            
            room_cache[cache_key] = {
                'translation': translation,
                'original_text': text,
                'original_translation': translation,
                'normalized_text': text_normalized,
                'confidence': confidence,
                'frequency': frequency,
                'timestamp': time.time()
            }
            
            print(f"Ajouté au cache room {room_id}: '{text}' → '{translation}' (freq: {frequency})")
            
            # Nettoyer si trop grand
            if len(room_cache) > self.max_smart_cache_size:
                self.cleanup_room_cache(room_id)
        
        # Ajouter aussi au cache ancien pour compatibilité
        old_key = f"{text_normalized}|{source_lang}|{target_lang}"
        if len(self.translation_cache) < self.max_cache_size:
            self.translation_cache[old_key] = translation

    def cleanup_room_cache(self, room_id):
        """Nettoie le cache d'une room en gardant les plus utiles"""
        room_cache = self.get_room_cache(room_id)
        
        priority_order = ['professional', 'frequent', 'common', 'fragment', 'single']
        
        sorted_cache = []
        for key, value in room_cache.items():
            confidence = value.get('confidence', 'single')
            priority = priority_order.index(confidence) if confidence in priority_order else 999
            sorted_cache.append((priority, key, value))
        
        sorted_cache.sort(key=lambda x: x[0])
        
        # Garder les meilleurs
        room_cache.clear()
        for priority, key, value in sorted_cache[:self.max_smart_cache_size]:
            room_cache[key] = value
        
        print(f"Cache room {room_id} nettoyé: {len(room_cache)} entrées conservées")
    
    def get_cache_stats(self, room_id=None):
        """Retourne statistiques cache pour une room"""
        if room_id and room_id in self.room_caches:
            room_cache = self.room_caches[room_id]
            total = len(room_cache)
            
            stats = {'total': total}
            for confidence in ['professional', 'frequent', 'common', 'fragment', 'single']:
                count = sum(1 for v in room_cache.values() if v.get('confidence') == confidence)
                stats[confidence] = count
            
            return stats
        
        return {'total': 0}
    
    def get_professional_cache(self):
        """Retourne le cache professionnel (global, pas par room)"""
        if not hasattr(self, '_professional_cache'):
            self._professional_cache = {}
            self.preload_professional_cache()
        return self._professional_cache
    
    def init_smart_cache(self):
        """Initialise le cache intelligent"""
        smart_cache_file = "room_caches.json"
        
        if os.path.exists(smart_cache_file):
            try:
                with open(smart_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.room_caches = cache_data.get('room_caches', {})
                    self.room_phrase_frequency = cache_data.get('room_phrase_frequency', {})
                    print(f"Caches rooms chargés: {len(self.room_caches)} rooms")
            except Exception as e:
                print(f"Erreur chargement caches rooms: {e}")
        
        # Initialiser cache professionnel
        self.preload_professional_cache()
    
    def preload_professional_cache(self):
        """Cache bidirectionnel SIMPLIFIÉ - Mots/phrases simples uniquement"""
        if not hasattr(self, '_professional_cache'):
            self._professional_cache = {}
        
        print("Création du cache bidirectionnel SIMPLIFIÉ...")
        
        for sector, languages in self.professional_phrases.items():
            # Pour chaque phrase dans chaque secteur
            for source_lang, source_phrases in languages.items():
                for i, source_phrase in enumerate(source_phrases):
                    source_normalized = self.normalize_text_for_cache(source_phrase)
                    
                    # Traduire vers TOUTES les autres langues
                    for target_lang, target_phrases in languages.items():
                        if target_lang != source_lang and i < len(target_phrases):
                            target_phrase = target_phrases[i]
                            
                            # Créer les clés dans TOUTES les directions possibles
                            cache_keys = [
                                f"{source_normalized}|{source_lang}|{target_lang}",
                                f"{source_normalized}|auto|{target_lang}",
                            ]
                            
                            for cache_key in cache_keys:
                                self._professional_cache[cache_key] = {
                                    'translation': target_phrase,
                                    'confidence': 'professional',
                                    'sector': sector,
                                    'source_phrase': source_phrase,
                                    'timestamp': time.time()
                                }
        
        total_entries = len(self._professional_cache)
        print(f"Cache bidirectionnel SIMPLIFIÉ créé: {total_entries} correspondances")
        
        # Tests de vérification
        test_words = [
            ("bonjour", "fr", "en"),
            ("hello", "en", "fr"), 
            ("hola", "es", "fr"),
            ("merci", "fr", "en"),
            ("thank you", "en", "fr"),
            ("super", "fr", "en"),
            ("perfect", "en", "fr")
        ]
        
        print("Tests du cache bidirectionnel SIMPLIFIÉ:")
        for word, src, tgt in test_words:
            word_norm = self.normalize_text_for_cache(word)
            test_key = f"{word_norm}|{src}|{tgt}"
            if test_key in self._professional_cache:
                result = self._professional_cache[test_key]['translation']
                print(f"   ✅ {word} ({src}→{tgt}) = {result}")
            else:
                print(f"   ❌ {word} ({src}→{tgt}) = NON TROUVÉ")
    
    def save_smart_cache(self):
        """Sauvegarde les caches des rooms"""
        try:
            cache_data = {
                'room_caches': self.room_caches,
                'room_phrase_frequency': self.room_phrase_frequency,
                'last_update': time.time()
            }
            
            with open("room_caches.json", 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erreur sauvegarde caches rooms: {e}")
    
    # FONCTIONS EXISTANTES CONSERVÉES
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
