from flask import (Flask, request, jsonify)
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
    inventories = db["inventories"]

    @app.route("/cleanup", methods=["POST"])
    def clean_database():
        mongoClient.drop_database(db)

        return { "message": "Cleanup completed." }, 200
    
    @app.route("/products", methods=["PUT"])
    def register_product():
        reqBody = request.json

        if not all([reqBody.get("name"), reqBody.get("category"), reqBody.get("price")]):
            return { "message": "Invalid input, missing name or price." }, 400

        productId = reqBody.get("id") if reqBody.get("id") else str(ObjectId())

        products.insert_one(
            {
                "_id": productId,
                "name": reqBody.get("name"),
                "category": reqBody.get("category"),
                "price": reqBody.get("price")
            }
        )

        return { "message": "Product registered.", "id": productId }, 201
    
    @app.route("/products", methods=["GET"])
    def get_products():
        category_filter = {"category": request.args.get('category')} if request.args.get('category') else {}
        product_list = list(products.find(category_filter))
        
        return product_list, 200
    
    @app.route("/products/<productId>", methods=["GET"])
    def get_product(productId):
        product = products.find_one({"_id": productId})

        if product is None:
            return { "message": "Product not found." }, 404
        
        return product, 200
    
    @app.route("/products/<productId>", methods=["DELETE"])
    def delete_product(productId):
        result = products.delete_one({"_id": productId})
        
        if (result.deleted_count > 0):
            return { "message": "Product deleted." }, 204
        
        else:
            return { "message": "Product not found." }, 404
        
    @app.route("/warehouses", methods=["PUT"])
    def register_warehouse():
        reqBody = request.json

        if not all([reqBody.get("name"), reqBody.get("location"), reqBody.get("capacity")]):
            return { "message": "Invalid input, missing name, location or capacity." }, 400

        warehouse = warehouses.insert_one(
            {
                "name": reqBody.get("name"),
                "location": reqBody.get("location"),
                "capacity": reqBody.get("capacity")
            }
        )

        return { "message": "Warehouse registered.", "id": str(warehouse.inserted_id) }, 201
    
    @app.route("/warehouses/<warehouseId>", methods=["GET"])
    def get_warehouse(warehouseId):
        warehouse = warehouses.find_one({"_id": ObjectId(warehouseId)})

        if warehouse is None:
            return { "message": "Warehouse not found." }, 404
        
        else:
            warehouse["_id"] = str(warehouse["_id"])
            return warehouse, 200
    
    @app.route("/warehouses", methods=["GET"])
    def get_warehouses():
        warehouse_list = []

        for warehouse in warehouses.find():
            warehouse["_id"] = str(warehouse["_id"])
            warehouse_list.append(warehouse)
        
        return warehouse_list, 200
        
    @app.route("/warehouses/<warehouseId>", methods=["DELETE"])
    def delete_warehouse_and_inventory(warehouseId):
        result = warehouses.delete_one({"_id": ObjectId(warehouseId)})
        
        if (result.deleted_count > 0):
            inventories.delete_many({"warehouseId": warehouseId})
            return { "message": "Warehouse deleted." }, 204
        
        else:
            return { "message": "Warehouse not found." }, 404
        
    @app.route("/warehouses/<warehouseId>/inventory", methods=["PUT"])
    def add_product_to_warehouse_inventory(warehouseId):
        reqBody = request.json

        if not all([reqBody.get("productId"), reqBody.get("quantity")]):
            return { "message": "Invalid input, missing productId or quantity." }, 400

        inventory_product = {
            "warehouseId": warehouseId,
            "productId": reqBody['productId'],
            "quantity": reqBody['quantity']
        }

        product = inventories.insert_one(inventory_product)

        return { "message": "Product added to inventory.", "id": str(product.inserted_id) }, 201
        
    @app.route("/warehouses/<warehouseId>/inventory", methods=["GET"])
    def get_warehouse_inventory(warehouseId):
        inventory = list(inventories.find({"warehouseId": warehouseId}))

        if(inventory is None):
            return { "message": "Warehouse or inventory not found." }, 404

        else:
            for product in inventory:
                product["_id"] = str(product["_id"])

            return inventory, 200
        
    @app.route("/warehouses/<warehouseId>/inventory/<inventoryId>", methods=["GET"])
    def get_inventory(warehouseId, inventoryId):
        inventory = inventories.find_one({"_id": ObjectId(inventoryId), "warehouseId": warehouseId})

        if(inventory is None):
            return { "message": "Inventory not found." }, 404

        else:
            inventory["_id"] = str(inventory["_id"])
            return inventory, 200

    @app.route("/warehouses/<warehouseId>/inventory/<inventoryId>", methods=["DELETE"])
    def remove_product_from_inventory(warehouseId, inventoryId):
        result = inventories.delete_one({"_id": ObjectId(inventoryId), "warehouseId": warehouseId})

        if(result.deleted_count > 0):
            return { "message": "Product removed from inventory." }, 204

        else:
            return { "message": "Warehouse not found." }, 200
        
    @app.route('/warehouses/<warehouseId>/value', methods=['GET'])
    def get_warehouse_total_product_value(warehouseId):
        pipeline = [
        {
            "$match": {
                "warehouseId": warehouseId
            }
        },
        {
            "$lookup": {
                "from": "products",
                "localField": "productId",
                "foreignField": "_id",
                "as": "productDetails"
            }
        },
        {
            "$unwind": {
                "path": "$productDetails",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$group": {
                "_id": None,
                "totalValue": {
                    "$sum": {
                        "$multiply": ["$quantity", "$productDetails.price"]
                    }
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "value": "$totalValue"
            }
        }
    ]
        warehouse = warehouses.find_one({"_id": ObjectId(warehouseId)})

        if warehouse is None:
            return { "message": "Warehouse not found." }, 404
        
        else:
            result = list(inventories.aggregate(pipeline))

            return result[0], 200
    

    @app.route('/statistics/warehouse/capacity', methods=['GET'])
    def get_warehouses_capacity():
        # Calculate total capacity by summing up the capacity of all warehouses
        total_capacity_result = list(warehouses.aggregate([
            {
                "$group": {
                    "_id": None,
                    "totalCapacity": {"$sum": "$capacity"}
                }
            }
        ]))
        total_capacity = total_capacity_result[0]["totalCapacity"] if total_capacity_result else 0

        # Calculate used capacity by summing up the quantity of each inventory item
        used_capacity_result = list(inventories.aggregate([
            {
                "$group": {
                    "_id": None,
                    "totalUsedCapacity": {"$sum": "$quantity"}
                }
            }
        ]))
        used_capacity = used_capacity_result[0]["totalUsedCapacity"] if used_capacity_result else 0

        # Calculate free capacity as the difference between total capacity and used capacity
        free_capacity = total_capacity - used_capacity

        return {
            "totalCapacity": total_capacity,
            "usedCapacity": used_capacity,
            "freeCapacity": free_capacity
        }, 200

    @app.route('/statistics/products/by/category', methods=['GET'])
    def products_by_category():
        pipeline = [
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        category_stats = [{"category": result['_id'], "count": result['count']} for result in products.aggregate(pipeline)]
        return jsonify(category_stats), 200
    
    return app