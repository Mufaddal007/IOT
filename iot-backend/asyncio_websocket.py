import asyncio
import json 
import logging
import datetime
import websockets
from aiohttp import web
import sqlite3
import aiohttp_cors

logging.basicConfig(level = logging.INFO)

esp_online= False
active_timers = {}
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
    
    
    
async def run_timer(device, duration):
    logging.info("⏱️ Timer started for %s (%s sec)", device, duration)
    
    
    await send_to_esp(device, "on")
    
    remaining = duration
    await send_to_browser({"device": device, "state" : "on"})
    while remaining > 0:
        await send_to_browser({
            "type" : "timer" ,
            "device" : device, 
            "remaining" : remaining
        })
        await asyncio.sleep(1)
            
        remaining -=1
    await send_to_esp(device, "off")
    await send_to_browser({"device": device, "state" :  "off"})
    await send_to_browser({"type": "timer_done", "device" : device})
    logging.info("⏱️ Timer finished for %s", device)
    
#    try:
        #await asyncio.sleep(duration)
        

        
#    except asyncio.CancelledError:
#        logging.info("⏱️ Timer cancelled for %s", device)
        
        
async def start_timer(request):
    data = await request.json()
    device = data["device"]
    duration = int(data["duration"])
    
    if device in active_timers:
        active_timers[device].cancel()
    task = asyncio.create_task(run_timer(device, duration))
    active_timers[device]  = task
    
    return web.json_response({"status": "timer started"})
    
async def cancel_timer(request):
    data = await request.json()
    device = data["device"]
    if device in active_timers:
        active_timers[device].cancel()
        await send_to_esp(device, "off")
        await send_to_browser({"device": device, "state" :  "off"})
        del active_timers[device]
        
    return web.json_response({"status": "timer cancelled"})
    
async def scheduler():
    last_state = {}
    while True:
        now = datetime.datetime.now().strftime("%H:%M");
        today = datetime.datetime.now().strftime("%a").upper();
        
        logging.info("checking schedule at: %s", now);
        conn = get_db_connection();
        result = conn.execute("select * from schedule where enabled=1").fetchall();
        
        for row in result:
            device = row["device"]
            days = row["days"]
            if days:
                if today not in days: continue;
            

            if(now==row['from_time'] and row['last_run_from'] != now):
                logging.info("Triggering  => %s %s", device, 'on')
                conn.execute("update device_state set led=? where id = 1", ('on',)); 
                conn.execute("update schedule set last_run_from=? where id=?", (now, row["id"])); 
                state = {"device": device, "state": 'on'}
                await send_to_esp(device, 'on')
                #await send_to_browser(state)
            if(now==row['to_time'] and row['last_run_to'] != now):
                logging.info("Triggering  => %s %s", device, 'off')
                conn.execute("update device_state set led=? where id = 1", ('off',)); 
                conn.execute("update schedule set last_run_to=? where id=?", (now, row["id"])); 
                state = {"device": device, "state": 'off'}
                await send_to_esp(device, 'off')
                #await send_to_browser(state)
        conn.commit();
        conn.close()
        #last_state[device] = desired
        await asyncio.sleep(30)


async def browser_handler(websocket):
    logging.info("✅ Browser connected")
    browser_clients.add(websocket)
    if esp_online:
        await send_to_browser({"type": "esp_status", "status":"online"})
    else:
        await send_to_browser({"type": "esp_status", "status": "offline"})
    state = get_current_state_from_db()
    await send_to_browser({"device": "led", "state": state["led"]})
    try:
        async for message_from_browser in websocket:
            logging.info("📩 From Browser: %s", message_from_browser)
    finally:
        browser_clients.remove(websocket)
        logging.info("❌ Browser disconnected")
    


async def esp_handler(websocket):
    global esp_online
    logging.info("✅ ESP connected")
    esp_clients.add(websocket)
    esp_online = True
    await send_to_browser({
        "type": "esp_status", 
        "status" : "online"
    })
    state = get_current_state_from_db()
    await send_to_esp("led", state["led"])
    try:
        async for message in websocket:
            logging.info("📩 From ESP: %s", message)
            data = json.loads(message)
            
            if data.get("type") == "status":
               conn = get_db_connection()
               conn.execute("update device_state set led=? where id =1", (data.get("state"), ))
               conn.commit(); 
               conn.close(); 
               await send_to_browser({"device": "led", "state": data.get("state")})
            
    except Exception as e:
            logging.info("❌ ESP error:  %s", e)
    finally:
        esp_clients.remove(websocket)
        logging.info("❌ ESP disconnected")
        esp_online=False
        await send_to_browser({
        "type": "esp_status", 
        "status" : "offline"
    })
        
        


async def send_to_browser(payload: dict):
    if not browser_clients:
        logging.info("no browser clients connected")
        return 

    msg = json.dumps(payload)
    dead = []

    for ws in browser_clients.copy():
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
    
    app.router.add_post("/start-timer", start_timer)
    app.router.add_post("/cancel-timer", cancel_timer)
    
    cors = aiohttp_cors.setup(app, defaults= {
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials= True, 
            expose_headers="*", 
            allow_headers= "*",
        )
        
    })
    
    for route in list(app.router.routes()):
        cors.add(route)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8081)
    await site.start()
    
    logging.info("Async core running (ESP WS: 8765, Browser WS: 8766, HTTP: 8001)")
    
    
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
