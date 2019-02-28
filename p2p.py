from protocol import *


log.startLogging(sys.stdout)
 


### Server
server = TCP4ServerEndpoint(reactor, 5999)
server.listen(node)


### Client
BOOTSTRAP_LIST = [ "localhost:5997",
                   "localhost:5998",
                 ]

for bootstrap in BOOTSTRAP_LIST:
    host, port = bootstrap.split(":")
    point = TCP4ClientEndpoint(reactor, host, int(port))
    d = connectProtocol(point, protocol)
    d.addCallback(gotProtocol)


### Run
reactor.run()
