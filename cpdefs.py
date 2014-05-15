class CpDefs:
    Debug = True
    DebugVerbose = True
    Apn = "c1.korem2m.com"
    ApnUserid = ""
    ApnPassword = ""
    #ModemPort = "/dev/tty.usbserial-FTELSNMW"
    ModemPort = "/dev/ttyO4"
    ModemBaudrate = 115200
    #RfPort = "/dev/tty.usbserial-FTELSNMW"
    RfPort = "/dev/ttyO2"
    RfBaudrate = 38400
    PurgeDbOnStartup = True
    VacuumDbOnStartup = True
    InetHost = "appserver05.cphandheld.com"
    InetPort = 1337
    InetRoute = "/pings"
    InetPostParams = "POST %s HTTP/1.1\r\ncontent-type:application/json\r\nhost: %s\r\ncontent-length:%d\r\n\r\n%s"
    
    
    