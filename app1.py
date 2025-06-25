from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from datetime import datetime
from bson.json_util import dumps
import logging
import os
MONGO_URI = "mongodb+srv://deepak7232914731:eaZ99fUMJd1wfGOR@cluster0.woqbxsd.mongodb.net/?retryWrites=true&w=majority&tls=true"


# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Connection
try:
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client["billing_db"]
    logger.info("✅ Successfully connected to MongoDB.")
except Exception as e:
    logger.error("❌ Error connecting to MongoDB: %s", e)
    raise

@app.route('/')
def index():
    """Render the main page with the list of products."""
    try:
        products = list(db.products.find({}, {"_id": 1, "name": 1, "price": 1}))
        return render_template('index.html', products=products)
    except Exception as e:
        logger.error("Error fetching products: %s", e)
        return jsonify({"error": "Failed to fetch products"}), 500

@app.route('/add_product', methods=['POST'])
def add_product():
    """Add a new product to the database."""
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'price' not in data or 'category' not in data:
            return jsonify({"error": "Missing required fields: name, price, or category"}), 400

        name = data['name'].strip()
        price = float(data['price'])
        category = data['category'].strip()

        if not name or price < 0:
            return jsonify({"error": "Invalid product name or price"}), 400

        product = {
            "name": name,
            "price": price,
            "category": category,
            "created_at": datetime.utcnow()
        }
        result = db.products.insert_one(product)
        logger.info("Added product: %s", name)
        return jsonify({"message": "Product added successfully", "product_id": str(result.inserted_id)}), 201
    except ValueError:
        return jsonify({"error": "Invalid price format"}), 400
    except Exception as e:
        logger.error("Error adding product: %s", e)
        return jsonify({"error": "Failed to add product"}), 500

@app.route('/create_invoice', methods=['POST'])
def create_invoice():
    """Create a new invoice and store it in the database."""
    try:
        data = request.get_json()
        if not data or 'customer_name' not in data or 'items' not in data or not data['items']:
            return jsonify({"error": "Missing required fields: customer_name or items"}), 400

        customer_name = data['customer_name'].strip()
        items = data['items']
        subtotal = float(data.get('subtotal', 0))
        tax = float(data.get('tax', 0))
        total = float(data.get('total', 0))

        # Validate items
        for item in items:
            if 'product_id' not in item or 'name' not in item or 'price' not in item or 'quantity' not in item:
                return jsonify({"error": "Invalid item data"}), 400
            if float(item['price']) < 0 or int(item['quantity']) < 1:
                return jsonify({"error": "Invalid price or quantity in items"}), 400

        # Verify subtotal, tax, and total
        calculated_subtotal = sum(float(item['price']) * int(item['quantity']) for item in items)
        calculated_tax = calculated_subtotal * 0.05
        calculated_total = calculated_subtotal + calculated_tax

        if abs(calculated_subtotal - subtotal) > 0.01 or abs(calculated_tax - tax) > 0.01 or abs(calculated_total - total) > 0.01:
            return jsonify({"error": "Subtotal, tax, or total mismatch"}), 400

        invoice = {
            "customer_name": customer_name,
            "items": items,
            "subtotal": subtotal,
            "tax": tax,
            "total_amount": total,
            "date": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
        result = db.invoices.insert_one(invoice)
        logger.info("Created invoice for customer: %s", customer_name)
        return jsonify({"message": "Invoice created successfully", "invoice_id": str(result.inserted_id)}), 201
    except ValueError:
        return jsonify({"error": "Invalid numeric data format"}), 400
    except Exception as e:
        logger.error("Error creating invoice: %s", e)
        return jsonify({"error": "Failed to create invoice"}), 500

@app.route('/get_invoices', methods=['GET'])
def get_invoices():
    """Retrieve invoices based on optional date range."""
    try:
        start_date_str = request.args.get('start')
        end_date_str = request.args.get('end')

        query = {}
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = {"date": {"$gte": start_date, "$lte": end_date}}
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        invoices = list(db.invoices.find(query, {"_id": 1, "customer_name": 1, "date": 1, "total_amount": 1, "items": 1}))
        logger.info("Fetched %d invoices", len(invoices))
        return dumps(invoices), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        logger.error("Error fetching invoices: %s", e)
        return jsonify({"error": "Failed to fetch invoices"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
