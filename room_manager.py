import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class User:
    def __init__(self, user_id: str, nickname: str, language: str, is_host: bool = False):
        self.user_id = user_id
        self.nickname = nickname
        self.language = language
        self.is_host = is_host
        self.joined_at = datetime.now()
        self.last_activity = datetime.now()
    
    def update_activity(self):
        """Met à jour l'activité de l'utilisateur"""
        self.last_activity = datetime.now()
    
    def to_dict(self):
        """Convertit l'utilisateur en dictionnaire pour JSON"""
        return {
            'user_id': self.user_id,
            'nickname': self.nickname,
            'language': self.language,
            'is_host': self.is_host,
            'joined_at': self.joined_at.isoformat(),
            'last_activity': self.last_activity.isoformat()
        }

class Room:
    def __init__(self, room_id: str, host_id: str, room_name: str, password: str = None):
        self.room_id = room_id
        self.host_id = host_id
        self.room_name = room_name
        self.password = password
        self.created_at = datetime.now()
        self.users: Dict[str, User] = {}
        self.last_translation = {
            'original': '',
            'translated': {},  # {language: translation}
            'timestamp': datetime.now(),
            'source_language': 'fr',  # Langue source du message
            'enable_speech': False,    # Si la synthèse vocale doit être activée
            'sender_id': None         # ID de l'utilisateur qui a envoyé le message
        }
    
    def add_user(self, user: User) -> bool:
        """Ajoute un utilisateur à la salle"""
        if len(self.users) >= 10:  # Limite de 10 utilisateurs par salle
            return False
        
        self.users[user.user_id] = user
        print(f"👤 {user.nickname} ({user.language}) a rejoint la salle {self.room_name}")
        return True
    
    def remove_user(self, user_id: str) -> Optional[User]:
        """Supprime un utilisateur de la salle"""
        user = self.users.pop(user_id, None)
        if user:
            print(f"👋 {user.nickname} a quitté la salle {self.room_name}")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Récupère un utilisateur par son ID"""
        return self.users.get(user_id)
    
    def update_translation(self, original_text: str, translations: Dict[str, str], source_language: str = 'fr', enable_speech: bool = False, sender_id: str = None):
        """Met à jour la dernière traduction pour toute la salle"""
        self.last_translation = {
            'original': original_text,
            'translated': translations,
            'timestamp': datetime.now(),
            'source_language': source_language,
            'enable_speech': enable_speech,
            'sender_id': sender_id  # ID de l'utilisateur qui a envoyé le message
        }
        
        print(f"📝 Nouvelle traduction dans {self.room_name}: '{original_text[:50]}...' -> {len(translations)} langues")
    
    def get_active_languages(self) -> List[str]:
        """Retourne la liste des langues utilisées dans la salle"""
        return list(set(user.language for user in self.users.values()))
    
    def get_participant_languages(self) -> List[str]:
        """Retourne la liste des langues des participants (non-hôtes)"""
        return list(set(user.language for user in self.users.values() if not user.is_host))
    
    def cleanup_inactive_users(self, timeout_minutes: int = 30):
        """Supprime les utilisateurs inactifs"""
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        inactive_users = [
            user_id for user_id, user in self.users.items()
            if user.last_activity < cutoff_time
        ]
        
        for user_id in inactive_users:
            self.remove_user(user_id)
    
    def to_dict(self):
        """Convertit la salle en dictionnaire pour JSON"""
        return {
            'room_id': self.room_id,
            'room_name': self.room_name,
            'created_at': self.created_at.isoformat(),
            'users_count': len(self.users),
            'users': [user.to_dict() for user in self.users.values()],
            'last_translation': {
                'original': self.last_translation['original'],
                'translated': self.last_translation['translated'],
                'timestamp': self.last_translation['timestamp'].isoformat(),
                'source_language': self.last_translation['source_language'],
                'sender_id': self.last_translation.get('sender_id')
            }
        }

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        print("🏠 Gestionnaire de salles initialisé")
    
    def create_room(self, host_nickname: str, host_language: str, room_name: str, password: str = None) -> tuple:
        """
        Crée une nouvelle salle
        Returns: (room_id, user_id, success)
        """
        try:
            # Générer un ID de salle simple (4 chiffres)
            room_id = self._generate_room_id()
            
            # Créer l'hôte
            host_id = str(uuid.uuid4())
            host_user = User(host_id, host_nickname, host_language, is_host=True)
            
            # Créer la salle
            room = Room(room_id, host_id, room_name, password)
            room.add_user(host_user)
            
            # Stocker la salle
            self.rooms[room_id] = room
            
            print(f"🎉 Salle créée : {room_name} (ID: {room_id}) par {host_nickname}")
            return room_id, host_id, True
            
        except Exception as e:
            print(f"❌ Erreur création salle : {str(e)}")
            return None, None, False
    
    def join_room(self, room_id: str, nickname: str, language: str, password: str = None) -> tuple:
        """
        Rejoint une salle existante
        Returns: (user_id, success, error_message)
        """
        try:
            # Vérifier que la salle existe
            if room_id not in self.rooms:
                return None, False, "Salle introuvable"
            
            room = self.rooms[room_id]
            
            # Vérifier le mot de passe
            if room.password and room.password != password:
                return None, False, "Mot de passe incorrect"
            
            # Créer l'utilisateur
            user_id = str(uuid.uuid4())
            user = User(user_id, nickname, language)
            
            # Ajouter à la salle
            if room.add_user(user):
                return user_id, True, None
            else:
                return None, False, "Salle pleine (maximum 10 utilisateurs)"
                
        except Exception as e:
            print(f"❌ Erreur rejoindre salle : {str(e)}")
            return None, False, f"Erreur : {str(e)}"
    
    def leave_room(self, room_id: str, user_id: str) -> bool:
        """Quitte une salle"""
        try:
            if room_id not in self.rooms:
                return False
            
            room = self.rooms[room_id]
            user = room.remove_user(user_id)
            
            # Si l'hôte quitte, supprimer la salle
            if user and user.is_host:
                self._delete_room(room_id)
                print(f"🗑️ Salle {room.room_name} supprimée (hôte parti)")
            
            # Si plus personne, supprimer la salle
            elif len(room.users) == 0:
                self._delete_room(room_id)
                print(f"🗑️ Salle {room.room_name} supprimée (vide)")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur quitter salle : {str(e)}")
            return False
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """Récupère une salle par son ID"""
        return self.rooms.get(room_id)
    
    def update_user_activity(self, room_id: str, user_id: str):
        """Met à jour l'activité d'un utilisateur"""
        room = self.get_room(room_id)
        if room:
            user = room.get_user(user_id)
            if user:
                user.update_activity()
    
    def broadcast_translation(self, room_id: str, original_text: str, source_language: str, sender_id: str = None, enable_speech: bool = False):
        """
        Diffuse une traduction à tous les utilisateurs d'une salle
        Flux adapté selon les spécifications :
        - Hôte parle français -> traduit vers toutes les langues des participants + synthèse vocale
        - Participant parle sa langue -> traduit vers français seulement
        """
        room = self.get_room(room_id)
        if not room:
            return False
        
        # Importer ici pour éviter les imports circulaires
        from translation_manager import translation_manager
        
        translations = {}
        
        if source_language == 'fr':  # L'hôte parle français
            # Traduire vers toutes les langues des participants
            participant_languages = room.get_participant_languages()
            
            for target_lang in participant_languages:
                try:
                    translated = translation_manager.translate(original_text, source_language, target_lang)
                    translations[target_lang] = translated
                    print(f"🌍 Hôte -> {target_lang}: {translated[:50]}...")
                except Exception as e:
                    print(f"❌ Erreur traduction vers {target_lang}: {str(e)}")
                    translations[target_lang] = f"Erreur de traduction"
            
            # Activer la synthèse vocale pour les participants
            enable_speech = True
            
        else:  # Un participant parle dans sa langue
            # Traduire seulement vers le français pour l'hôte
            try:
                translated = translation_manager.translate(original_text, source_language, 'fr')
                translations['fr'] = translated
                print(f"🌍 Participant ({source_language}) -> français: {translated[:50]}...")
            except Exception as e:
                print(f"❌ Erreur traduction vers français: {str(e)}")
                translations['fr'] = f"Erreur de traduction"
            
            # Pas de synthèse vocale pour l'hôte
            enable_speech = False
        
        # Mettre à jour la salle avec l'ID de l'expéditeur
        room.update_translation(original_text, translations, source_language, enable_speech, sender_id)
        
        return True
    
    def _generate_room_id(self) -> str:
        """Génère un ID de salle simple (4 chiffres)"""
        import random
        while True:
            room_id = f"{random.randint(1000, 9999)}"
            if room_id not in self.rooms:
                return room_id
    
    def _delete_room(self, room_id: str):
        """Supprime une salle"""
        if room_id in self.rooms:
            del self.rooms[room_id]
    
    def cleanup_rooms(self):
        """Nettoie les salles vides et les utilisateurs inactifs"""
        rooms_to_delete = []
        
        for room_id, room in self.rooms.items():
            room.cleanup_inactive_users()
            
            if len(room.users) == 0:
                rooms_to_delete.append(room_id)
        
        for room_id in rooms_to_delete:
            self._delete_room(room_id)
            print(f"🧹 Salle {room_id} supprimée (nettoyage)")
    
    def get_stats(self) -> dict:
        """Retourne les statistiques des salles"""
        return {
            'total_rooms': len(self.rooms),
            'total_users': sum(len(room.users) for room in self.rooms.values()),
            'rooms': [room.to_dict() for room in self.rooms.values()]
        }

# Instance globale du gestionnaire de salles
room_manager = RoomManager()
