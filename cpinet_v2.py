import threading
import time
from datetime import datetime
import Queue
import socket
import mmap
from cpdefs import CpDefs
from cplog import CpLog
from cpstats import CpInetStats
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
    RESULT_SCKTIMEOUT = 4
    RESULT_SCKSENDERROR = 5
    RESULT_SCKRECVERROR = 6
    
class CpInetResponses:
    TOKEN_HTTPOK = "HTTP/1.1 200"
    TOKEN_HTTPACCEPTED = "HTTP/1.1 202"
    TOKEN_HTTPNORESPONSE = "HTTP/1.1 204"
    TOKEN_HTTPERROR = "ERROR"
    TOKEN_HTTPCONNECT = "CONNECT"
    
      
class CpInetDefs:

    INET_HOST = CpDefs.InetHost
    INET_PORT = CpDefs.InetPort
    INET_ROUTE = CpDefs.InetRoute
    INET_HTTPPOST = CpDefs.InetPostParams
    INET_TIMEOUT = CpDefs.InetTimeout
    
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
    
class CpWatchdogStatus:
    Success = "1"
    Error = "2"
    
class CpInet(threading.Thread):
    
    def __init__(self, inetResponseCallbackFunc=None, *args):
        self._target = self.inet_handler
        self._args = args
        self.__lock = threading.Lock()
        self.closing = False # A flag to indicate thread shutdown
        self.commands = Queue.Queue(32)
        #self.data_buffer = Queue.Queue(128)
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
        self.current_state = CpInetState.INITIALIZE
        self.inetError = CpInetError()
        self.state_timeout = time.time()
        self.exponential_backoff = 30
        self.log = CpLog()
        self.state_cb = None
        self.retries = 1
        self.waitRetryBackoff = {1:5, 2:15, 3:30}
        #self.waitRetryBackoff = {1:1, 2:2, 3:3} # Test timeouts to speed up testing
        self.stateMaxRetries = 3
        self.inet_stats = CpInetStats()
        self.inet_stats.LastSent = time
        
        self.fmap = {0:self.init_socket,
                     1:self.inet_idle, 
                     2:self.inet_connect, 
                     3:self.inet_close, 
                     4:self.inet_sleep,
                     5:self.inet_send,
                     6:self.inet_waitnetworkinterface}
        
        
        threading.Thread.__init__(self)
    
    def get_queue_depth(self):
        return self.commands.qsize()
    
    def get_current_state(self):
        return self.lookupStateName(self.current_state)
    
    def get_inet_stats(self):
        return self.inet_stats
       
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
               

    def enter_state(self, new_state, timeout):
        self.current_state = new_state
        self.STATEFUNC = self.fmap[self.current_state]
        self.timestamp = datetime.now()
        self.timeout = timeout
        
        #if(CpDefs.LogVerboseInet):
        print 'enter_state: (', self.lookupStateName(self.current_state), ')'
            
        # Set the led pattern via state_cb
        # Hack if statement to prevent state_cb from being called before
        # setStateChangedCallback is set by cptaskmanager
        if (self.state_cb == None):
            return
        else:
            self.state_cb(new_state)
        
    def exit_state(self):
        self.current_state = 0
        self.STATEFUNC = 0
        self.timeout = 0.0   
        
    def state_timedout(self):
        if((datetime.now() - self.timestamp).seconds >= self.timeout):
            
            if(CpDefs.LogVerboseInet):
                print 'state_timeout: (', self.lookupStateName(self.current_state), ')'
                
            return True
        else:
            return False
        
    def reset_state_timeout(self):
        self.timestamp = datetime.now()
        
    def inet_handler(self):
        
        if (CpDefs.WatchdogWaitNetworkInterface):
            # Start out waiting for network interface
            self.enter_state(CpInetState.WAITNETWORKINTERFACE, CpInetTimeout.WAITNETWORKINTERFACE)
        else:
            # Start out initializing (Use Case for testing without watchdog)
            self.enter_state(CpInetState.INITIALIZE, CpInetTimeout.INITIALIZE)
            
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
            
            if(CpDefs.LogVerboseInet):
                print 'init_socket: successful (%s)' %self.remoteIp
                
            self.enter_state(CpInetState.CONNECT, CpInetTimeout.CONNECT)
            return True
        except socket.gaierror:
            self.log.logError('init_socket: failed (hostname could not be resolved)')
            print 'init_socket: failed (hostname could not be resolved)'
        except:      
            self.log.logError('init_socket: failed (other)')
            print 'init_socket: failed (other)'
        
        # If we get this far we received an error
        self.handle_init_socket_error()
        
        return False
    
    def handle_init_socket_error(self): 
        
        # ******** BEGIN ERROR HANDLING ********
        
        # If we get this far we received an error
        self.inetError.InitializeErrors += 1
        # Updated Statistics
        self.inet_stats.InitErrors += 1
        
        if (self.inetError.InitializeErrors > self.inetError.InitializeMax):
            print 'Max Initialize Errors'
            # Reset Error Counter
            self.inetError.InitializeErrors = 0
            # Handle Max Errors
            # TODO: TEST BEFORE PROD
            
            # Check to see if we need to update watchdog
            # if not we are in test mode and just want to remain in
            # init_socket indefinately
            if (CpDefs.WatchdogWaitNetworkInterface):
                self.watchdog_set_status(CpWatchdogStatus.Error)
                self.enter_state(CpInetState.WAITNETWORKINTERFACE, CpInetTimeout.WAITNETWORKINTERFACE)
                
            return False 
        
        # Allow some settle time before trying again
        print 'Wait Retry Backoff %d sec.' % self.waitRetryBackoff[self.inetError.InitializeErrors]
        time.sleep(self.waitRetryBackoff[self.inetError.InitializeErrors])
        
        # ******** END ERROR HANDLING ********
                      
    def inet_connect(self):
           
        try:
            self.sock.connect((self.remoteIp, self.port))
            # New Code for Timeout
            self.sock.settimeout(CpInetDefs.INET_TIMEOUT)
            # End New Code for Timeout
            
            if(CpDefs.LogVerboseInet):
                print 'inet_connect: successful'
                
            self.enter_state(CpInetState.IDLE, CpInetTimeout.IDLE)
            self.watchdog_set_status(CpWatchdogStatus.Success)
            return True
        except:         
            self.log.logError('inet_connect: failed')
            print 'inet_connect: failed'
        
        # If we get this far we received an error
        self.handle_inet_connect_error()
        
        return False


    def handle_inet_connect_error(self): 
        
        # ******** BEGIN ERROR HANDLING ********
        
        self.inetError.ConnectErrors += 1
        
        # Updated Statistics
        self.inet_stats.ConnectErrros += 1
        
        print 'CONNECT FAILED'
        
        if (self.inetError.ConnectErrors > self.inetError.ConnectMax):
            # Handle Max Errors
            self.inetError.ConnectErrors = 0
            self.enter_state(CpInetState.INITIALIZE, CpInetTimeout.INITIALIZE)
            return False 
          
        # Allow some settle time before trying again
        print 'Wait Retry Backoff %d sec.' % self.waitRetryBackoff[self.inetError.ConnectErrors]
        time.sleep(self.waitRetryBackoff[self.inetError.ConnectErrors])
        
        # ******** END ERROR HANDLING ********        
        
    def inet_send(self):
        
        # Allow the connected state to wait at least 30s before
        # going to idle. This will keep us from bouncing between
        # idle and connected states thus decreasing latency.
        # Reset the timer for each new message
        if(self.state_timedout() == True):
            self.enter_state(CpInetState.IDLE, CpInetTimeout.IDLE)
            return True

        if (self.commands.qsize() > 0):
            self.reset_state_timeout()
            
            if(CpDefs.LogVerboseInet):
                print 'Command found'
                
            packet = self.commands.get(True)
            
            
            #if(self.inet_send_packet(packet) == True):
            result = self.inet_send_packet(packet)
            
            if(result.ResultCode == CpInetResultCode.RESULT_OK):
                
                # Updated Statistics
                self.inet_stats.Sent += 1
                self.inet_stats.LastSent = time
        
                if(CpDefs.LogVerboseInet):
                    print 'SEND SUCCESSFUL'
                    
                self.commands.task_done()
            else:
                print 'inet_send error: %s' % result.Data
                self.enqueue_packet(packet)
                self.handle_inet_send_error()
                #print 'tasks in queue %d' % self.commands.qsize()
                #print 'error: ResultCode=(%d) Data=%s ' % (result.ResultCode, result.Data)
                
            return True
        else:
            # Otherwise we have no new messages and the current
            # state has not yet timed out so return True in order
            # to avoid the error handling
            return True
        
        
    def handle_inet_send_error(self): 
        
        # ******** BEGIN ERROR HANDLING ********
        
        self.inetError.SendErrors += 1
        
        # Updated Statistics
        self.inet_stats.SendErrors += 1
        
        print 'SEND FAILED'
        
        if (self.inetError.SendErrors > self.inetError.SendMax):
            # We have exceeded the maximum allowable attempts so
            # close and reinitialize the connection
            self.inetError.SendErrors = 0
            self.inet_close()
            self.enter_state(CpInetState.INITIALIZE, CpInetTimeout.INITIALIZE)
            return False 
          
        # Allow some settle time before trying again
        print 'Wait Retry Backoff %d sec.' % self.waitRetryBackoff[self.inetError.SendErrors]
        time.sleep(self.waitRetryBackoff[self.inetError.SendErrors])
        
        # ******** END ERROR HANDLING ********
            
    # inet_send_packet is explicitly called by inet_send 
    def inet_send_packet(self, packet):
        
        # Setup the HTTP request
        postData = CpInetDefs.INET_HTTPPOST % (CpInetDefs.INET_ROUTE, CpInetDefs.INET_HOST, len(packet), packet)
        
        result = CpInetResultCode()
        
        if(CpDefs.LogVerboseInet):
            print 'inet_send: (',self.remoteIp, ':', self.port, ')'
            print 'inet_send: ', postData
          
        # Send the HTTP request
        try:
            byteCount = self.sock.send(postData)
        except socket.error, e:
            result.ResultCode = CpInetResultCode.RESULT_SCKSENDERROR
            result.Data = e.args[0]
            self.log.logError('inet_send: failed')
            print 'inet_send: failed'
            return result
         
        # Process the response
        try:
            reply = self.sock.recv(4096)
        except socket.error, e:
            err = e.args[0]
            if err == 'timed out':
                result.ResultCode = CpInetResultCode.RESULT_SCKTIMEOUT
                print 'socket timeout exception'
            else:
                result.ResultCode = CpInetResultCode.RESULT_SCKRECVERROR   
                
            result.Data = e.args[0]    
                
            self.log.logError('inet_send: failed')
            print 'inet_send: failed'
            return result
                 

        result = self.inet_parse_result(reply)
        
        return result
     
    def inet_idle(self):
        # Check to see if there is a queued message
        if (self.commands.qsize() > 0):
            
            if(CpDefs.LogVerboseInet):
                print 'inet_idle record found'
                
            self.enter_state(CpInetState.SEND,CpInetTimeout.SEND)
            return
            
        # Check for idle timeout then close connection
        if(self.state_timedout() == True):
            self.inet_close()
            self.enter_state(CpInetState.SLEEP, CpInetTimeout.SLEEP)
            
    def inet_sleep(self):
        # Check to see if there is a queued message
        if (self.commands.qsize() > 0):
            self.enter_state(CpInetState.INITIALIZE, CpInetTimeout.INITIALIZE)
            return
        
        # Check to wake send ping once every 60s
        if(self.state_timedout() == True):
            self.enter_state(CpInetState.INITIALIZE, CpInetTimeout.INITIALIZE)
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
        
    def inet_waitnetworkinterface(self):   
        # Allow the PON/POFF commands 120s before
        # attempting to initialize a new connection
        if(self.state_timedout() == True):
            self.enter_state(CpInetState.INITIALIZE, CpInetTimeout.INITIALIZE)
            return False
        
        # TODO: REVIEW AND TEST BEFORE PROD
        with open(CpDefs.WatchdogFilePath, "r+b") as f: #mmap file
            mm = mmap.mmap(f.fileno(), 0)
            
        # Check to see if we have a network interface
        if (mm[:1] == "1"):
            print 'inet_waitnetworkinterface: found successful'
            self.enter_state(CpInetState.INITIALIZE, CpInetTimeout.INITIALIZE)
        else:
            print 'inet_waitnetworkinterface wait retry 1 sec.'
            time.sleep(1)
            
        mm.close()
        
        return True 
              
    def enqueue_packet(self, packet):
        try:
            self.commands.put(packet, block=True, timeout=1)
        except:
            self.__lock.acquire()
            print "CpInet commands queue is full"
            self.__lock.release()

    def inet_parse_result(self, result):
        
        inet_result = CpInetResult()
        
        if(result.find(CpInetResponses.TOKEN_HTTPOK) > -1):
            inet_result.Data = result
            inet_result.ResultCode = CpInetResultCode.RESULT_OK
        elif(result.find(CpInetResponses.TOKEN_HTTPNORESPONSE) > -1):
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

    def watchdog_set_status(self, status):
            
        try:
            with open(CpDefs.WatchdogFilePath, "r+b") as f: #mmap file
                mm = mmap.mmap(f.fileno(), 0)
            
            mm[1:2] = status
            mm.flush()
            mm.close()

        except IOError, e:         
            #self.log.logError('watchdog_set_status: failed (%s)')  e.args[0]
            print 'watchdog_set_status: failed (%s)' % e.args[0]
        except EnvironmentError, ee:
            print 'watchdog_set_status: failed (%s)' % ee.args[0]
        except:
            print 'watchdog_set_status: failed'
            
            
def inetDataReceived(data):
    #print 'Callback function inetDataReceived ', data
    pass
    
if __name__ == '__main__':
    inetThread = CpInet(inetDataReceived)
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
    
    
    