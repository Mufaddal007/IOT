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
    const time = document.getElementById("time").value;
    const device = document.getElementById("device").value;
    const days = document.getElementById("days").value;
    const action = document.getElementById("action").value;

    await fetch("/api/schedule", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            device: device,
            action: action,
            time: time,
            days: days
        })
    });

    loadSchedules();
}

async function loadSchedules() {
    const res = await fetch("/api/schedules");
    const data = await res.json();
    const list = document.getElementById("schedules_list");
    list.innerHTML = "";

    data.forEach(s => {
        const li = document.createElement("li");

        li.innerHTML = `
					<div class="schedule-row">
						<div>
							<strong>${s.device}</strong>
							<p>${s.time} • ${s.action}  •  ${s.days ? s.days : "All" }</p>
						</div>
						<div>
							<button class="secondary" onclick="toggleSchedule(${s.id}, ${s.enabled ? 0 : 1})">${s.enabled ? "Disable" : "Enable"}</button>
						
							<button class="danger" onclick="deleteSchedule(${s.id})">Delete</button>
						</div>					
					</div>

				`;
        list.appendChild(li);
    });

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
