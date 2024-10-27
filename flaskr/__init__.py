from flask import (Flask, request)
import json
import pymongo
import werkzeug
from bson.objectid import ObjectId

def create_app():
    app = Flask(__name__)
    mongoClient = pymongo.MongoClient(host="localhost", port=27017)
    db = mongoClient["database"]
    warehouses = db["warehouses"]
    products = db["products"]

    @app.route("/cleanup", methods=["POST"])
    def clean_database():
        mongoClient.drop_database(db)

        return { "message": "Cleanup completed." }, 200
    
    @app.route("/products", methods=["PUT"])
    def register_product():
        reqBody = request.json

        if not all([reqBody.get("id"), reqBody.get("name"), reqBody.get("category"), reqBody.get("price")]):
            return { "message": "Invalid input, missing name, location or capacity." }, 400

        products.insert_one(
            {
                "_id": reqBody.get("id"),
                "name": reqBody.get("name"),
                "category": reqBody.get("category"),
                "price": reqBody.get("price")
            }
        )

        return { "message": "Product registered." }, 200
    
    @app.route("/products", methods=["GET"])
    def get_products():
        product_list = []

        for product in products.find():
            product_list.append(product)
        
        return product_list, 200
    
    @app.route("/products/<productId>", methods=["GET"])
    def get_product(productId):
        product = products.find_one({"_id": productId})
        
        return product, 200
    
    @app.route("/products/<productId>", methods=["DELETE"])
    def delete_product(productId):
        result = products.delete_one({"_id": productId})
        
        if (result.deleted_count > 0):
            return {}, 204
        
        else:
            return { "message": "Product not found." }, 404
        
    @app.route("/warehouses", methods=["PUT"])
    def register_warehouse():
        reqBody = request.json

        if not all([reqBody.get("name"), reqBody.get("location"), reqBody.get("capacity")]):
            return { "message": "Invalid input, missing name, location or capacity." }, 400

        warehouses.insert_one(
            {
                "name": reqBody.get("name"),
                "location": reqBody.get("location"),
                "capacity": reqBody.get("capacity")
            }
        )

        return { "message": "Warehouse registered." }, 201
    
    @app.route("/warehouses/<warehouseId>", methods=["GET"])
    def get_warehouse(warehouseId):
        warehouse = warehouses.find_one({"_id": ObjectId(warehouseId)})

        return str(warehouse), 200
    
    @app.route("/warehouses", methods=["GET"])
    def get_warehouses():
        warehouse_list = []

        for warehouse in warehouses.find():
            warehouse_list.append(warehouse)
        
        return str(warehouse_list), 200
        
    @app.route("/warehouses/<warehouseId>", methods=["DELETE"])
    def delete_warehouse_and_inventory(warehouseId):
        result = warehouses.delete_one({"_id": warehouseId})
        
        if (result.deleted_count > 0):
            return { "message": "Warehouse deleted." }, 204
        
        else:
            return { "message": "Warehouse not found." }, 404
        
    @app.route("/warehouses/<warehouseId>/invetory", methods=["PUT"])
    def add_product_to_warehouse_inventory(warehouseId):
        reqBody = request.json

        if not all([reqBody.get("productId"), reqBody.get("quantity")]):
            return { "message": "Invalid input, missing productId or quantity." }, 400

        warehouses.update_one(
            {
                "_id": ObjectId(warehouseId)
            }, {
                "$push": {
                    "inventory": [
                        {
                        "productId": reqBody.get("productId"),
                        "quantity": reqBody.get("quantity")
                        }
                    ]
                }
            }
        )
        
    @app.route("/warehouses/<warehouseId>/inventory", methods=["GET"])
    def get_warehouse_inventory(warehouseId):
        warehouse = warehouses.find_one({"_id": ObjectId(warehouseId)}, {})


        return { "message": "Warehouse deleted." }, 204

    return app