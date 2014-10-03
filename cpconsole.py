import threading
import time
import Queue


class CpConsole(threading.Thread):
    
    #def __init__(self, taskMgr, modem, comm, rfThread, inetThread, *args):
    def __init__(self, taskMgr, *args):
        self._target = self.console_handler
        self._args = args
        self.__lock = threading.Lock()
        self.closing = False # A flag to indicate thread shutdown
        self.taskMgr = taskMgr
        threading.Thread.__init__(self)
        
    def run(self):
        self._target(*self._args)
    
    def comm_callback_handler(self, result):
        print "comm_callback_handler ", result
        
    def shutdown_thread(self):
        print 'shutting down EchoBasePPP...'

        self.taskMgr.getRfThread().shutdown_thread()
        self.taskMgr.getInetThread().shutdown_thread()
        self.taskMgr.getDbThread().shutdown_thread()
        self.taskMgr.getLedThread().shutdown_thread()
        self.taskMgr.shutdown_thread()
        
        
        while(self.taskMgr.getRfThread().isAlive()):
            print 'waiting for CpRf shutdown isAlive=', self.taskMgr.getRfThread().isAlive()
            time.sleep(.5)
        while( self.taskMgr.getInetThread().isAlive()):
            print 'waiting for CpInet shutdown isAlive=', self.taskMgr.getInetThread().isAlive()
            time.sleep(.5)
        while(self.taskMgr.getDbThread().isAlive()):
            print 'waiting for CpDbManager shutdown isAlive=', self.taskMgr.getDbThread().isAlive()
            time.sleep(.5)
        while(self.taskMgr.getLedThread().isAlive()):
            print 'waiting for CpLed shutdown isAlive=', self.taskMgr.getLedThread().isAlive()
            time.sleep(.5)   
        while(self.taskMgr.isAlive()):
            print 'waiting for CpTaskManager shutdown isAlive=', self.taskMgr.isAlive()
            time.sleep(.5)
        
        print 'waiting for CpRf shutdown isAlive=', self.taskMgr.getRfThread().isAlive()
        print 'waiting for CpInet shutdown isAlive=', self.taskMgr.getInetThread().isAlive()
        print 'waiting for CpDbManager shutdown isAlive=', self.taskMgr.getDbThread().isAlive()
        print 'waiting for CpLed shutdown isAlive=', self.taskMgr.getLedThread().isAlive()
        print 'waiting for CpTaskManager shutdown isAlive=', self.taskMgr.isAlive()

        self.__lock.acquire()
        self.closing = True
        self.__lock.release()
        
    def console_handler(self):
        
        input=1
        while not self.closing:
            # get keyboard input
            input = raw_input(">> ")
                # Python 3 users
                # input = input(">> ")
            if input == 'exit' or input == 'EXIT':
                self.shutdown_thread()
            elif input == 'isalive':
                print 'isAlive ', self.taskMgr.isAlive()
            elif input == 'xrf':
                print 'shutdown CpRf'
                self.taskMgr.getRfThread().shutdown_thread()
                pass
            elif input == '?':
                self.taskMgr.logStats()
            elif input == 'date':
                print 'time:', time.strftime("%d/%m/%Y %H:%M:%S")
                
            time.sleep(.005)