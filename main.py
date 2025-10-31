from flask import Flask, request, jsonify
from database import db, init_database, UserRepository, GameVersionRepository
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config[
    "SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://wakeEmil:%2120010809%21@wakeEmil.mysql.pythonanywhere-services.com/wakeEmil$default"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299
app.config["SQLALCHEMY_POOL_TIMEOUT"] = 20

# Инициализация базы данных
init_database(app)


@app.route('/')
def index():
    return 'API работает'


@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data or "username" not in data or "password" not in data:
            return jsonify({"status": "error", "message": "Missing data"}), 400

        # Проверяем, есть ли пользователь
        if UserRepository.get_user_by_username(data["username"]):
            return jsonify({"status": "error", "message": "User exists"}), 400

        # Создаем пользователя
        hashed_password = generate_password_hash(data["password"])
        user = UserRepository.create_user(
            username=data["username"],
            password_hash=hashed_password,
            is_subscription=data.get("is_subscription", False),
            crystal=data.get("crystal", 0)
        )

        return jsonify({
            "status": "ok",
            "user_id": user.id
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        auth_result = UserRepository.authenticate_user(
            username=data["username"],
            password_hash_check_func=check_password_hash,
            password=data["password"]
        )

        if auth_result['status']:
            user = auth_result['user']
            return jsonify({
                "status": "ok",
                "user_id": user.id,
                "is_subscription": user.is_subscription,
                "crystal": user.crystal
            })
        return jsonify({"status": "fail", "message": auth_result['message']}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/version', methods=['GET'])
def get_version():
    try:
        latest_version = GameVersionRepository.get_latest_version()
        if latest_version:
            return jsonify({
                "status": "ok",
                "version": latest_version.to_dict()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "No active version found"
            }), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run()
