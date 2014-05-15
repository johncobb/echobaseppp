
import threading
import time
import Queue
import subprocess
import sqlite3
import json
import time
import binascii
import os
import cpcobs
from cprfmsg import CpRfMsg


class CpDbManager(threading.Thread):

    
    
    def __init__(self, inetThread, *args):
        self._target = self.task_handler
        self._args = args
        self.__lock = threading.Lock()
        self.records = Queue.Queue(10)
        self.closing = False # A flag to indicate thread shutdown
        self.inetThread = inetThread
        
        self.db = CpDb()
        threading.Thread.__init__(self)
        
    def run(self):
        self._target(*self._args)
        
    def task_handler(self):
        

            
        # Initialize database
        self.db.initDb()
        
        while not self.closing:
            
            if (self.records.qsize() > 0):
                # Pop the tag_info from the queue
                tag_info = self.records.get(True)
                
                #Production (saving raw bytes)
                #self.db_handler(tag_info)
                # Debug (saving readable tag info)
                self.db_handler_debug(tag_info)
                self.db_handler(tag_info)
                # Production (sending raw bytes)
                #self.inet_handler(tag_info)
                # Debug (sending json)
                self.inet_handler_debug(tag_info)

                self.records.task_done()
            # Let database breathe
            time.sleep(.0005)
            
            
    def inet_handler_debug(self, tag_info):
        # Hydrate the message 
        msg = CpRfMsg(tag_info)
        self.inetThread.enqueue_packet(msg.toJson())
    
    def inet_handler(self, tag_info):
        # Enqueue message to send to server
        self.inetThread.enqueue_packet(tag_info)
        
    def db_handler_debug(self, tag_info):
        # Hydrate the message 
        msg = CpRfMsg(tag_info)
        # Write record to database
        self.db.updateRecord(msg.shortAddr, binascii.hexlify(tag_info))
        
    def db_handler(self, tag_info):
        # Hydrate the message 
        msg = CpRfMsg(tag_info)
        # TODO: handler for writing raw bytes to database
        self.db.updateRecordBlob(msg.shortAddr, tag_info)
        pass
        
    def enqueue_record(self, record):
        try:
            self.records.put(record, block=True, timeout=1)
        except:
            self.__lock.acquire()
            print "The queue is full"
            self.__release()
            
    def shutdown_thread(self):
        print 'shutting down CpDbManager...'
        self.__lock.acquire()
        self.closing = True
        self.__lock.release()


class CpDb():
    
    dbPath = 'test.db'
    
    def initDb(self):
        
        # Remove file every time for now until version is implemented
        if(os.path.isfile(self.dbPath)):
            os.remove(self.dbPath)
            
        # Add version checking,vacuum etc...
        print 'Initializing database ', self.dbPath
        self.createTables()
        
        
        
    def createTables(self):
        
        conn = sqlite3.connect(self.dbPath)
        
        print "Database opened successfully"
        
        conn.execute("CREATE TABLE TAGS (ID INT PRIMARY KEY NOT NULL, TAG CHAR(128), TIMESTAMP INT);")
        conn.execute("CREATE TABLE TAGS2 (ID INT PRIMARY KEY NOT NULL, TAG CHAR(128), TAGBLOB BLOB, TIMESTAMP INT);")
        #conn.execute("CREATE TABLE VERSION (REV INT);")
        
        print "Table created successfully"
        
        conn.execute("INSERT INTO TAGS (ID, TAG, TIMESTAMP) VALUES (1, 'DUMMY', 0)")
        conn.execute("INSERT INTO TAGS2 (ID, TAG, TAGBLOB, TIMESTAMP) VALUES (1, 'DUMMY', NULL, 0)")

       
        conn.commit()
        print "Records created successfully"
        conn.close()
        
    
    def queryTable(self):
        
        conn = sqlite3.connect(self.dbPath)
        
        cursor = conn.execute("SELECT ID, TAG, TIMESTAMP  from TAGS")
        for row in cursor:
            print "ID = ", row[0]
            print "TAG = ", row[1]
            print "TIMESTAMP = ", row[2], "\n"
        
        print "Operation completed successfully";
        conn.close()
        
        
    def updateTable(self, tagId, tagInfo):
        
        conn = sqlite3.connect(self.dbPath)
        #sql = "INSERT OR REPLACE INTO TAGS (ID, TAG, TIMESTAMP) VALUES (1, '0123456789ABCDEF1', DATETIME('NOW'))"
        
        
        sql = "INSERT OR REPLACE INTO TAGS (ID, TAG, TIMESTAMP) VALUES (%d, '%s', DATETIME('NOW'))", tagId, tagInfo
        
        cursor = conn.execute(sql)
        
        conn.commit()
        
        print "Operation completed successfully";
        conn.close()
        
        
        
    def updateRecord(self, tagId, tagInfo):
        
        conn = sqlite3.connect(self.dbPath)
        #sql = "INSERT OR REPLACE INTO TAGS (ID, TAG, TIMESTAMP) VALUES (1, '0123456789ABCDEF1', DATETIME('NOW'))"
        
        
        sql = "INSERT OR REPLACE INTO TAGS (ID, TAG, TIMESTAMP) VALUES (%d, '%s', DATETIME('NOW'))" % (tagId, tagInfo)
        
        cursor = conn.execute(sql)
        
        conn.commit()
        
        print "Operation completed successfully";
        conn.close() 
        
    def updateRecordBlob(self, tagId, tagInfo):
        
        conn = sqlite3.connect(self.dbPath)
        #sql = "INSERT OR REPLACE INTO TAGS (ID, TAG, TIMESTAMP) VALUES (1, '0123456789ABCDEF1', DATETIME('NOW'))"
        
        
        
        sql = "INSERT OR REPLACE INTO TAGS2 (ID, TAG, TAGBLOB, TIMESTAMP) VALUES (?, ?, ?, DATETIME('NOW'))"
        
        cursor = conn.execute(sql, (tagId, binascii.hexlify(tagInfo), buffer(tagInfo)))
        
        conn.commit()
        
        print "Operation completed successfully";
        conn.close()                     
        
    def deleteRecord(self):
        
        conn = sqlite3.connect(self.dbPath)
        sql = "DELETE FROM TAGS WHERE ID = 2"
        
        cursor = conn.execute(sql)
        
        conn.commit()
        
        print "Operation completed successfully";
        conn.close()   
        
    def vacuumDb(self):
    
        #call(["sqlite3 test.db", "\"VACUUM;\""])
        
        
        proc = subprocess.Popen(['sqlite3', self.dbPath, 'VACUUM;'] , stdout=subprocess.PIPE)
        
        response = proc.communicate()
        
        print "Results:"
        print response[0]
        
        
if __name__ == '__main__':
    
    cpdb = CpDb()
    
    #cpdb.createTables() 
    #cpdb.updateTable()
    cpdb.queryTable()    
     
    cpdb.deleteRecord()
    cpdb.queryTable()
    #cpdb.vacuumDb()  
    
    
    