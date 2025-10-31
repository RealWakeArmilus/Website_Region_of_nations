from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Инициализация SQLAlchemy
db = SQLAlchemy()


class DatabaseManager:
    """Менеджер для работы с базой данных"""

    def __init__(self, app=None):
        self._initialized = False
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Инициализация базы данных с приложением Flask"""
        if self._initialized:
            logger.info("База данных уже инициализирована")
            return

        try:
            db.init_app(app)
            with app.app_context():
                db.create_all()
                self._create_default_data()
            self._initialized = True
            logger.info("База данных успешно инициализирована")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise

    def _create_default_data(self):
        """Создание данных по умолчанию"""
        # Создаем дефолтную версию если таблица пустая
        if not GameVersion.query.first():
            default_version = GameVersion(
                version_number="1.0.0",
                version_name="Initial Release",
                is_active=True
            )
            db.session.add(default_version)
            db.session.commit()
            logger.info("Создана версия по умолчанию")

    @contextmanager
    def session(self):
        """Контекстный менеджер для сессии БД"""
        try:
            yield db.session
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Ошибка в сессии БД: {e}")
            raise
        finally:
            db.session.close()

    @contextmanager
    def transaction(self):
        """Контекстный менеджер для транзакций"""
        try:
            yield db.session
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Ошибка в транзакции, откат: {e}")
            raise


# Создаем экземпляр менеджера БД
db_manager = DatabaseManager()


# ---------------------
# Модели данных
# ---------------------

class User(db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_subscription = db.Column(db.Boolean, default=False, nullable=False)
    crystal = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __str__(self):
        return f"User({self.id}: {self.username})"

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование объекта в словарь"""
        return {
            'id': self.id,
            'username': self.username,
            'is_subscription': self.is_subscription,
            'crystal': self.crystal,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class GameVersion(db.Model):
    """Модель версии игры"""
    __tablename__ = 'game_versions'

    id = db.Column(db.Integer, primary_key=True)
    version_number = db.Column(db.String(20), nullable=False)  # "0.0.0" или "0.0.0 beta.1"
    version_name = db.Column(db.String(100), nullable=False)  # "closed beta v.1"
    release_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __str__(self):
        return f"GameVersion({self.id}: {self.version_number} - {self.version_name})"

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование объекта в словарь"""
        return {
            'id': self.id,
            'version_number': self.version_number,
            'version_name': self.version_name,
            'release_date': self.release_date.isoformat() if self.release_date else None,
            'is_active': self.is_active
        }


# ---------------------
# Репозитории
# ---------------------

class UserRepository:
    """Репозиторий для работы с пользователями"""

    @staticmethod
    def create_user(
            username: str,
            password_hash: str,
            is_subscription: bool = False,
            crystal: int = 0
    ) -> User:
        """Создание нового пользователя"""
        with db_manager.session() as session:
            user = User(
                username=username,
                password_hash=password_hash,
                is_subscription=is_subscription,
                crystal=crystal
            )
            session.add(user)
            session.commit()
            logger.info(f"Создан пользователь: {user.username}")
            return user

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        try:
            with db_manager.session() as session:
                user = session.query(User).filter(User.id == user_id).first()
                return user
        except OperationalError:
            with db_manager.session() as session:
                session.rollback()
                user = session.query(User).filter(User.id == user_id).first()
                return user

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Получение пользователя по username"""
        try:
            with db_manager.session() as session:
                user = session.query(User).filter(User.username == username).first()
                return user
        except OperationalError:
            with db_manager.session() as session:
                session.rollback()
                user = session.query(User).filter(User.username == username).first()
                return user

    @staticmethod
    def authenticate_user(username: str, password_hash_check_func, password: str) -> Dict[str, Any]:
        """Аутентификация пользователя"""
        with db_manager.session() as session:
            user = session.query(User).filter(User.username == username).first()
            if user is None:
                return {'status': False, 'message': 'Пользователь не найден', 'user': None}

            if not password_hash_check_func(user.password_hash, password):
                return {'status': False, 'message': 'Неверный пароль', 'user': None}

            return {
                'status': True,
                'message': 'Успешная аутентификация',
                'user': user,
                'user_data': user.to_dict()
            }

    @staticmethod
    def get_all_users() -> List[User]:
        """Получение всех пользователей"""
        with db_manager.session() as session:
            users = session.query(User).all()
            return users

    @staticmethod
    def update_user(user_id: int, **kwargs) -> Optional[User]:
        """Обновление данных пользователя"""
        with db_manager.session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                session.commit()
                logger.info(f"Обновлен пользователь: {user.username}")
                return user
            return None

    @staticmethod
    def delete_user(user_id: int) -> bool:
        """Удаление пользователя"""
        with db_manager.session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                session.delete(user)
                session.commit()
                logger.info(f"Удален пользователь: {user.username}")
                return True
            return False


class GameVersionRepository:
    """Репозиторий для работы с версиями игры"""

    @staticmethod
    def create_version(
            version_number: str,
            version_name: str,
            is_active: bool = True
    ) -> GameVersion:
        """Создание новой версии игры"""
        with db_manager.session() as session:
            # Если новая версия активна, деактивируем все остальные
            if is_active:
                session.query(GameVersion).update({GameVersion.is_active: False})

            version = GameVersion(
                version_number=version_number,
                version_name=version_name,
                is_active=is_active
            )
            session.add(version)
            session.commit()
            logger.info(f"Создана версия: {version.version_number} - {version.version_name}")
            return version

    @staticmethod
    def get_latest_version() -> Optional[GameVersion]:
        """Получение самой новой активной версии игры"""
        try:
            with db_manager.session() as session:
                version = session.query(GameVersion) \
                    .filter(GameVersion.is_active == True) \
                    .order_by(GameVersion.release_date.desc()) \
                    .first()
                return version
        except OperationalError:
            with db_manager.session() as session:
                session.rollback()
                version = session.query(GameVersion) \
                    .filter(GameVersion.is_active == True) \
                    .order_by(GameVersion.release_date.desc()) \
                    .first()
                return version

    @staticmethod
    def get_version_by_id(version_id: int) -> Optional[GameVersion]:
        """Получение версии игры по ID"""
        with db_manager.session() as session:
            version = session.query(GameVersion).filter(GameVersion.id == version_id).first()
            return version

    @staticmethod
    def get_all_versions() -> List[GameVersion]:
        """Получение всех версий игры"""
        with db_manager.session() as session:
            versions = session.query(GameVersion).order_by(GameVersion.release_date.desc()).all()
            return versions

    @staticmethod
    def set_active_version(version_id: int) -> Optional[GameVersion]:
        """Установка версии игры как активной"""
        with db_manager.transaction() as session:
            # Деактивируем все версии
            session.query(GameVersion).update({GameVersion.is_active: False})

            # Активируем выбранную версию
            version = session.query(GameVersion).filter(GameVersion.id == version_id).first()
            if version:
                version.is_active = True
                session.commit()
                logger.info(f"Установлена активная версия игры: {version.version_number}")
                return version
            return None

    @staticmethod
    def update_version(version_id: int, **kwargs) -> Optional[GameVersion]:
        """Обновление данных версии игры"""
        with db_manager.session() as session:
            version = session.query(GameVersion).filter(GameVersion.id == version_id).first()
            if version:
                for key, value in kwargs.items():
                    if hasattr(version, key):
                        setattr(version, key, value)
                session.commit()
                logger.info(f"Обновлена версия игры: {version.version_number}")
                return version
            return None

    @staticmethod
    def delete_version(version_id: int) -> bool:
        """Удаление версии игры"""
        with db_manager.session() as session:
            version = session.query(GameVersion).filter(GameVersion.id == version_id).first()
            if version:
                session.delete(version)
                session.commit()
                logger.info(f"Удалена версия игры: {version.version_number}")
                return True
            return False


# Утилиты для инициализации
def init_database(app):
    """Инициализация базы данных"""
    db_manager.init_app(app)


def close_database():
    """Закрытие соединений с базой данных"""
    # SQLAlchemy автоматически управляет соединениями через пул
    pass
