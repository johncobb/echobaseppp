class CpEncoding:
    CpRaw = 0
    CpJson = 1
    CpJsonCustom = 2
    CpJsonCustomBase64 = 3

class CpDefs:
    Debug = True
    LogVerbose = True
    LogToStdOut = False
    LogPacketLevel = False
    LogVerboseRf = False
    LogVerboseDb = False
    LogVerboseInet = False
    LogVerboseTaskMgr = False
    LogEncodedMessage = False
    Apn = "c1.korem2m.com"
    ApnUserid = ""
    ApnPassword = ""
    #ModemPort = "/dev/tty.usbserial-FTELSNMW"
    ModemPort = "/dev/ttyO4"
    ModemBaudrate = 115200
    #RfPort = "/dev/tty.usbserial-FTELSNMW"
    RfMsgThrottleTimeout = 5
    RfMsgLen = 37
    RfPort = "/dev/ttyO2"
    RfBaudrate = 38400
    PurgeDbOnStartup = True
    VacuumDbOnStartup = True
    #InetHost = "appserver05.cphandheld.com"
    #InetPort = 1337
    #InetRoute = "/pings"
    InetHost = "unison-alt.cphandheld.com"
    InetPort = 80
    InetRoute = "/api/bitstorm/ping"
    InetPostParams = "POST %s HTTP/1.1\r\ncontent-type:application/json\r\nhost: %s\r\ncontent-length:%d\r\n\r\n%s"
    InetTimeout = 5
    WatchdogFilePath = "/home/root/watchdog/info.txt"
    WatchdogWaitNetworkInterface = True
    Encoding = CpEncoding.CpJsonCustomBase64

    
    
class CpGpioMap():
    GPIO_CELLENABLE = "P9_12"
    GPIO_CELLRESET = "P9_23"
    GPIO_CELLONOFF = "P8_12"
    GPIO_CELLPWRMON = "P9_42"
    GPIO_LED1 = "P8_14"
    GPIO_LED2 = "P8_15"
    
class CpSystemState:
    INITIALIZE = 0
    IDLE = 1
    CONNECT = 2
    CLOSE = 3
    SLEEP = 4
    SEND = 5
    WAITNETWORKINTERFACE = 6
