# XOS VNF PROXY

This is a simple container that can be used to proxy requests from the local environment 
to a VNF livinig somewhere else.

### Start the proxy

```bash
docker run --name proxy -p 8000:8000 -d xos/vnf-proxy node proxy.js <vnf-url:vnf-port>
```

For example: 
```
docker run --name proxy -p 8000:8000 -d xos/vnf-proxy node proxy.js http://10.128.23.1:8882
```

### Consume the proxied APIs from inside a synchronizer

To call the VNF APIs from your synchronizer you'll need as first to find your host machine ip,
you can do that with:

```bash
docker exec -it <your-sincronizer-container> bash
/sbin/ip route|awk '/default/ { print $3 }'
```

Supposing that the returned ip is `172.20.0.1` you can then point your synchronizer to use `http://172.20.0.1:8000`