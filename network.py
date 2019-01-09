import json
from twisted.internet.endpoints import TCP4ServerEndpoint, TCP4ClientEndpoint, connectProtocol
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from uuid import uuid4
from time import time
from twisted.python import log
import sys, logging


generate_nodeid = lambda: str(uuid4())


class P2Protocol(Protocol):
    def __init__(self, factory):
        self.factory = factory
        self.state = "HELLO"
        self.remote_nodeid = None
        self.nodeid = self.factory.nodeid
        self.lc_ping = LoopingCall(self.send_ping)
        self.peertype = None
        self.lastping = None

    ### Connection events
    def connectionMade(self):
        remote_ip = self.transport.getPeer()
        host_ip = self.transport.getHost()
        self.remote_ip = remote_ip.host + ":" + str(remote_ip.port)
        self.host_ip = host_ip.host + ":" + str(host_ip.port)
        log.msg("Connection from", self.transport.getPeer(), logLevel=logging.CRITICAL)
        
    def connectionLost(self, reason):
        if self.remote_nodeid in self.factory.peers:
            self.factory.peers.pop(self.remote_nodeid)
            self.lc_ping.stop()
        print(self.nodeid, "disconnected")

    ### onDataReceived
    def dataReceived(self, data):
        print("Data Received")
        for line in data.splitlines():
            line = line.strip()
            msg = json.loads(line)
            msgtype = msg['msgtype']
            print (msg, msgtype)
            
            if msgtype == "hello":
                self.handle_hello(msg)
                self.state = "READY"

            elif msgtype == "ping":
                self.handle_ping()

            elif msgtype == "pong":
                self.handle_pong()

            elif msgtype == "getaddr":
                self.handle_getaddr()

            elif msgtype == "addr":
                self.handle_addr(msg)
            
    ### Send method
    def send_hello(self):
        hello = json.dumps({'nodeid': self.nodeid, 'msgtype': 'hello'})
        self.transport.write((hello + '\n').encode())
          
    
    def send_ping(self):
        ping = json.dumps({'msgtype': 'ping'})
        print("Pinging", self.remote_nodeid)
        self.transport.write((ping + '\n').encode())


    def send_pong(self):
        pong = json.dumps({'msgtype': 'pong'})
        self.transport.write((pong + '\n').encode())

    
    def send_addr(self, mine=False):
        now = time()
        if mine:
            peers = [(self.host_ip, self.nodeid)]
        else:
            peers = [(peer.remote_ip, peer.remote_nodeid) for peer in self.factory.peers if peer.peertype == 1 and peer.lastping > now-240]
        addr = json.dumps({'msgtype': 'addr', 'peers': peers})
        self.transport.write((addr + '\n').encode())


    def send_getaddr(self):
        getaddr = json.dumps({'msgtype': 'getaddr'})
        self.transport.write((getaddr + '\n').encode())
    
    ### Handlers
    def handle_addr(self, msg):
        print(msg["peers"], self.factory.peers)
        for remote_ip, remote_nodeid in msg["peers"]:
            if remote_nodeid not in self.factory.peers:
                host, port = remote_ip.split(":")
                point = TCP4ClientEndpoint(reactor, host, int(port))
                d = connectProtocol(point, P2Protocol(node))
                d.addCallback(gotProtocol)
        print("PEERSSSSS:", self.factory.peers)

    def handle_getaddr(self):
        self.send_addr()


    def handle_hello(self, hello):
        self.remote_nodeid = hello["nodeid"]
        if self.remote_nodeid == self.nodeid:
            print("Connected to myself.", self.nodeid)
            self.transport.loseConnection()
        else:
            self.factory.peers[self.remote_nodeid] = self
            #self.lc_ping.start(10)
            ### inform our new peer about us
            self.send_addr(mine=True)
            ### and ask them for more peers
            self.send_getaddr()

    
    def handle_ping(self):
        self.send_pong()
    
    
    def handle_pong(self):
        print("Got pong from", self.remote_nodeid)
        self.lastping = time()


class P2PFactory(Factory):
    def __init__(self):
        self.peers = {}
        self.nodeid = generate_nodeid()
        self.peertype = 1

    def buildProtocol(self, addr):
        return P2Protocol(self)



def gotProtocol(p):
    """The callback to start the protocol exchange. We let connecting
    nodes start the hello handshake""" 
    p.send_hello()
    

### Settings
node = P2PFactory()
protocol = P2Protocol(node)
