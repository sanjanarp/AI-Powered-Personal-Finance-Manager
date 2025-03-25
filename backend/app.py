from flask import Flask
from routes.advice import advice_bp
from routes.analyze import analyze_bp

app = Flask(__name__)
app.register_blueprint(advice_bp, url_prefix="/advice")
app.register_blueprint(analyze_bp, url_prefix="/analyze")

if __name__ == "__main__":
    app.run(debug=True)
