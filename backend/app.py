from flask import Flask
from backend.routes.advice import advice_bp
from backend.routes.analyze import analyze_bp

app = Flask(__name__)
app.register_blueprint(advice_bp, url_prefix="/advice")
app.register_blueprint(analyze_bp, url_prefix="/analyze")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5050)
