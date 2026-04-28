const base_url = "/api";
async function loadState() {
    const res = await fetch(base_url + "/state");
    const data = await res.json();
    document.getElementById("ledState").innerText = data.led;
}

async function toggleLed() {
    const current = document.getElementById("ledState").innerText;
    const newState = current == "on" ? "off" : "on";

    await fetch(base_url + "/state", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            led: newState
        })
    });
    //	loadState();

}

const socket = new  WebSocket("ws://192.168.31.113:8766");
socket.onopen = () => {
	console.log("Connected to websocket")
  socket.send(JSON.stringify({
    type: "register",
    client: "browser"
  }));
};
socket.onmessage  = (event) => {
	const msg = JSON.parse(event.data); 
	if(msg.type && msg.type==="timer"){
		document.getElementById("timerDisplay").innerText = msg.remaining + "sec"; 
		return ; 
	}
	
	else if(msg.type && msg.type==="timer_done"){
		document.getElementById("timerDisplay").innerText = "Done"; 
		return ;
	}
	else if(msg.type && msg.type==="esp_status"){
		const el = document.getElementById("espStatus");; 
		el.innerText = msg.status; 
		el.className = msg.status; 
		return ;
	}
	const device =   msg["device"];
	const state = msg ["state"]; 
	updateDeviceUI(device, state); 
	console.log(msg);
};

function updateDeviceUI(device, state) {
    const el = document.getElementById("ledState");
    if (!el)
        return;
    if (state === "on") {
        el.innerText = "on";
        el.style.background = "green";
    } else {
        el.innerText = "off";
        el.style.background = "red";
    }

}
async function createSchedule() {
    const from_time = document.getElementById("from_time").value;
	const to_time = document.getElementById("to_time").value; 
    const device = document.getElementById("device").value;
    const days = document.getElementById("days").value;
	const label = document.getElementById("label").value; 

    await fetch("/api/schedule", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            device: device,
			from_time: from_time, 
			to_time : to_time, 
            label : label,
            days: days
        })
    });

    loadSchedules();
}

async function loadSchedules() {
    const res = await fetch("/api/schedules");
    const data = await res.json();
    const table = document.getElementById("scheduleTable"); 
	table.innerHTML='';
 

    data.forEach(s => {
        const row = `
		  <tr>
			 <td>${s.label}</td>
			 <td>${s.device}</td>
			 <td>${s.from_time}</td>
			 <td>${s.to_time}</td>
			 <td>${s.days || "All"}</td>
			 <td>${s.enabled ? "enabled" : "disabled"}</td>
			 <td>${getActionButtons(s)}</td>
		  </tr>
			
		`; 
		table.innerHTML +=row; 
		
    });

}

function getActionButtons(schedule){
	return 	`
		<button class="btn-toggle" onclick="toggleSchedule(${schedule.id}, ${schedule.enabled==1 ? 0 : 1})"> ${schedule.enabled ? 'Disable' : 'Enable'}</button>
		<button class="btn-delete" onclick="deleteSchedule(${schedule.id})">Delete</button>
	`;
}

async function toggleSchedule(id, enabled) {
    await fetch("/api/schedule/toggle", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            id: id,
            enabled: enabled
        })
    });
    loadSchedules();
}

async function deleteSchedule(id){
	await fetch("/api/schedule/delete", {
		method: "POST", 
		headers: {"Content-Type": "application/json"}, 
		body: JSON.stringify({id: id})
	}); 
	loadSchedules();
}

document.addEventListener("DOMContentLoaded", function () {
    loadSchedules()
});


async function startTimer(){
	const duration = document.getElementById("timerInput").value; 
	await fetch("http://192.168.31.113:8081/start-timer", {
		method: "POST", 
	    headers : {"Content-Type": "application/json"}, 
		body: JSON.stringify({
			device:"led", 
			duration : duration
		}) 
		
	}); 
}


async function cancelTimer(){
	await fetch("http://192.168.31.113:8081/cancel-timer", {
		method: "POST", 
		headers: {"Content-Type": "application/json"},
		body: JSON.stringify({
			device: "led"
		})
	}); 
}

