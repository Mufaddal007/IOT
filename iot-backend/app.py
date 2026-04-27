from flask import Flask, request, jsonify, render_template
import requests
import logging
import sqlite3


app = Flask(__name__)
logging.basicConfig(level = logging.INFO)

ASYNC_CORE_URL="http://127.0.0.1:8081"


def get_current_state_from_db():
	conn = get_db_connection();
	state = conn.execute('select * from device_state limit 1').fetchone();
	#print(dict(state))
	conn.close()
	if(state):
		return dict(state);
	else:
		return {"led": "off", "pump": "off"}




def get_db_connection():
	conn  = sqlite3.connect("iot.db"); 
	conn.row_factory = sqlite3.Row
	return conn


@app.route("/")
def home():
	return render_template("index.html"); 


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    if data.get("username")=="admin" and data.get("password") =="admin":
        return jsonify({"status": "ok"})
    return jsonify({"error": "invalid"}), 401
    
    


@app.route("/api/state", methods=["POST"])
def update_state():
	data = request.json;
	logging.info(data)
	conn = get_db_connection()
	#send_command("led", data.get("led"))
	conn.execute("update device_state set led=?, pump=? where id=1 ", (data.get("led"), data.get("pump")))
	data = {"device": "led", "state": data.get("led")}
	try:
        	requests.post(f"{ASYNC_CORE_URL}/command", json= data, timeout=1)
	except Exception as e:
        	logging.info("Async core not reachable: %s", e)
	conn.commit();
	conn.close()
	return jsonify({"status": "sent"})


@app.route("/api/sensor", methods=["POST"])
def sensor_data():
	data = request.json
	conn = get_db_connection()
	conn.execute("insert into sensor_data (moisture) values(?)", (data.get("moisture"),));
	conn.commit(); 
	conn.close();
	logging.info("sensor data: %s", data)
	return jsonify({"status": "stored"})



@app.route("/api/schedule", methods=["POST"])
def create_schedule():
	data = request.json
	conn = get_db_connection()
	enabled = 1;
	conn.execute("insert into schedule(label, device, from_time, to_time, days, enabled) values(?,?,?,?,?,?)", (data.get("label"), data.get("device"),  data.get("from_time"), data.get("to_time"), data.get("days"), enabled))
    
	try:
       		requests.post(f"{ASYNC_CORE_URL}/schedules", json=schedules, timeout= 1)
	except Exception as e:
        	logging.info("Async core not reachable: %s", e )
	conn.commit();
	conn.close()
	return jsonify({"status": "updated"})

@app.route("/api/schedules", methods=["GET"])
def get_schedule():
	conn = get_db_connection();
	rows = conn.execute("select * from schedule").fetchall(); 
	conn.close(); 
	return jsonify([dict(row) for row in rows]);

@app.route("/api/schedule/toggle", methods=["POST"])
def toggle_schedule():
	data = request.json
	conn  = get_db_connection();
	conn.execute("update schedule set enabled = ? where id = ? ", (data.get("enabled"), data.get("id"))); 
	conn.commit()
	conn.close()
	return jsonify({"status": "updated"})
    
@app.route("/api/schedule/delete", methods=["POST"])    
def  delete_schedule():
    data = request.json
    conn = get_db_connection(); 
    conn.execute("delete from schedule where id=? ", (data.get("id"),)); 
    conn.commit(); 
    conn.close();
    return jsonify({"status": "deleted"}); 



if __name__== '__main__':
    app.run(host="0.0.0.0", port=1000)
