importScripts("https://cdn.jsdelivr.net/pyodide/v0.18.1/full/pyodide.js");

config = {
  backend: "https://192.168.0.81:8080",
  filesystem: {
    baseURL: "/",
    files: ["main.py", "interface.py"]
  },
  entrypoint: "main.py",
}

function get(data) {
  var request;
  request = new XMLHttpRequest();
  request.open('POST', 'http://192.168.0.81:8080/', false);  // `false` makes the request synchronous
  request.send(data);
  return request.responseText;
}
function sleep(amount) {
  const request = new XMLHttpRequest();
  request.open('GET', '/sleep?t='+amount, false);  // `false` makes the request synchronous
  request.send(null)
  return request.responseText
}
function stdin(amount) {
  self.postMessage({type:"stdin", length: amount})
  const request = new XMLHttpRequest();
  request.open('GET', '/stdin', false);  // `false` makes the request synchronous
  request.send(null)
  return request.responseText;
}
function writeOutput(type, text) {self.postMessage({type:type, content:text})}
async function main() {
  pyodide = await loadPyodide({
    indexURL  : "https://cdn.jsdelivr.net/pyodide/v0.18.1/full/",
    fullStdLib: false
  })

  let FS = pyodide.FS
  FS.registerDevice(FS.makedev(70, 0), {write: text => writeOutput("stdout", text)})
  FS.mkdir("/app")
  FS.mount(FS.filesystems.IDBFS, {}, "/app")
  for (const filename of config.filesystem.files.values())
    FS.createLazyFile("/app", filename, config.filesystem.baseURL + filename, true, true)
  FS.chdir("/app")

  pyodide.globals.set("config", config)

  await pyodide.loadPackage("micropip")
  await pyodide.runPython("import micropip")
  await pyodide.globals.get("micropip").install("https://cdn.jsdelivr.net/gh/cole-wilson/jug-wheel@main/Jug-2.1.1.post9-py3-none-any.whl")
  await pyodide.globals.get("micropip").install("koral")
  await pyodide.runPython("from koral import run\nrun(config)")

};

main();
