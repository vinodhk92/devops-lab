from flask import Flask, jsonify
import os

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "message": "DevOps Lab API is running",
        "version": os.getenv("APP_VERSION", "1.0.0")
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy"
    })


@app.route("/info")
def info():
    return jsonify({
        "application": "devops-lab-api",
        "environment": os.getenv("ENVIRONMENT", "local"),
        "version": os.getenv("APP_VERSION", "1.0.0")
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
