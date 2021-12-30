importScripts("https://cdn.jsdelivr.net/pyodide/v0.18.1/full/pyodide.js");

var stdinReadLength = null;

config = {
  entrypoint: "main.py",
  filesystem: {
    base: "/",
    files: ["main.py", "interface.py"]
  }
}


function makeid(length) {
    var result           = '';
    var characters       = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    var charactersLength = characters.length;
    for ( var i = 0; i < length; i++ ) {
      result += characters.charAt(Math.floor(Math.random() * 
 charactersLength));
   }
   return result;
}


function get(data) {
  // let buffer = new Uint16Array(data);
  var request;
  for (var i = 0; i< 6; i++) {
    request = new XMLHttpRequest();
    request.open('POST', 'http://192.168.0.81:8080/', false);  // `false` makes the request synchronous
    request.send(data);
    if (request.status == 200) break
  }
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
function writeOutput(type, text) {
  self.postMessage({type:type, content:text})
}
async function main() {
  pyodide = await loadPyodide({
    indexURL  : "https://cdn.jsdelivr.net/pyodide/v0.18.1/full/",
    fullStdLib: false
  })

  let FS = pyodide.FS
  FS.registerDevice(FS.makedev(70, 0), {write: text => writeOutput("stdout", text)})
  FS.mkdir("/main")
  FS.mount(FS.filesystems.IDBFS, {}, "/main")
  for (const filename of config.filesystem.files.values()) {
    FS.createLazyFile("/main", filename, config.filesystem.base + filename, true, true)
  }
  pyodide.globals.set("config", config)

  await pyodide.loadPackage("micropip")
  await pyodide.runPython("import micropip")
  await pyodide.globals.get("micropip").install("https://cdn.jsdelivr.net/gh/cole-wilson/jug-wheel@main/Jug-2.1.1.post9-py3-none-any.whl")
  await pyodide.runPython(`
import sys
import js

class Input():
  def read(self, amount):
    return js.stdin(amount)
  def readline(self):
    return self.read(chr(10))

class StandardPrinter():
  def flush(self): ...
  def write(self, text):
    js.writeOutput("stdout", text)

class ErrorPrinter():
  def flush(self): ...
  def write(self, text):
    js.writeOutput("stderr", text)

sys.stdout = StandardPrinter()
sys.stderr = ErrorPrinter()
sys.stdin = Input()

import jug, os
input()
sys.argv = ["<jug runner>", "execute", config.entrypoint, "--will-cite"]
try:
  os.chdir("/main")
  jug.jug.main()
except SystemExit as err:
  print('exited with code', 0 if err.code is None else err.code)
  pass
`,)

};

main();
