import threading
import time
import Queue
import socket
import sys
from cpdefs import CpDefs
from cpdefs import CpSystemState
from cplog import CpLog
from datetime import datetime
#import Adafruit_BBIO.UART as UART
#import Adafruit_BBIO.GPIO as GPIO

class CpInetState:
    INITIALIZED = 0
    IDLE = 1
    CONNECTED = 2
    CLOSED = 3
    SLEEP = 4
    WAITNETWORKINTERFACE = 5
                      
class CpInetResultCode:
    RESULT_UNKNOWN = 0
    RESULT_OK = 1
    RESULT_ERROR = 2
    RESULT_CONNECT = 3
    RESULT_TIMEOUT = 4
    
class CpInetResponses:
    TOKEN_HTTPOK = "HTTP/1.1 200 OK"
    TOKEN_HTTPERROR = "ERROR"
    TOKEN_HTTPCONNECT = "CONNECT"
    
      
    
class CpInetDefs:

    INET_HOST = CpDefs.InetHost
    INET_PORT = CpDefs.InetPort
    INET_ROUTE = CpDefs.InetRoute
    INET_HTTPPOST = CpDefs.InetPostParams


class CpInetResult:
    ResultCode = 0
    Data = ""
    
class CpInet(threading.Thread):
    
    def __init__(self, inetResponseCallbackFunc=None, *args):
        self._target = self.inet_handler
        self._args = args
        self.__lock = threading.Lock()
        self.closing = False # A flag to indicate thread shutdown
        self.commands = Queue.Queue(5)
        self.data_buffer = Queue.Queue(128)
        self.inet_timeout = 0
        self.inetResponseCallbackFunc = inetResponseCallbackFunc
        self.inetBusy = False
        self.inetResult = CpInetResult()
        self.inetToken = ""
        self.host = CpInetDefs.INET_HOST
        self.port = CpInetDefs.INET_PORT
        self.route = CpInetDefs.INET_ROUTE
        self.sock = None
        self.remoteIp = None
        self.initialized = False
        self.state = CpInetState.CLOSED
        self.state_timeout = time.time()
        self.exponential_backoff = 30
        self.log = CpLog()
        self.state_cb = None
        #self.data_buffer = ""
        threading.Thread.__init__(self)
    
    def setStateChangedCallback(self, callback):
        self.state_cb = callback   
                        
    def lookupStateName(self, index):
        if(index == 0):
            return "INITIALIZED"
        elif(index == 1):
            return "IDLE"
        elif(index == 2):
            return "CONNECTED"
        elif(index == 3):
            return "CLOSED"
        elif(index == 4):
            return "SLEEP"  
                   
    def enter_state(self, new_state, timeout):
        print 'enter_state: ', self.lookupStateName(new_state)
            
        self.state = new_state
        self.state_timeout = time.time() + timeout
    
    def state_timedout(self):
        if(time.time() >= self.state_timeout):
            print 'state_timeout: (', self.lookupStateName(self.state), ')'
            return True
        else:
            return False
        
    def reset_state_timeout(self, timeout):
        print 'reset_state_timeout:'
        self.state_timeout = time.time() + timeout    
    
    def run(self):
        self._target(*self._args)
        
    def shutdown_thread(self):
        print 'shutting down CpInet...'
        self.inet_close() # New code added
        self.__lock.acquire()
        self.closing = True
        self.__lock.release()
    

    def init_socket(self):
        try:
            self.remoteIp = socket.gethostbyname(self.host)
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print 'init_socket: successful (%s)' %self.remoteIp
            return True
        except socket.gaierror:
            self.log.logError('init_socket: failed (hostname could not be resolved)')
            print 'init_socket: failed (hostname could not be resolved)'
            return False
        except:
            self.log.logError('init_socket: failed (other)')
            print 'init_socket: failed (other)'
            return False
              
    def inet_connect(self):
           
        try:
            self.sock.connect((self.remoteIp, self.port))
            print 'inet_connect: successful'
            return True
        except:
            self.log.logError('inet_connect: failed')
            print 'inet_connect: failed'
            return False
        
    def inet_send(self, packet):
           
        postData = CpInetDefs.INET_HTTPPOST % (CpInetDefs.INET_ROUTE, CpInetDefs.INET_HOST, len(packet), packet)
            
        print 'inet_send: (',self.remoteIp, ':', self.port, ')'
        
        if CpDefs.LogPacketLevel == True:
            print 'inet_send: ', postData
        
        try:
            byteCount = self.sock.send(postData)
        except socket.error:
            self.log.logError('inet_send: failed')
            print 'inet_send: failed'
            return False
    
        print 'Packet sent successfully %d' % byteCount    
        reply = self.sock.recv(4096)
        
        #print 'inet_send (reply): ', reply
        
        result = CpInetResultCode()
        
        result = self.inet_parse_result(reply)
        
        if (result.ResultCode == CpInetResultCode.RESULT_OK):
            #print 'ResultCode=CpInetResultCode.RESULT_OK'
            print 'inet_send: successful'
            return True
        elif (result.ResultCode == CpInetResultCode.RESULT_ERROR):
            #print 'ResultCode=CpInetResultCode.RESULT_ERROR'
            self.log.logError('inet_parse_result: %s' % result.Data)
            print 'inet_send: failed (error)'
            return False
        else:
            self.log.logError('inet_parse_result: %s' % result.Data)
            print 'inet_send: failed (unknown)'
            return False
     
        
    def inet_close(self):
           
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            print 'inet_close: successful'
            return True
        except:
            self.log.logError('inet_close: failed')
            print 'inet_close: failed'
            return False      
              
    def toggleState(self, state):
        if (self.state_cb != None):
            self.state_cb(state)    
            
    def inet_handler(self):
        
        retry = 0
        # Start out closed
        self.enter_state(CpInetState.CLOSED, 1)
        
        while not self.closing:
            
            if(self.state == CpInetState.CLOSED):
                # Make sure we have established a connection
                if(self.init_socket() == True):
                    self.enter_state(CpInetState.INITIALIZED, 1)
                    time.sleep(.05)
                    continue
            elif(self.state == CpInetState.INITIALIZED):
                self.toggleState(CpSystemState.CONNECTING)
                if self.inet_connect() == True:
                    self.enter_state(CpInetState.CONNECTED, 30)
                    
                    time.sleep(.05)
                    continue
            elif(self.state == CpInetState.CONNECTED):
                # Allow the connected state to wait at least 30s before
                # going to idle. This will keep us from bouncing between
                # idle and connected states thus decreasing latency.
                # Reset the timer for each new message
                if(self.state_timedout() == True):
                    self.toggleState(CpSystemState.IDLE)
                    self.enter_state(CpInetState.IDLE, 30)
                    continue
                if (self.commands.qsize() > 0):
                    self.toggleState(CpSystemState.SENDING)
                    self.reset_state_timeout(30)
                    print 'Command found'
                    packet = self.commands.get(True)
                    
                    if(self.inet_send(packet) == True):
                        self.commands.task_done()
                    else:
                        # Keep track of send failures
                        pass

            elif(self.state == CpInetState.IDLE):
                # Check to see if there is a queued message
                if (self.commands.qsize() > 0):
                    self.enter_state(CpInetState.CONNECTED, 30)
                    
                # Check for idle timeout then close connection
                if(self.state_timedout() == True):
                    self.inet_close()
                    self.toggleState(CpSystemState.SLEEP)
                    self.enter_state(CpInetState.SLEEP, 60)
                pass
            elif(self.state == CpInetState.SLEEP):
                # Check to see if there is a queued message
                if (self.commands.qsize() > 0):
                    self.enter_state(CpInetState.CLOSED, 1)
                    continue
                
                # Check to wake send ping once every 60s
                if(self.state_timedout() == True):
                    self.enter_state(CpInetState.CLOSED, 1)
                    continue

                
            
        '''
        if(self.inet_test() == True ):
            
            tmp_buffer = ""
        
            while not self.closing:
                
                if (self.commands.qsize() > 0):
                    print 'Command found'
                    packet = self.commands.get(True)
                    self.commands.task_done()
                    self.inet_send(packet)
                    continue
                
                time.sleep(2)
        '''
                    
    def enqueue_packet(self, packet):
        try:
            #self.inetBusy = True
            self.commands.put(packet, block=True, timeout=1)
        except:
            self.__lock.acquire()
            print "The Rf queue is full"
            self.__lock.release()

    def set_timeout(self, timeout):
        self.inet_timeout = datetime.now() + timeout
    
    def is_timeout(self):
        if(datetime.now() >= self.rf_timeout):
            return True
        else:
            return False
    '''
    def is_error(self, token):        
        if(token.find(CpInetResponses.TOKEN_HTTPERROR) > -1):
            return True
        else:
            return False
    '''
        
    def inet_parse_result(self, result):
        
        inet_result = CpInetResult()
        
        if(result.find(CpInetResponses.TOKEN_HTTPOK) > -1):
            inet_result.Data = result
            inet_result.ResultCode = CpInetResultCode.RESULT_OK
        elif(result.find(CpInetResponses.TOKEN_HTTPERROR) > -1):
            inet_result.Data = result
            inet_result.ResultCode = CpInetResultCode.RESULT_ERROR
        else:
            inet_result.Data = result
            inet_result.ResultCode = CpInetResultCode.RESULT_UNKNOWN
                
        return inet_result
            
    
  
  
  
    def inet_test(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.remoteIp, self.port))
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            return True
        except:
            self.log.logError('inet_test:')
            return False


def inetDataReceived(data):
    #print 'Callback function inetDataReceived ', data
    pass
    
if __name__ == '__main__':
    inetThread = CpInet(inetDataReceived)
    inetThread.start()   
    
    
    
    
    
    
    
    
    
           
    '''
    def inet_send2(self, packet):
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error:
            print 'Failed to create socket'
            return False
        
        postData = CpInetDefs.INET_HTTPPOST % (CpInetDefs.INET_ROUTE, CpInetDefs.INET_HOST, len(packet), packet)
        print "RemoteIp %s" % self.remoteIp
        print "Port %d" % self.port
        
        try:
            self.sock.connect((self.remoteIp, self.port))
        except socket.timeout:
            print "Connection timeout"
            return False

        print 'sending inet data ', postData
        
        try:
            byteCount = self.sock.send(postData)
        except socket.error:
            print 'Send failed'
            return False
        
        print 'Packet sent successfully %d' % byteCount    
        reply = self.sock.recv(4096)
        
        print 'Server reply: %s' % reply
        
        result = CpInetResultCode()
        
        result = self.inet_parse_result(reply)
        
        if (result.ResultCode == CpInetResultCode.RESULT_OK):
            print 'ResultCode=CpInetResultCode.RESULT_OK'
        elif (result.ResultCode == CpInetResultCode.RESULT_ERROR):
            print 'ResultCode=CpInetResultCode.RESULT_ERROR'
        else:
            print 'ResultCode=CpInetResultCode.RESULT_UNKNOWN'
            
        
        
            
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        '''
    
    
    