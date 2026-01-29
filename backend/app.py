from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允许前端访问

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    # ⚠️ 现在是“假登录”，后面再接数据库
    if email == "test@example.com" and password == "123456":
        return jsonify({
            "code": 0,
            "message": "login success",
            "data": {
                "user": {
                    "email": email,
                    "name": "Test User"
                }
            }
        })

    return jsonify({
        "code": 1,
        "message": "invalid credentials"
    }), 401


if __name__ == "__main__":
    app.run(debug=True)


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    # 现在先做“假注册”：只要字段齐就成功
    if not name or not email or not password:
        return jsonify({"code": 1, "message": "missing fields"}), 400

    return jsonify({
        "code": 0,
        "message": "register success",
        "data": {
            "user": {
                "name": name,
                "email": email
            }
        }
    })
