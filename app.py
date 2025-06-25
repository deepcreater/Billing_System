from flask import Flask, render_template, request, jsonify, g
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import logging
import os
import certifi
from dotenv import load_dotenv


client = MongoClient(MONGO_URI, tls=True, tlsCAFile=certifi.where())


# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
handler = logging.FileHandler('app.log')
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)
logger.addHandler(handler)

# MongoDB connection
def get_db():
    if 'db' not in g:
        MONGO_URI = os.getenv("MONGO_URI")
        if not MONGO_URI:
            logger.error("MONGO_URI environment variable not set. Please set it in your environment or .env file.")
            raise ValueError("MONGO_URI environment variable not set.")
        g.client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
        g.db = g.client["billing_db"]
        logger.info("✅ Successfully connected to MongoDB.")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    client = g.pop('client', None)
    if client is not None:
        client.close()


@app.route('/')
def index():
    """Render the main page with the list of products."""
    try:
        db = get_db()  # ✅ Fix: Get the database connection first
        products = list(db.products.find({}, {"_id": 1, "name": 1, "price": 1}))
        return render_template('index.html', products=products)
    except Exception as e:
        logger.error("Error fetching products: %s", e)
        return jsonify({"error": "Failed to fetch products"}), 500


@app.route('/add_product', methods=['POST'])
def add_product():
    """Add a new product to the menu."""
    try:
        db = get_db()
        data = request.get_json()
        name = data.get('name')
        price = data.get('price')
        category = data.get('category')

        if not name or not isinstance(price, (int, float)) or price <= 0:
            return jsonify({"message": "Invalid product details"}), 400

        product = {
            "name": name,
            "price": float(price),
            "category": category,
            "created_at": datetime.utcnow()
        }
        result = db.products.insert_one(product)
        return jsonify({"message": f"Product '{name}' added successfully", "product_id": str(result.inserted_id)}), 201
    except Exception as e:
        logger.error("Error adding product: %s", e)
        return jsonify({"message": "Failed to add product"}), 500

@app.route('/create_invoice', methods=['POST'])
def create_invoice():
    """Create a new invoice for the current bill."""
    try:
        db = get_db()
        data = request.get_json()
        customer_name = data.get('customer_name')
        items = data.get('items')
        subtotal = data.get('subtotal')
        tax = data.get('tax')
        total = data.get('total')
        date = data.get('date')

        if not items or not isinstance(subtotal, (int, float)) or not isinstance(tax, (int, float)) or not isinstance(total, (int, float)):
            return jsonify({"message": "Invalid invoice details"}), 400

        # Validate product IDs
        for item in items:
            product_id = item.get('product_id')
            if not ObjectId.is_valid(product_id):
                return jsonify({"message": f"Invalid product ID: {product_id}"}), 400
            if not db.products.find_one({"_id": ObjectId(product_id)}):
                return jsonify({"message": f"Product not found: {product_id}"}), 404

        invoice = {
            "customer_name": customer_name,
            "items": items,
            "subtotal": float(subtotal),
            "tax": float(tax),
            "total_amount": float(total),
            "date": datetime.fromisoformat(date.replace('Z', '+00:00')),
            "created_at": datetime.utcnow()
        }
        result = db.invoices.insert_one(invoice)
        return jsonify({"message": "Invoice created successfully", "invoice_id": str(result.inserted_id)}), 201
    except Exception as e:
        logger.error("Error creating invoice: %s", e)
        return jsonify({"message": "Failed to create invoice"}), 500

@app.route('/get_invoices', methods=['GET'])
def get_invoices():
    """Fetch invoices within a date range."""
    try:
        db = get_db()
        start_date = request.args.get('start')
        end_date = request.args.get('end')

        if not start_date or not end_date:
            return jsonify({"message": "Start and end dates are required"}), 400

        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00')).replace(hour=23, minute=59, second=59)

        invoices = db.invoices.find({
            "date": {
                "$gte": start,
                "$lte": end
            }
        })

        invoices_list = [
            {
                "invoice_id": str(invoice["_id"]),
                "customer_name": invoice["customer_name"],
                "items": invoice["items"],
                "subtotal": invoice["subtotal"],
                "tax": invoice["tax"],
                "total_amount": invoice["total_amount"],
                "date": invoice["date"].isoformat()
            }
            for invoice in invoices
        ]
        return jsonify(invoices_list), 200
    except Exception as e:
        logger.error("Error fetching invoices: %s", e)
        return jsonify({"message": "Failed to fetch invoices"}), 500

if __name__ == '__main__':
    app.run(debug=False)
