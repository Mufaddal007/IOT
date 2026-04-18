from flask import Flask, request, jsonify, render_template
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
import datetime


app = Flask(__name__)

device_state = {
	"led" : "off", 
	"pump" : "off"
}



def check_schedule():
	now = datetime.datetime.now().strftime("%H:%M"); 
	print("checking schedule at: ", now); 
	conn = get_db_connection(); 
	result = conn.execute("select * from schedule where time=? and enabled=1", (now,)).fetchall();
	today = datetime.datetime.now().strftime("%a").upper();
	for row in result:
		device = row["device"]
		action = row["action"]
		last_run = row["last_run"]
		days = row["days"]
		if days:
			if today not in days: continue;
		print(f"Triggering {device} -> {action}")
		if(device=="led" and last_run!=now):
			conn.execute("update device_state set led=? where id = 1", (action,)); 
			conn.execute("update device_state set last_run=? where id=?", (now, row["id"])); 
	conn.commit();
	conn.close()

scheduler = BackgroundScheduler()
scheduler.add_job(check_schedule, 'interval', seconds=30)
scheduler.start()


def get_db_connection():
	conn  = sqlite3.connect("iot.db"); 
	conn.row_factory = sqlite3.Row
	return conn


@app.route("/")
def home():
	return render_template("index.html"); 


@app.route("/api/state", methods=["GET"])
def get_state():
	conn = get_db_connection(); 
	state = conn.execute('select * from device_state limit 1').fetchone(); 
	conn.close()
	if(state):
		return jsonify(dict(state))
	else:
		return jsonify({"led": "off", "pump": "off"})


@app.route("/api/state", methods=["POST"])
def update_state():
	data = request.json; 
	print(data)
	conn = get_db_connection()
	conn.execute("update device_state set led=?, pump=? where id=1 ", (data.get("led"), data.get("pump")))
	conn.commit(); 
	conn.close()
	return jsonify({"status": "updated"})


@app.route("/api/sensor", methods=["POST"])
def sensor_data():
	data = request.json
	conn = get_db_connection()
	conn.execute("insert into sensor_data (moisture) values(?)", (data.get("moisture"),));
	conn.commit(); 
	conn.close();
	print("sensor data: ", data)
	return jsonify({"status": "stored"})



@app.route("/api/schedule", methods=["POST"])
def create_schedule():
	data = request.json
	conn = get_db_connection()
	enabled = 1;
	conn.execute("insert into schedule(device, action, time, days, enabled) values(?,?,?,?,?)", (data.get("device"), data.get("action"), data.get("time"), data.get("days"), enabled))
	conn.commit();
	conn.close()
	return jsonify({"status": "created"})

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

if __name__ =='__main__':
	app.run(host="0.0.0.0", port=1000, debug=False)
