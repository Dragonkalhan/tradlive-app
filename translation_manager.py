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
                    'te': ['రోగి', 'నిర్ధారణ', 'లక్షణం', 'వ్యాధి', 'మందు', 'చికిత్స', 'నొప্పি', 'జ్వరం', 'సలహా', 'ప్రిస్క్రిప్షన్', 'అలెర్జీ', 'ఇన్ఫెక్షన్', 'శస్త్రచికిత్స', 'అత్యవసర', 'ఆసుపత్రి', 'నొప్పి', 'బాధ'],
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
                    'te': ['పెట్టుబడి', 'క్రెడిట్', 'రుణం', 'భీమా', 'తనఖా', 'పెట్టుబడి', 'పొదుపు', 'పన్ను', 'బ్యాంక్', 'ఖాతా'],
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
        """🧠 Détecte le domaine et recommande un mode de traduction"""
        
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
                    'warning': f"⚠️ Domaine {domain_name} détecté - Mode précision activé"
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
                    'info': f"🚀 {domain_name} détecté - Mode rapide activé"
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
        
        # 🆕 CACHE ISOLÉ PAR ROOM (au lieu de global)
        self.room_caches = {}           # {room_id: {cache_data}}
        self.room_phrase_frequency = {} # {room_id: {phrase: count}}
        self.translation_cache = {}     # Cache ancien conservé pour compatibilité
        
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
        
        # 🆕 BIBLIOTHÈQUES PROFESSIONNELLES ÉTENDUES (16 LANGUES)
        self.professional_phrases = {
            'accueil': {
                'fr': ['bonjour', 'bonsoir', 'puis-je vous aider', 'merci', 'au revoir', 'de rien', 'excusez-moi', 'pardon', 'comment allez-vous', 'très bien merci'],
                'en': ['hello', 'good evening', 'can I help you', 'thank you', 'goodbye', 'you\'re welcome', 'excuse me', 'sorry', 'how are you', 'very well thank you'],
                'es': ['hola', 'buenas tardes', 'puedo ayudarle', 'gracias', 'adiós', 'de nada', 'disculpe', 'perdón', 'cómo está usted', 'muy bien gracias'],
                'de': ['hallo', 'guten abend', 'kann ich ihnen helfen', 'danke', 'auf wiedersehen', 'gern geschehen', 'entschuldigung', 'verzeihung', 'wie geht es ihnen', 'sehr gut danke'],
                'it': ['ciao', 'buonasera', 'posso aiutarla', 'grazie', 'arrivederci', 'prego', 'mi scusi', 'scusi', 'come sta', 'molto bene grazie'],
                'pt': ['olá', 'boa tarde', 'posso ajudá-lo', 'obrigado', 'tchau', 'de nada', 'com licença', 'desculpe', 'como está', 'muito bem obrigado'],
                'ru': ['привет', 'добрый вечер', 'могу ли я помочь', 'спасибо', 'до свидания', 'пожалуйста', 'извините', 'простите', 'как дела', 'очень хорошо спасибо'],
                'zh-CN': ['你好', '晚上好', '我可以帮助您吗', '谢谢', '再见', '不客气', '对不起', '抱歉', '您好吗', '很好谢谢'],
                'ja': ['こんにちは', 'こんばんは', 'お手伝いできますか', 'ありがとう', 'さようなら', 'どういたしまして', 'すみません', 'ごめんなさい', 'お元気ですか', 'とても元気です'],
                'ar': ['مرحبا', 'مساء الخير', 'هل يمكنني مساعدتك', 'شكرا', 'وداعا', 'عفوا', 'معذرة', 'آسف', 'كيف حالك', 'بخير شكرا'],
                'uk': ['привіт', 'добрий вечір', 'чи можу допомогти', 'дякую', 'до побачення', 'будь ласка', 'вибачте', 'пробачте', 'як справи', 'дуже добре дякую'],
                'fa': ['سلام', 'عصر بخیر', 'می‌توانم کمک کنم', 'متشکرم', 'خداحافظ', 'خواهش می‌کنم', 'ببخشید', 'شرمنده', 'حالتان چطور است', 'خیلی خوب متشکرم'],
                'hi': ['नमस्ते', 'शुभ संध्या', 'क्या मैं मदद कर सकता हूं', 'धन्यवाद', 'अलविदा', 'कृपया', 'माफ करें', 'क्षमा करें', 'आप कैसे हैं', 'बहुत अच्छा धन्यवाद'],
                'bn': ['নমস্কার', 'শুভ সন্ধ্যা', 'আমি কি সাহায্য করতে পারি', 'ধন্যবাদ', 'বিদায়', 'অনুগ্রহ করে', 'ক্ষমা করুন', 'দুঃখিত', 'আপনি কেমন আছেন', 'খুব ভাল ধন্যবাদ'],
                'te': ['నమస్కారం', 'శుభ సాయంత్రం', 'నేను సహాయం చేయగలనా', 'ధన్యవాదాలు', 'వీడ్కోలు', 'దయచేసి', 'క్షమించండి', 'కేవలం', 'మీరు ఎలా ఉన్నారు', 'చాలా బాగా ధన్యవాదాలు'],
                'mr': ['नमस्कार', 'शुभ संध्याकाळ', 'मी मदत करू शकतो का', 'धन्यवाद', 'निरोप', 'कृपया', 'माफ करा', 'क्षमा करा', 'तुम्ही कसे आहात', 'खूप चांगले धन्यवाद']
            },
            'numerique': {
                'fr': ['cliquez', 'ouvrez', 'tapez', 'avez-vous compris', 'essayez', 'parfait', 'recommencez', 'sauvegardez'],
                'en': ['click', 'open', 'type', 'do you understand', 'try', 'perfect', 'try again', 'save'],
                'es': ['hagan clic', 'abran', 'escriban', 'han entendido', 'prueben', 'perfecto', 'inténtenlo', 'guarden'],
                'de': ['klicken', 'öffnen', 'geben sie ein', 'haben sie verstanden', 'versuchen', 'perfekt', 'nochmal', 'speichern'],
                'it': ['cliccate', 'aprite', 'digitate', 'avete capito', 'provate', 'perfetto', 'riprovate', 'salvate'],
                'pt': ['cliquem', 'abram', 'digitem', 'entenderam', 'tentem', 'perfeito', 'novamente', 'salvem'],
                'ru': ['нажмите', 'откройте', 'наберите', 'поняли ли вы', 'попробуйте', 'отлично', 'попробуйте снова', 'сохраните'],
                'zh-CN': ['点击', '打开', '输入', '您明白了吗', '试试', '完美', '再试', '保存'],
                'ja': ['クリック', '開く', '入力', '理解しましたか', '試す', '完璧', 'もう一度', '保存'],
                'ar': ['انقروا', 'افتحوا', 'اكتبوا', 'هل فهمتم', 'جربوا', 'مثالي', 'مرة أخرى', 'احفظوا'],
                'uk': ['натисніть', 'відкрийте', 'введіть', 'ви зрозуміли', 'спробуйте', 'ідеально', 'спробуйте знову', 'збережіть'],
                'fa': ['کلیک کنید', 'باز کنید', 'تایپ کنید', 'متوجه شدید', 'امتحان کنید', 'عالی', 'دوباره امتحان کنید', 'ذخیره کنید'],
                'hi': ['क्लिक करें', 'खोलें', 'टाइप करें', 'क्या आप समझे', 'कोशिश करें', 'बेहतरीन', 'फिर कोशिश करें', 'सेव करें'],
                'bn': ['ক্লিক করুন', 'খুলুন', 'টাইপ করুন', 'আপনি বুঝেছেন', 'চেষ্টা করুন', 'নিখুঁত', 'আবার চেষ্টা করুন', 'সেভ করুন'],
                'te': ['క్లిక్ చేయండి', 'తెరవండి', 'టైప్ చేయండి', 'మీరు అర్థం చేసుకున్నారా', 'ప్రయత్నించండి', 'అద్భుతం', 'మళ్లీ ప్రయత్నించండి', 'సేవ్ చేయండి'],
                'mr': ['क्लिक करा', 'उघडा', 'टाइप करा', 'तुम्हाला समजले का', 'प्रयत्न करा', 'उत्तम', 'पुन्हा प्रयत्न करा', 'सेव्ह करा']
            },
            'vie_quotidienne': {
                'fr': ['comment ça va', 'ça va bien', 'très bien', 'pas mal', 'et vous', 'de rien', 'avec plaisir', 'bien sûr', 'peut-être', 'je ne sais pas', 'attendez', 'voilà', 'exactement', 'parfait', 'super'],
                'en': ['how are you', 'I am fine', 'very good', 'not bad', 'and you', 'you are welcome', 'with pleasure', 'of course', 'maybe', 'I do not know', 'wait', 'here it is', 'exactly', 'perfect', 'great'],
                'es': ['cómo estás', 'estoy bien', 'muy bien', 'no está mal', 'y tú', 'de nada', 'con mucho gusto', 'por supuesto', 'tal vez', 'no lo sé', 'espera', 'aquí está', 'exactamente', 'perfecto', 'genial'],
                'de': ['wie geht es dir', 'mir geht es gut', 'sehr gut', 'nicht schlecht', 'und dir', 'gern geschehen', 'gerne', 'natürlich', 'vielleicht', 'ich weiß nicht', 'warte', 'hier ist es', 'genau', 'perfekt', 'toll'],
                'it': ['come stai', 'sto bene', 'molto bene', 'non male', 'e tu', 'prego', 'con piacere', 'certo', 'forse', 'non lo so', 'aspetta', 'ecco', 'esatto', 'perfetto', 'fantastico'],
                'pt': ['como está', 'estou bem', 'muito bem', 'não está mal', 'e você', 'de nada', 'com prazer', 'claro', 'talvez', 'não sei', 'espere', 'aqui está', 'exatamente', 'perfeito', 'ótimo'],
                'ru': ['как дела', 'у меня всё хорошо', 'очень хорошо', 'неплохо', 'а у тебя', 'пожалуйста', 'с удовольствием', 'конечно', 'может быть', 'я не знаю', 'подожди', 'вот', 'точно', 'отлично', 'супер'],
                'zh-CN': ['你好吗', '我很好', '非常好', '还不错', '你呢', '不客气', '乐意效劳', '当然', '也许', '我不知道', '等等', '这里', '正确', '完美', '太好了'],
                'ja': ['元気ですか', '元気です', 'とても良い', '悪くない', 'あなたは', 'どういたしまして', '喜んで', 'もちろん', 'たぶん', 'わかりません', '待って', 'ここです', 'その通り', '完璧', 'すばらしい'],
                'ar': ['كيف حالك', 'أنا بخير', 'جيد جدا', 'ليس سيئا', 'وأنت', 'عفوا', 'بكل سرور', 'بالطبع', 'ربما', 'لا أعرف', 'انتظر', 'هنا', 'بالضبط', 'مثالي', 'رائع'],
                'uk': ['як справи', 'у мене все добре', 'дуже добре', 'непогано', 'а в тебе', 'будь ласка', 'з задоволенням', 'звичайно', 'можливо', 'я не знаю', 'зачекай', 'ось', 'точно', 'відмінно', 'супер'],
                'fa': ['حالت چطوره', 'من خوبم', 'خیلی خوب', 'بد نیست', 'تو چطور', 'خواهش می‌کنم', 'با کمال میل', 'البته', 'شاید', 'نمی‌دانم', 'صبر کن', 'اینجاست', 'دقیقا', 'عالی', 'فوق‌العاده'],
                'hi': ['कैसे हो', 'मैं ठीक हूं', 'बहुत अच्छा', 'बुरा नहीं', 'और आप', 'कृपया', 'खुशी से', 'जरूर', 'शायद', 'मुझे नहीं पता', 'रुको', 'यहां है', 'बिल्कुल', 'बेहतरीन', 'शानदार'],
                'bn': ['কেমন আছেন', 'আমি ভাল আছি', 'খুব ভাল', 'খারাপ নয়', 'আর আপনি', 'অনুগ্রহ করে', 'আনন্দের সাথে', 'অবশ্যই', 'হয়তো', 'আমি জানি না', 'অপেক্ষা করুন', 'এখানে', 'ঠিক', 'নিখুঁত', 'দুর্দান্ত'],
                'te': ['ఎలా ఉన్నారు', 'నేను బాగున్నాను', 'చాలా బాగుంది', 'చెడ్డది కాదు', 'మీరు ఎలా', 'దయచేసి', 'ఆనందంగా', 'అవును', 'బహుశా', 'నాకు తెలియదు', 'వేచి ఉండండి', 'ఇక్కడ ఉంది', 'సరిగ్గా', 'అద్భుతం', 'గొప్పది'],
                'mr': ['कसे आहात', 'मी ठीक आहे', 'खूप चांगले', 'वाईट नाही', 'आणि तुम्ही', 'कृपया', 'आनंदाने', 'नक्कीच', 'कदाचित', 'मला माहित नाही', 'थांबा', 'इथे आहे', 'नक्की', 'परिपूर्ण', 'उत्तम']
            },
            'emotions_reactions': {
                'fr': ['super', 'génial', 'parfait', 'excellent', 'bravo', 'félicitations', 'dommage', 'tant pis', 'pas grave', 'ça arrive', 'oh là là', 'incroyable', 'formidable', 'magnifique', 'impressionnant'],
                'en': ['great', 'awesome', 'perfect', 'excellent', 'well done', 'congratulations', 'too bad', 'never mind', 'no problem', 'it happens', 'oh my', 'incredible', 'wonderful', 'beautiful', 'impressive'],
                'es': ['genial', 'increíble', 'perfecto', 'excelente', 'muy bien', 'felicitaciones', 'qué pena', 'no importa', 'no hay problema', 'pasa', 'dios mío', 'increíble', 'maravilloso', 'hermoso', 'impresionante'],
                'de': ['toll', 'fantastisch', 'perfekt', 'ausgezeichnet', 'gut gemacht', 'herzlichen glückwunsch', 'schade', 'macht nichts', 'kein problem', 'passiert', 'ach so', 'unglaublich', 'wunderbar', 'schön', 'beeindruckend'],
                'it': ['fantastico', 'incredibile', 'perfetto', 'eccellente', 'bravo', 'congratulazioni', 'peccato', 'non importa', 'non c\'è problema', 'capita', 'mamma mia', 'incredibile', 'meraviglioso', 'bellissimo', 'impressionante'],
                'pt': ['ótimo', 'incrível', 'perfeito', 'excelente', 'muito bem', 'parabéns', 'que pena', 'não importa', 'sem problema', 'acontece', 'nossa', 'incrível', 'maravilhoso', 'lindo', 'impressionante'],
                'ru': ['отлично', 'потрясающе', 'идеально', 'превосходно', 'молодец', 'поздравляю', 'жаль', 'неважно', 'не проблема', 'бывает', 'боже мой', 'невероятно', 'замечательно', 'красиво', 'впечатляюще'],
                'zh-CN': ['太好了', '令人惊叹', '完美', '优秀', '做得好', '恭喜', '可惜', '没关系', '没问题', '会发生', '天哪', '难以置信', '精彩', '美丽', '令人印象深刻'],
                'ja': ['素晴らしい', '驚くべき', '完璧', '優秀', 'よくできました', 'おめでとう', '残念', '大丈夫', '問題ない', 'よくある', 'すごい', '信じられない', '素晴らしい', '美しい', '印象的'],
                'ar': ['رائع', 'مذهل', 'مثالي', 'ممتاز', 'أحسنت', 'تهانينا', 'يا للأسف', 'لا يهم', 'لا مشكلة', 'يحدث', 'يا إلهي', 'لا يصدق', 'رائع', 'جميل', 'مثير للإعجاب'],
                'uk': ['чудово', 'дивовижно', 'ідеально', 'відмінно', 'молодець', 'вітаю', 'шкода', 'неважливо', 'без проблем', 'буває', 'боже мій', 'неймовірно', 'чудово', 'гарно', 'вражає'],
                'fa': ['عالی', 'شگفت‌انگیز', 'کامل', 'عالی', 'آفرین', 'تبریک', 'حیف', 'مهم نیست', 'مشکلی نیست', 'اتفاق می‌افتد', 'خدای من', 'باورنکردنی', 'فوق‌العاده', 'زیبا', 'چشمگیر'],
                'hi': ['शानदार', 'अद्भुत', 'परफेक्ट', 'बेहतरीन', 'शाबाश', 'बधाई', 'अफसोस', 'कोई बात नहीं', 'कोई समस्या नहीं', 'होता है', 'हे भगवान', 'अविश्वसनीय', 'अद्भुत', 'सुंदर', 'प्रभावशाली'],
                'bn': ['দুর্দান্ত', 'আশ্চর্যজনক', 'নিখুঁত', 'চমৎকার', 'বাহবা', 'অভিনন্দন', 'দুঃখজনক', 'কিছু না', 'কোন সমস্যা নেই', 'হয়', 'হে ভগবান', 'অবিশ্বাস্য', 'চমৎকার', 'সুন্দর', 'চিত্তাকর্ষক'],
                'te': ['అద్భుతం', 'ఆశ్చర్యకరమైన', 'పరిపూర్ణమైన', 'అద్భుతమైన', 'బాగా చేసారు', 'అభినందనలు', 'దురదృష్టం', 'పర్వాలేదు', 'సమస్య లేదు', 'జరుగుతుంది', 'దేవుడా', 'నమ్మశక్యం కాని', 'అద్భుతమైన', 'అందమైన', 'ఆకట్టుకునే'],
                'mr': ['उत्तम', 'आश्चर्यकारक', 'परिपूर्ण', 'उत्कृष्ट', 'शाब्बास', 'अभिनंदन', 'खेद', 'काही हरकत नाही', 'समस्या नाही', 'होते', 'देवा', 'अविश्वसनीय', 'अप्रतिम', 'सुंदर', 'प्रभावी']
            }
        }
        
        # Initialiser systèmes
        self.init_counters()
        self.init_smart_cache()
    
    # 🆕 NORMALISATION AUTOMATIQUE DU TEXTE
    def normalize_text_for_cache(self, text):
        """Normalise le texte pour la recherche en cache (gère ponctuation, majuscules, etc.)"""
        if not text:
            return ""
        
        # Minuscules
        text = text.lower()
        
        # Supprimer ponctuation et caractères spéciaux
        text = re.sub(r'[^\w\s]', '', text)
        
        # Supprimer espaces multiples et trim
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    # 🆕 CACHE PAR ROOM (ISOLATION CLIENT)
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
    
    # FONCTION PRINCIPALE DE TRADUCTION
    def translate(self, text, source_lang, target_lang='fr', forced_mode=None, room_id=None):
        """Traduit avec détection intelligente de domaine + cache isolé par room"""
        if not text or text.strip() == "":
            return ""
        
        if source_lang != 'auto':
            self.set_preferred_language(source_lang)
        
        # Détection du domaine
        domain_analysis = self.domain_detector.detect_domain(text, source_lang, forced_mode)
        translation_mode = domain_analysis['mode']
        
        if 'warning' in domain_analysis:
            print(domain_analysis['warning'])
        elif 'info' in domain_analysis:
            print(domain_analysis['info'])
        
        # Vérifier le cache (avec room_id pour isolation)
        cached_translation = self.check_cache(text, source_lang, target_lang, room_id)
        if cached_translation:
            print(f"⚡ Traduction trouvée dans le cache ! (Mode: {translation_mode})")
            return cached_translation
        
        # Obtenir services disponibles
        available_services = self.get_available_services()
        
        if 'deepl' in available_services and not self.can_use_deepl(source_lang, target_lang):
            available_services.remove('deepl')
            print(f"ℹ️ DeepL retiré (langues {source_lang}->{target_lang} non supportées)")
        
        print(f"🚀 Traduction PARALLÈLE avec {len(available_services)} services: {available_services}")
        print(f"🧠 Mode détecté: {translation_mode.upper()} (domaine: {domain_analysis['domain']})")
        
        # Stats cache
        cache_stats = self.get_cache_stats(room_id)
        print(f"📊 Cache room {room_id}: {cache_stats['total']} entrées")
        
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
                    
                    print(f"✅ PREMIER résultat reçu de {used_service} en {elapsed:.2f}s (Mode: {translation_mode})")
                    
                    # Post-traitement et cache
                    translation = self.post_process_translation(translation, target_lang)
                    self.add_to_cache(text, source_lang, target_lang, translation, room_id)
                    
                    return translation
                    
                except Exception as e:
                    print(f"❌ Échec {service}: {str(e)}")
                    continue
        
        return f"Erreur de traduction: tous les services ont échoué"
    
    def check_cache(self, text, source_lang, target_lang, room_id=None):
        """Vérifie le cache intelligent avec normalisation pour recherche mais préservation ponctuation"""
        # Normaliser SEULEMENT pour la recherche
        text_normalized = self.normalize_text_for_cache(text)
        
        print(f"🔍 CACHE DEBUG: '{text}' → normalisé pour recherche: '{text_normalized}'")
        
        # 1. Cache professionnel global (priorité max)
        prof_cache = self.get_professional_cache()
        prof_key = f"{text_normalized}|{source_lang}|{target_lang}"
        
        if prof_key in prof_cache:
            # NOUVEAU : Reconstruire la ponctuation sur la traduction
            base_translation = prof_cache[prof_key]['translation']
            final_translation = self.restore_punctuation(text, base_translation, source_lang, target_lang)
            print(f"✅ CACHE HIT professionnel: {prof_key} → '{final_translation}'")
            return final_translation
        
        # 2. Cache spécifique à la room
        if room_id:
            room_cache = self.get_room_cache(room_id)
            
            exact_key = f"{text_normalized}|{source_lang}|{target_lang}"
            if exact_key in room_cache:
                stored_data = room_cache[exact_key]
                
                # NOUVEAU : Si on a stocké la version originale, l'utiliser
                if 'original_text' in stored_data and 'original_translation' in stored_data:
                    final_translation = self.restore_punctuation(text, stored_data['original_translation'], source_lang, target_lang)
                else:
                    # Ancienne version : reconstruire la ponctuation
                    base_translation = stored_data['translation']
                    final_translation = self.restore_punctuation(text, base_translation, source_lang, target_lang)
                
                print(f"✅ CACHE HIT room: {exact_key} → '{final_translation}'")
                return final_translation
            
            # Vérifier fragments avec reconstruction ponctuation
            fragments = self.extract_fragments(text_normalized)
            for fragment in fragments:
                fragment_key = f"{fragment}|{source_lang}|{target_lang}"
                if fragment_key in room_cache:
                    confidence = room_cache[fragment_key].get('confidence', 'fragment')
                    if confidence in ['professional', 'frequent']:
                        base_translation = room_cache[fragment_key]['translation']
                        final_translation = self.restore_punctuation(text, base_translation, source_lang, target_lang)
                        print(f"✅ CACHE HIT fragment room: {fragment_key} → '{final_translation}'")
                        return final_translation
        
        # 3. Cache ancien pour compatibilité
        old_key = f"{text_normalized}|{source_lang}|{target_lang}"
        if old_key in self.translation_cache:
            base_translation = self.translation_cache[old_key]
            final_translation = self.restore_punctuation(text, base_translation, source_lang, target_lang)
            print(f"✅ CACHE HIT ancien: {old_key} → '{final_translation}'")
            return final_translation
        
        print(f"❌ CACHE MISS pour: {text_normalized}")
        return None

    def restore_punctuation(self, original_text, base_translation, source_lang, target_lang):
        """Restaure la ponctuation du texte original sur la traduction"""
        
        # Si le texte original n'a pas de ponctuation, retourner tel quel
        original_normalized = self.normalize_text_for_cache(original_text)
        if original_text.lower().strip() == original_normalized:
            return base_translation
        
        # Extraire la ponctuation du texte original
        import re
        
        # Trouver la ponctuation en fin de phrase
        end_punctuation = re.findall(r'[.!?]+\s*$', original_text)
        end_punct = end_punctuation[0] if end_punctuation else ''
        
        # Trouver les virgules et autres ponctuations intérieures
        # Pour simplifier, on garde la logique de base et on ajoute la ponctuation de fin
        
        # Si le texte original se termine par une ponctuation, l'ajouter à la traduction
        if end_punct:
            # Enlever la ponctuation existante de la traduction de base si elle existe
            base_clean = re.sub(r'[.!?]+\s*$', '', base_translation).strip()
            final_translation = base_clean + end_punct
        else:
            final_translation = base_translation
        
        # Capitaliser le premier mot si l'original était capitalisé
        if original_text and original_text[0].isupper() and final_translation:
            final_translation = final_translation[0].upper() + final_translation[1:] if len(final_translation) > 1 else final_translation.upper()
        
        return final_translation

    def add_to_cache(self, text, source_lang, target_lang, translation, room_id=None):
        """Ajoute une traduction au cache EN STOCKANT AUSSI LES VERSIONS ORIGINALES"""
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
            
            # NOUVEAU : Stocker à la fois la version normalisée ET les versions originales
            room_cache[cache_key] = {
                'translation': translation,  # Traduction complète avec ponctuation
                'original_text': text,       # Texte original avec ponctuation
                'original_translation': translation,  # Traduction originale avec ponctuation
                'normalized_text': text_normalized,   # Version normalisée pour recherche
                'confidence': confidence,
                'frequency': frequency,
                'timestamp': time.time()
            }
            
            print(f"💾 Ajouté au cache room {room_id}: '{text}' → '{translation}' (freq: {frequency})")
            
            # Nettoyer si trop grand
            if len(room_cache) > self.max_smart_cache_size:
                self.cleanup_room_cache(room_id)
        
        # Ajouter aussi au cache ancien pour compatibilité (avec traduction complète)
        old_key = f"{text_normalized}|{source_lang}|{target_lang}"
        if len(self.translation_cache) < self.max_cache_size:
            self.translation_cache[old_key] = translation  # Traduction complète avec ponctuation

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
        
        print(f"🧹 Cache room {room_id} nettoyé: {len(room_cache)} entrées conservées")
    
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
    
    # CACHE PROFESSIONNEL GLOBAL
    def get_professional_cache(self):
        """Retourne le cache professionnel (global, pas par room)"""
        if not hasattr(self, '_professional_cache'):
            self._professional_cache = {}
            self.preload_professional_cache()
        return self._professional_cache
    
    def init_smart_cache(self):
        """Initialise le cache intelligent"""
        # Charger caches de rooms existants
        smart_cache_file = "room_caches.json"
        
        if os.path.exists(smart_cache_file):
            try:
                with open(smart_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.room_caches = cache_data.get('room_caches', {})
                    self.room_phrase_frequency = cache_data.get('room_phrase_frequency', {})
                    print(f"✅ Caches rooms chargés: {len(self.room_caches)} rooms")
            except Exception as e:
                print(f"⚠️ Erreur chargement caches rooms: {e}")
        
        # Initialiser cache professionnel
        self.preload_professional_cache()
    
    def preload_professional_cache(self):
        """Pré-remplit le cache professionnel global"""
        if not hasattr(self, '_professional_cache'):
            self._professional_cache = {}
        
        for sector, languages in self.professional_phrases.items():
            for lang, phrases in languages.items():
                for phrase in phrases:
                    if lang == 'fr':
                        for target_lang, target_phrases in languages.items():
                            if target_lang != 'fr' and len(target_phrases) > phrases.index(phrase):
                                # Normaliser la phrase
                                phrase_normalized = self.normalize_text_for_cache(phrase)
                                cache_key = f"{phrase_normalized}|auto|{target_lang}"
                                translation = target_phrases[phrases.index(phrase)]
                                self._professional_cache[cache_key] = {
                                    'translation': translation,
                                    'confidence': 'professional',
                                    'sector': sector,
                                    'timestamp': time.time()
                                }
        
        print(f"🌍 Cache professionnel multilingue initialisé: {len(self._professional_cache)} phrases (16 langues x 4 secteurs)")
        
        # Test debug
        test_key = self.normalize_text_for_cache("bonjour") + "|auto|en"
        if test_key in self._professional_cache:
            print(f"   ✅ TROUVÉ: '{test_key}' -> '{self._professional_cache[test_key]['translation']}'")
        else:
            print(f"   ❌ PAS TROUVÉ: '{test_key}'")
    
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
            print(f"⚠️ Erreur sauvegarde caches rooms: {e}")
    
    # FONCTIONS UTILITAIRES
    def extract_fragments(self, text):
        """Extrait des fragments significatifs d'un texte"""
        words = text.split()
        fragments = []
        
        # Mots importants
        important_words = [word for word in words if len(word) > 2]
        fragments.extend(important_words)
        
        # Fragments 2-3 mots
        for i in range(len(words) - 1):
            fragments.append(' '.join(words[i:i+2]))
            if i < len(words) - 2:
                fragments.append(' '.join(words[i:i+3]))
        
        fragments.append(text)
        return fragments
    
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
