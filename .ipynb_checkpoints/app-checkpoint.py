from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient  # ✅ Import MongoClient
from config import db  # Import db from config.py
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    products = list(db.products.find({}, {"_id": 1, "name": 1, "price": 1}))
    return render_template('index.html', products=products)

@app.route('/add_product', methods=['POST'])
def add_product():
    data = request.json
    product = {"name": data["name"], "price": data["price"]}
    db.products.insert_one(product)
    return jsonify({"message": "Product added successfully"}), 201

@app.route('/create_invoice', methods=['POST'])
def create_invoice():
    data = request.json
    customer_name = data["customer_name"]

    total_amount = sum(item["price"] * item["quantity"] for item in data["items"])

    invoice = {
        "customer_name": customer_name,
        "date": datetime.utcnow(),
        "total_amount": total_amount,
        "items": data["items"]
    }

    result = db.invoices.insert_one(invoice)
    return jsonify({"message": "Invoice created successfully", "invoice_id": str(result.inserted_id)}), 201

if __name__ == '__main__':
    app.run(debug=True)
