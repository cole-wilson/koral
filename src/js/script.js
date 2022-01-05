var stdinRead = "";
var stdinReadLength = null;

Terminal.applyAddon(fit)
term = new Terminal({convertEol: true})
term.open(document.getElementById('terminal'))
term.write("loading...\r\n")
term.fit()

function getKey(key) {
	if (key.charCodeAt(0) == 13)
		return '\n'
	else if (key.charCodeAt(0) == 127) {
		if (stdinRead.length > 0)
			term.write('\b \b')
		stdinRead = stdinRead.slice(0, -1)
		return ""
	}
	else
		return key
}

navigator.serviceWorker.register('/service-worker.js')
navigator.serviceWorker.ready.then( registration => {
onkey = (key) => {
		key = getKey(key)
		if (key == "") return
		stdinRead += key;
		term.write(key)
		if (stdinReadLength == "\n" && stdinRead.includes("\n")) {
			var send = stdinRead.split(/\n/);
			stdinRead = send.slice(1).join("\n");
			registration.active.postMessage({type:"resolveStdin", content:send[0]+"\n"})
			stdinReadLength = null;
		}
		else if (stdinReadLength == "\n") return
		else if (stdinRead.length >= stdinReadLength && stdinReadLength !== null) {
			var send = stdinRead.slice(0, stdinReadLength);
			stdinRead = stdinRead.slice(stdinReadLength);
			registration.active.postMessage({type:"resolveStdin", content:send})
			stdinReadLength = null;
		}
	}
	term.on('key', onkey);

	navigator.serviceWorker.addEventListener('message', event => {
	  console.log(event.data.msg, event.data.url);
	});

	const worker = new Worker("./worker.js", {name: "Coral Thread"});
	worker.onmessage = (e) => {
		data = (e.data)
		switch (data.type) {
			case "stderr":
				term.write("\u001b[31m" + data.content + "\u001b[0m")
				break
			case "stdout":
				term.write(data.content)
				break
			case "stdin":
				stdinReadLength = data.length;
				onkey("")
				break
			default:
				console.log("got unknown message type from WebWorker:", data);
				break
		}
	}

});
