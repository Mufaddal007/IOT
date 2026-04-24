import asyncio
import json 
import logging
import datetime
import websockets
from aiohttp import web
import sqlite3

logging.basicConfig(level = logging.INFO)



esp_clients = set()
browser_clients = set()
actual_state = {}
schedules = []

def get_db_connection():
	conn  = sqlite3.connect("iot.db"); 
	conn.row_factory = sqlite3.Row
	return conn

def get_current_state_from_db():
	conn = get_db_connection();
	state = conn.execute('select * from device_state limit 1').fetchone();
	#print(dict(state))
	conn.close()
	if(state):
		return dict(state);
	else:
		return {"led": "off", "pump": "off"}


def get_now():
    return datetime.now().strftime("%H:%M")
    
    
    
async def scheduler():
    last_state = {}
    while True:
        now = datetime.datetime.now().strftime("%H:%M");
        logging.info("checking schedule at: %s", now);
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
            logging.info("Triggering  => %s %s", device, action)

            if(device=="led" and last_run!=now):
                conn.execute("update device_state set led=? where id = 1", (action,)); 
                conn.execute("update device_state set last_run=? where id=?", (now, row	["id"])); 
                state = {"device": device, "state": action}
                await send_to_esp(device, action)
                logging.info("data emitted")
        conn.commit();
        conn.close()
        #last_state[device] = desired
        await asyncio.sleep(30)


async def browser_handler(websocket):
    logging.info("✅ Browser connected")
    browser_clients.add(websocket)
    try:
        async for message_from_browser in websocket:
            logging.info("📩 From Browser: %s", message_from_browser)
    finally:
        browser_clients.remove(websocket)
        logging.info("❌ Browser disconnected")
    


async def esp_handler(websocket):
    logging.info("✅ ESP connected")
    esp_clients.add(websocket)
    state = get_current_state_from_db()
    await send_to_esp("led", state["led"])
    try:
        async for message in websocket:
            logging.info("📩 From ESP: %s", message)
            data = json.loads(message)
            
            if data.get("type") == "status":
#               conn = get_db_connection()
#               conn.execute("update device_state set led=? where id =1", (data.get("led"), ))
#                conn.commit(); 
#                conn.close(); 
                await send_to_browser({"device": "led", "state": state["led"]})
            
    except Exception as e:
            logging.info("❌ ESP error:  %s", e)
    finally:
        esp_clients.remove(websocket)
        logging.info("❌ ESP disconnected")
        
        


async def send_to_browser(payload: dict):
    if not browser_clients:
        logging.info("no browser clients connected")
        return 

    msg = json.dumps(payload)
    dead = []

    for ws in browser_clients.copy():   # ✅ safe iteration
        try:
            await ws.send(msg)
        except Exception as e:
            logging.error(f"Browser send failed: {e}")
            dead.append(ws)

    for ws in dead:
        browser_clients.discard(ws)

    logging.info("Broadcast to browser: %s", msg)
   
async def send_to_esp(device, state):
    message = {"device": device, "state": state}
    if not esp_clients:
        logging.info("No ESP connected, skipping")
        return
    msg = json.dumps({
        "type": "command", 
        "device" : device, 
        "action" : state
    })
    for ws in esp_clients:
        await ws.send(msg)
    logging.info("Command sent : %s", msg)   
             
 
async def main():
    esp_ws_server = await websockets.serve(esp_handler, "0.0.0.0", 8765)
    browser_ws_server = await websockets.serve(browser_handler, "0.0.0.0", 8766)
    
    
    app = web.Application()
    app.router.add_post("/command", handle_command)
    app.router.add_post("/shceudles", set_schedules)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8081)
    await site.start()
    
    logging.info("Async core running (WS: 8765, HTTP: 8001)")
    
    
    asyncio.create_task(scheduler())
    await asyncio.Future()
    


        
        
async def handle_command(request):
    data = await request.json();
    device = data["device"]; 
    state = data["state"]
        
    await send_to_esp(device, state)
    return web.json_response({"status": "ok"})
    
async def set_schedules(request):
    global schedules
    schedules = await request.json()
    logging.info("Schhedules updated : %s", schedules)
    return web.json_response({"status": "ok"})
    
    
if __name__ =='__main__':
    logging.basicConfig(level = logging.INFO)
    asyncio.run(main())
