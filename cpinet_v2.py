import threading
import time
import Queue
import socket
import sys
from cpdefs import CpDefs
from cpdefs import CpSystemState
from cplog import CpLog
from datetime import datetime

class CpInetState:
    INITIALIZE = 0
    IDLE = 1
    CONNECT = 2
    CLOSE = 3
    SLEEP = 4
    SEND = 5
    WAITNETWORKINTERFACE = 6
                      
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
    
class CpInetTimeout:
    INITIALIZE = 5
    IDLE = 30
    CONNECT = 5
    CLOSE = 0
    SLEEP = 30
    SEND = 5
    WAITNETWORKINTERFACE = 120
    
class CpInetError:
    InitializeErrors = 0
    InitializeMax = 3
    ConnectErrors = 0
    ConnectMax = 3
    SendErrors = 0
    SendMax = 3
    CloseErrors = 0
    CloseMax = 3
    
    
    
    


class CpInetResult:
    ResultCode = 0
    Data = ""
    
class CpInet2(threading.Thread):
    
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
        self.state = CpInetState.INITIALIZE
        self.inetError = CpInetError()
        self.state_timeout = time.time()
        self.exponential_backoff = 30
        self.log = CpLog()
        self.state_cb = None
        self.retries = 1
        self.waitRetryBackoff = {1:5, 2:15, 3:30}
        self.stateMaxRetries = 3
        threading.Thread.__init__(self)
    
    def setStateChangedCallback(self, callback):
        self.state_cb = callback   
                        
    def lookupStateName(self, index):
        if(index == 0):
            return "INITIALIZE"
        elif(index == 1):
            return "IDLE"
        elif(index == 2):
            return "CONNECT"
        elif(index == 3):
            return "CLOSE"
        elif(index == 4):
            return "SLEEP"  
        elif(index == 5):
            return "SEND"
        elif(index == 6):
            return "WAITNETWORKINTERFACE" 
               
        
    def enter_state(self, statefunc, timeout):
        self.STATEFUNC = statefunc
        self.timestamp = datetime.now()
        self.timeout = timeout
        
    def exit_state(self):
        self.STATEFUNC = 0
        self.timeout = 0.0
        #self.commCallbackHandler = None        
        
    def state_timedout(self):
        if((datetime.now() - self.timestamp).seconds >= self.timeout):
            print 'state_timeout: (', self.lookupStateName(self.state), ')'
            return True
        else:
            return False
        
    def reset_state_timeout(self):
        self.timestamp = datetime.now()
        
    def inet_handler(self):
        # Start out initializing socket
        self.enter_state(self.init_socket, CpInetTimeout.INITIALIZE)
        
        while not self.closing:
            if(self.STATEFUNC != 0):
                self.STATEFUNC()
            time.sleep(.0001)
            
        
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
            self.enter_state(self.inet_connect, CpInetTimeout.CONNECT)
            return True
        except socket.gaierror:
            self.log.logError('init_socket: failed (hostname could not be resolved)')
            print 'init_socket: failed (hostname could not be resolved)'
        except:      
            self.log.logError('init_socket: failed (other)')
            print 'init_socket: failed (other)'
        
        
        # ******** BEGIN ERROR HANDLING ********
        
        # If we get this far we received an error
        self.inetError.InitializeErrors += 1
        
        if (self.inetError.InitializeErrors > self.inetError.InitializeMax):
            print 'Max Initialize Errors'
            # Reset Error Counter
            self.inetError.InitializeErrors = 0
            # Handle Max Errors
            # Signal to reset PPP
            return False 
          
        print 'Waiting Backoff %d' % self.waitRetryBackoff[self.inetError.InitializeErrors]
        # Allow some settle time before trying again
        time.sleep(self.waitRetryBackoff[self.inetError.InitializeErrors])
        
        # ******** END ERROR HANDLING ********
        
        return False
              
    def inet_connect(self):
           
        try:
            self.sock.connect((self.remoteIp, self.port))
            print 'inet_connect: successful'
            self.enter_state(self.inet_idle, CpInetTimeout.IDLE)
            return True
        except:         
            self.log.logError('inet_connect: failed')
            print 'inet_connect: failed'

        
        # ******** BEGIN ERROR HANDLING ********
        
        # If we get this far we received an error
        self.inetError.ConnectErrors += 1
        
        if (self.inetError.ConnectErrors > self.inetError.ConnectMax):
            # Handle Max Errors
            self.enter_state(self.init_socket, CpInetTimeout.INITIALIZE)
            return False 
          
        # Allow some settle time before trying again
        time.sleep(self.waitRetryBackoff[self.inetError.ConnectErrors])
        
        # ******** END ERROR HANDLING ********

    def inet_send(self):
        
        # Allow the connected state to wait at least 30s before
        # going to idle. This will keep us from bouncing between
        # idle and connected states thus decreasing latency.
        # Reset the timer for each new message
        if(self.state_timedout() == True):
            self.enter_state(self.inet_idle, CpInetTimeout.IDLE)
            return True

        if (self.commands.qsize() > 0):
            self.reset_state_timeout()
            print 'Command found'
            packet = self.commands.get(True)
            
            if(self.inet_send_packet(packet) == True):
                self.commands.task_done()
                return True
        else:
            # Otherwise we have no new messages and the current
            # state has not yet timed out so return True in order
            # to avoid the error handling
            return True
            
        # ******** BEGIN ERROR HANDLING ********
        
        # If we get this far we received an error
        self.inetError.SendErrors += 1
        
        if (self.inetError.SendErrors > self.inetError.SendMax):
            # Handle Max Errors
            self.enter_state(self.inet_connect, CpInetTimeout.CONNECT)
            return False 
          
        # Allow some settle time before trying again
        time.sleep(self.waitRetryBackoff[self.inetError.SendErrors])
        
        # ******** END ERROR HANDLING ********
            
    # inet_send_packet is explicitly called by inet_send 
    def inet_send_packet(self, packet):
           
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
     
    def inet_idle(self):
        # Check to see if there is a queued message
        if (self.commands.qsize() > 0):
            self.enter_state(self.inet_send,CpInetTimeout.SEND)
            return
            
        # Check for idle timeout then close connection
        if(self.state_timedout() == True):
            self.inet_close()
            self.enter_state(self.inet_sleep, CpInetTimeout.SLEEP)
            
    def inet_sleep(self):
        # Check to see if there is a queued message
        if (self.commands.qsize() > 0):
            self.enter_state(self.init_socket, CpInetTimeout.INITIALIZE)
            return
        
        # Check to wake send ping once every 60s
        if(self.state_timedout() == True):
            self.enter_state(self.init_socket, CpInetTimeout.INITIALIZE)
            return
      
    # inet_close is explicitly called by inet_sleep or shutdown_thread
    # inet_close is not used in conjunction with enter_state function  
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
              
    def handle_error(self):
        
        # Make sure we haven't exhausted all retries
        if self.retries == self.stateMaxRetries:
            print "max retries attempted for current state"
            return True

        time.sleep(self.waitRetryBackoff[self.retries]) # Delay n seconds before trying again
        self.retries += 1
        return False
             
    def enqueue_packet(self, packet):
        try:
            #self.inetBusy = True
            self.commands.put(packet, block=True, timeout=1)
        except:
            self.__lock.acquire()
            print "The Rf queue is full"
            self.__lock.release()

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
            
    
    '''
    def inet_handler2(self):

        # Start out closed
        self.enter_state(CpInetState.CLOSED, 1)
        
        while not self.closing:
            
            if(self.state == CpInetState.CLOSED):
                # Make sure we have established a connection
                if(self.init_socket() == True):
                    self.enter_state(CpInetState.INITIALIZED, 1)
                    time.sleep(.05)
                    continue
                
                # ERROR HANDLING ROUTINE
                if self.handle_error():
                    # NEED TO HANDLE INIT_SOCKET FAILING 3 TIMES
                    pass
                else:
                    print 'Error init_socket failed retry %d waiting %d sec.' % (self.retries, self.waitRetryBackoff[self.retries])
                    continue
                # END ERROR HANDLING ROUTINE
                        

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
    inetThread = CpInet2(inetDataReceived)
    inetThread.start()   
    
    
    while True:
        input = raw_input(">> ")
                # Python 3 users
                # input = input(">> ")
        if input == 'exit' or input == 'EXIT':
            inetThread.shutdown_thread()
            
            while(inetThread.isAlive()):
                time.sleep(.005)
                
            print "Exiting app"
            break
        elif input == '0':
            inetThread.enqueue_packet("abc123")
        else:
            pass

            
        time.sleep(.5)
    
    
    