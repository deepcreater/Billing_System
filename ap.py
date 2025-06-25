from flask import Flask, render_template, g
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

def get_db():
    if 'db' not in g:
        uri = os.getenv("MONGO_URI")
        g.client = MongoClient(uri, tlsCAFile=certifi.where())
        g.db = g.client["billing_db"]
    return g.db

@app.teardown_appcontext
def close_db(exception):
    client = g.pop('client', None)
    if client:
        client.close()

@app.route('/')
def show_products():
    try:
        db = get_db()
        products = list(db.products.find())
        return render_template("products.html", products=products)
    except Exception as e:
        return f"❌ Error fetching products: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)
