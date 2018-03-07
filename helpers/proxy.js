// npm install http-proxy
// node helpers/proxy.js http://10.128.23.1:8882

var httpProxy = require('http-proxy');

var target = process.argv[2];

if (!target) {
    console.error("You'll need to specify the target parameter");
    process.exit(1);
}

console.log(target)

var proxy = httpProxy.createProxyServer({
    target: target,
    localAddress: "0.0.0.0"
});

proxy.on('error', function (err, req, res) {
    console.error(err);
  res.writeHead(500, {
    'Content-Type': 'text/plain'
  });

  res.end('Something went wrong. And we are reporting a custom error message.');
});

proxy.listen(8000);