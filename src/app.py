from flask import Flask, jsonify
from dotenv import load_dotenv
import MySQLdb
import os


# Read the credentials from the .txt file
app = Flask(__name__)

# Load the environment variables file
BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, 'db.env'))

# Connect to the database
db = MySQLdb.connect(host=os.getenv('DB_HOST'),    # your host, usually localhost
                     user=os.getenv('DB_USER'),         # your username
                     passwd=os.getenv('DB_PASS'),  # your password
                     db=os.getenv('DB'),  # name of the database
                     autocommit=True,
                     ssl_mode="VERIFY_IDENTITY",
                     ssl={
                         "ca": "./cacert.pem"
                     })
@app.route('/', methods=['GET'])
def greet():
    return "Welcome to Jessica Leishman's (100747155) Manufacturing/Inventory Management API"

@app.route('/hello/', methods=['GET', 'POST'])
def welcome():
    return "Hello World!"

#Retrieves all parts
@app.get('/getAll')
def get_all_parts():
    #does not use warehouse as a filter, assumes user wants to know all locations
    query = """SELECT part_number, warehouse_id, supplier_id, quantity FROM PARTS ORDER BY part_number, warehouse_id ASC"""
    c = db.cursor()
    varhold = c.execute(query)
    if varhold > 0:
        parts = c.fetchall()
        #stringBuild = ""

        #for result in parts:
        #    string = f"'part': {result[0]}, 'warehouse': {result[1]}, 'quantity': {result[2]} "
        #    stringBuild += ("{"+ string + "},")

        # Return the results as JSON
        return jsonify({'result':'OK -- RETRIEVED','parts': parts}), 200
    else:
        return jsonify({'result': 'ERROR', 'msg': 'could not retrieve parts'}), 400


#get inventory for a part number in all warehouses
@app.get('/getPN/<string:id>')
def get_pn_inventory(id):
    #does not use warehouse as a filter, assumes user wants to know all locations
    query = """SELECT SUM(quantity) AS total FROM PARTS WHERE part_number =%s"""
    pn = id
    c = db.cursor()
    rows = c.execute(query, [pn])

    if rows > 0:
        qty = c.fetchone()
        # Return the results as JSON
        if qty[0] != None:
            return jsonify({'result':'OK -- RETRIEVED', 'part': pn, 'quantity': qty[0]}), 200
        else:
            return jsonify({'result': 'ERROR', 'msg': 'part does not exist!', 'part': id}), 200
    else:
        return jsonify({'result': 'ERROR', 'msg': 'could not query db'}), 400

#get inventory for a part number in a specific warehouse
@app.get('/getPN/<string:id>/<int:wh>')
def get_pn_wh_inventory(id,wh):
    #does use warehouse as a filter,
    query = """SELECT SUM(quantity) AS total FROM PARTS WHERE part_number =%s AND  warehouse_id=%s"""
    c = db.cursor()
    rows = c.execute(query, [id,wh])
    if rows > 0:
        qty = c.fetchone()
        if qty[0] != None:
            # Return the results as JSON
            return jsonify({'result':'OK -- RETRIEVED','part': id, 'warehouse': wh, 'quantity': qty[0]}), 200
        else:
            return jsonify({'result': 'ERROR', 'msg': 'part and wh combo does not exist!', 'part': id, 'wh': wh}), 200
    else:
        return jsonify({'result': 'ERROR', 'msg': 'could not query db'}), 400


#Place an order (would typically trigger a request for internal systems)
@app.post('/order/<string:id>/<int:wh>')
def order_part(id, wh):
    query = """SELECT quantity, supplier_id FROM PARTS WHERE part_number =%s AND  warehouse_id=%s ORDER BY priority ASC"""
    c = db.cursor()
    rows = c.execute(query, [id, wh])
    if rows > 0:
        qty = c.fetchone()
        try:
            while (qty[0] <= 0):
                qty = c.fetchone()
        except:
            return jsonify({'result': 'ERROR', 'msg': 'quantity 0 for all suppliers', 'part': id, 'warehouse': wh}), 400

        if qty[0] == None:
            return jsonify({'result': 'ERROR', 'msg': 'quantity 0 for all suppliers', 'part': id, 'warehouse': wh}), 400

        #if there is a valid quantity, need to update it so does not get over ordered from
        newqty = int(qty[0])-1
        query = """UPDATE PARTS SET quantity =%s WHERE part_number =%s AND warehouse_id=%s AND supplier_id=%s ORDER BY priority ASC"""
        rows2 = c.execute(query, [newqty, id, wh, str(qty[1])])
        if rows2 > 0:
            # Return the results as JSON
            return jsonify({'result': 'OK -- ORDERED', 'part': id, 'wh': wh, 'supplier': qty[1], 'remaining quantity': newqty}), 200
        else:
            return jsonify({'result': 'ERROR', 'msg': 'couldnt update quantity to place order', 'part': id, 'wh': wh, 'supplier': qty[1]}), 400
    else:
        return jsonify({'result': 'ERROR', 'msg': 'part and warehouse combination does not exist!', 'part': id,
                        'warehouse': wh}), 400
    return jsonify({'result': 'OK', 'pn': id})


#Add a part number, wh and supplier id to the database
@app.put('/addPN/<string:id>/<int:wh>/<string:suppID>')
def add_pn(id, wh, suppID):
    query = """INSERT INTO PARTS VALUES (%s, %s, %s, %s)"""
    c = db.cursor()
    rows = c.execute(query, [id, suppID, wh, 0])

    if rows > 0:
        return jsonify({'result': 'OK -- INSERTED', 'pn': id, 'warehouse':wh, 'supplier':suppID, 'qty': 0})
    else:
        return jsonify({'result': 'ERROR', 'msg': 'Could not add value combination!', 'pn': id, 'warehouse': wh, 'supplier': suppID, 'qty': 0})


#Increments the quantity fora given pn/wh/suppID combination
@app.put('/addQty/<string:id>/<int:wh>/<string:suppID>/<int:qty>')
def add_qty(id,wh,suppID,qty):
    query = """SELECT SUM(quantity) AS total FROM PARTS WHERE part_number =%s AND warehouse_id=%s AND supplier_id=%s"""
    c = db.cursor()
    rows = c.execute(query, [id, wh,suppID])

    if rows > 0:
        currentQty = c.fetchone()
        updatedVal = int(currentQty[0]) + int(qty)

        query = """UPDATE PARTS SET quantity=%s WHERE part_number=%s AND warehouse_id=%s AND supplier_id=%s"""
        rowsImpact = c.execute(query, [updatedVal, id, wh, suppID])

        if rowsImpact > 0:
            return jsonify({'result': 'OK -- UPDATED', 'pn': id, 'warehouse':wh, 'supplier':suppID, 'newQty': updatedVal}), 200
        else:
            return jsonify({'result': 'ERROR', 'msg': 'part number/supplierid/warehouse combo could not be increased'}), 400
    else:
        return jsonify({'result': 'ERROR', 'msg': 'part number/supplierid/warehouse combo does not exist'}), 400


#Updates the quantity of a part number, supplier id in a warehouse to the specified amount
@app.put('/updateQty/<string:id>/<int:wh>/<string:suppID>/<int:qty>')
def update_qty(id,wh,suppID,qty):
    query = """SELECT SUM(quantity) AS total FROM PARTS WHERE part_number =%s AND warehouse_id=%s AND supplier_id=%s"""
    c = db.cursor()
    rows = c.execute(query, [id, wh, suppID])

    if rows > 0:
        query = """UPDATE PARTS SET quantity=%s WHERE part_number=%s AND warehouse_id=%s AND supplier_id=%s"""
        rowsImpact = c.execute(query, [qty, id, wh, suppID])

        if rowsImpact > 0:
            return jsonify({'result': 'OK -- UPDATED', 'pn': id, 'warehouse': wh, 'supplier': suppID, 'qty': qty}), 200
        else:
            return jsonify({'result': 'ERROR', 'msg': 'part number/supplierid/warehouse combo could not be updated'}), 400
    else:
        return jsonify({'result': 'ERROR', 'msg': 'part number/supplierid/warehouse combo does not exist'}), 400


#Deletes a specific part number and supplier id combination from the database
@app.delete('/deletePN/<string:id>/<string:suppID>')
def remove_pn_wh(id,suppID):
    query = """SELECT part_number FROM PARTS WHERE part_number =%s AND supplier_id=%s"""
    c = db.cursor()
    rows = c.execute(query, [id, suppID])

    if rows > 0:
        query = """DELETE FROM PARTS WHERE part_number=%s  AND supplier_id=%s"""
        rowsImpact = c.execute(query, [id,suppID])

        if rowsImpact > 0:
            return jsonify({'result': 'OK -- DELETED', 'pn': id, 'supplier': suppID}), 200
        else:
            return jsonify({'result': 'ERROR', 'msg': 'could not delete part number/supplieridcombo'}), 400
    else:
        return jsonify({'result': 'ERROR', 'msg': 'part number/supplierid combo does not exist'}), 400


#Deletes all instances of a part number from the database
@app.delete('/deletePN/<string:id>')
def remove_pn(id):

    query = """SELECT part_number FROM PARTS WHERE part_number =%s"""
    c = db.cursor()
    rows = c.execute(query, [id])

    if rows > 0:
        query = """DELETE FROM PARTS WHERE part_number=%s"""
        rowsImpact = c.execute(query, [id])

        if rowsImpact > 0:
            return jsonify({'result': 'OK -- DELETED', 'pn': id}), 200
        else:
            return jsonify({'result': 'ERROR', 'msg': 'could not delete part number'}), 400
    else:
        return jsonify({'result': 'ERROR', 'msg': 'part number does not exist'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=105)