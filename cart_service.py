import os, requests
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
basedir = os.path.abspath(os.path.dirname(__file__))

# Initalizing the flask application and connecting to the database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'task.sqlite')
db = SQLAlchemy(app)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id =  db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    product_price = db.Column(db.Float, nullable=False)
    product_quantity = db.Column(db.Integer, nullable=False)

# GET ALL
@app.route('/cart', methods=['GET'])
def get_carts():
    carts = Cart.query.all()
    carts_list = [{"cart_id": cart.id,
                    "user_id": cart.user_id,
                    "product_id": cart.product_id,
                    "product_name": cart.product_name,
                    "product_price": cart.product_price,
                    "product_quantity": cart.product_quantity}
                    for cart in carts]

    return jsonify({"carts": carts_list})

@app.route('/cart/<int:user_id>', methods=['GET'])
def get_cart_by_user(user_id):
    carts = Cart.query.filter_by(user_id=user_id)
    carts_list = [{"cart_id": cart.id,
                    "user_id": cart.user_id,
                    "product_id": cart.product_id,
                    "product_name": cart.product_name,
                    "product_price": cart.product_price,
                    "product_quantity": cart.product_quantity}
                    for cart in carts]

    return jsonify({"carts": carts_list})

@app.route('/cart', methods=['POST'])
def create_cart():
    data = request.json
    if "product_id" not in data:
        return jsonify({"error": "All JSON fields must be filled. "})

    if "user_id" in data:
        new_cart = Cart(user_id=data['user_id'],
                        product_id=data['product_id'],
                        product_name=data['product_name'],
                        product_price=data['product_price'],
                        product_quantity=data['product_quantity'])

    if "user_id" not in data:
        new_cart = Cart(product_id=data['product_id'],
                        product_name=data['product_name'],
                        product_price=data['product_price'],
                        product_quantity=data['product_quantity'])

    db.session.add(new_cart)
    db.session.commit()

    return jsonify({"message": "Cart created", "product":
                    {"cart_id": new_cart.id,
                     "user_id": new_cart.user_id,
                     "product_name": new_cart.product_name,
                     "product_price": new_cart.product_price,
                     "product_quantity": new_cart.product_quantity}})

# ADD ITEM TO CART
@app.route('/cart/<int:user_id>/add/<int:product_id>', methods=['POST'])
def add_to_cart(user_id, product_id):

    # parse incoming JSON for quantity
    desired_quantity_json = request.json
    desired_quantity = int(desired_quantity_json['quantity'])

    # Query the product service
    product = requests.get(f'http://jhayes-cmsc455-productservice.onrender.com/products/{product_id}')
    data = product.json()
    if 'error' in data:
        return data
    quantity = int(data['quantity'])

    if (quantity < desired_quantity):
        return jsonify({"error": "Desired product quanity exceeds stock limit"}), 416

    quantity_modified = requests.post(f'http://jhayes-cmsc455-productservice.onrender.com/products/update/quantity/{product_id}', json=desired_quantity_json)
    if ('error' in quantity_modified):
        return quantity_modified.json()

    # Query the cart database for user's carts
    users_carts = Cart.query.filter_by(user_id=user_id, product_id=product_id)
    carts_list = [cart.id for cart in users_carts]

    # If a cart with the product ID already exist, update the db
    if carts_list:
        cart_id = carts_list[0]
        product_cart = Cart.query.get(cart_id)
        product_cart.product_quantity += desired_quantity
        db.session.commit()

        return jsonify({"success": "cart updated successfully"})

    # Else, create a new cart with the product
    new_cart = Cart(user_id=user_id,
                    product_id=data['id'],
                    product_name=data['name'],
                    product_price=data['price'],
                    product_quantity=data['quantity'])
    db.session.add(new_cart)
    db.session.commit()

    return jsonify({"success": "cart created successfully"})

@app.route('/cart/<int:user_id>/remove/<int:product_id>', methods=['POST'])
def remove_from_cart(user_id, product_id):

    # parse incoming JSON for quantity
    desired_quantity_json = request.json
    desired_quantity = int(desired_quantity_json['quantity'])

    # Query the cart database for user's carts
    users_carts = Cart.query.filter_by(user_id=user_id, product_id=product_id)
    carts_list = [cart.id for cart in users_carts]

    # If a cart with the product ID already exist, update the db
    if carts_list:
        cart_id = carts_list[0]
        product_cart = Cart.query.get(cart_id)
        current_quantity = product_cart.product_quantity

        if (current_quantity < desired_quantity):
            return jsonify({"error": "Can not have negative cart quanity. Lower quantity modifier"})

        if (current_quantity == desired_quantity):
            db.session.delete(product_cart)
            db.session.commit()
            return jsonify({"success": "Item removed from cart"})

        product_cart.product_quantity -= desired_quantity
        db.session.commit()
        return jsonify({"success": "Cart updated successfully"})

    return jsonify({"error": "Item not in cart"})



if __name__ == "__main__":
    # db.create_all()
    app.run(debug=True)
