addEventListener('install', () => self.skipWaiting());
addEventListener('activate', () => self.clients.claim());


// addEventListener('fetch', e => {
//   // we only handle requests to a special /SLEEP url:
//   const url = new URL(e.request.url);
//   if (url.pathname !== '/stdin') return;

//   // wait ?t=X milliseconds, then return a 304:
//   e.respondWith(new Promise(resolve => {
//     clients.get(event.clientId).then(id=>{console.log(id);resolve(new Response("hi"))})
//   }));
// });

// async function getch()

var resolvers = {};

addEventListener('message', async event => {
    if (event.data.type == "resolveStdin") {
        resolvers[event.source.id](new Response(event.data.content));
    }
});

addEventListener('fetch', e => {
  // we only handle requests to a special /SLEEP url:
  const url = new URL(e.request.url);
  if (url.pathname !== '/sleep') return;

  // wait ?t=X milliseconds, then return a 304:
  e.respondWith(new Promise(resolve => {
    const t = new URLSearchParams(url.search).get('t');
    const response = new Response(null, {status:304});
    setTimeout(resolve, t*1000, response);
  }));
});


addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    if (url.pathname != "/stdin" || !event.clientId) return

    let resolver;
    let promise = new Promise((resolve, reject) => {resolver = resolve});
    resolvers[event.clientId] = resolver;

    event.respondWith(promise)
});
