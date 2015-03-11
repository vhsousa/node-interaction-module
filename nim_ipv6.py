import socket
import traceback
import sys
import array
import time
import datetime
import numpy

__author__ = 'vhsousa'


class NodeInteractionModule:
    __connection_data = {}
    samplingTime = 1
    num_nodes = 3
    __socket = None
    locked = True

    def __init__(self, ip, port, mode, num_nodes=-1, sampling_time=-1):
        try:
            global failed
            failed = 0
            self.__connection_data = {'ip': ip, 'port': port}
            self.locked = True
            print self.__connection_data['ip']
            print self.__connection_data['port']

            self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.__socket.connect((self.__connection_data['ip'], int(self.__connection_data['port'])))
            self.__socket.settimeout(2)

            if mode == 'auto':
                # TODO: Implement the auto discover settings
                print 'Must discover nodes and Ts'
            else:
                print 'Connection as static mode'
                self.samplingTime = sampling_time
                self.num_nodes = num_nodes

                for i in range(1, self.num_nodes + 1):
                    self.__startSampling(i)

        except Exception, e:
            print '[Error] at init'
            print traceback.format_exc()
            sys.exit(0)

    def closeup(self):
        self.locked = False
        for i in range(1, self.num_nodes + 1):
            self.__rebootNode(i)

        self.__socket.close()

    def getdata(self, nodeId):
        mis = []
        result = {}
        tryout = 0
        while self.locked:
            try:

                element = self.__socket.recv(1)

                if element:  # No more elements to read
                    tryout = 0
                    value = self.__bytes2int(element)
                    value = int(value)

                    if value >= 0:
                        mis.append(value)
                    else:

                        mis.append(value + 256)

                    if mis[0] != 104:
                        mis = []
                    else:
                        if len(mis) > 3:
                            if mis[2] != 5:
                                mis = []

                    # Read enough data for one element, so we have to break
                    if len(mis) >= 34:
                        result = self.__processElement(mis, nodeId)
                        mis = []
                        if len(result.keys()) > 0:
                            break
                else:
                    tryout += 1
                    if tryout > nodeId + 1:
                        tryout = 0
                        print 'Lost connection to dispatcher'

            except Exception, e:
                print '[Error] Fetching data: ' + str(e)
                self.__init__(self.__connection_data['ip'], self.__connection_data['port'], 'static', self.num_nodes,
                              self.samplingTime)
                continue

        return result

    def __bytes2int(self, str):
        return int(str.encode('hex'), 16)


    def __rebootNode(self, id):
        print 'Rebooting Node ' + str(self.__idConverterLogical(id))
        self.__socket.send(array.array('B', [102, self.__idConverterLogical(id), 0, 16, 0]).tostring())
        time.sleep(2)

    def __stopSampling(self, id):
        print 'Stopping Sampling Agent Node ' + str(self.__idConverterLogical(id))
        self.__socket.send(array.array('B', [102, self.__idConverterLogical(id), 0, 34, 0]).tostring())
        time.sleep(1)

    def __startSampling(self, id):
        print 'Starting Sampling Agent Node ' + str(self.__idConverterLogical(id))
        self.__socket.send(array.array('B', [102, self.__idConverterLogical(id), 0, 32, 0, 1, 0, 1, 0]).tostring())
        time.sleep(1)
        self.getdata(id)

    # Convert to WSN node number. Specific to IPv6 solutions. Must change this code to other solutions (e.g. Ginseng)
    def __idConverterLogical(self, id):
        return id + 100

    def __processElement(self, mis, nodeId):
        global failed
        try:
            while len(mis) > 10:
                if mis[0] == 104:  # data message must begin with 104
                    misw = numpy.reshape(mis, (2, len(mis) / 2), order="F")  # message in word format
                    misw = misw[0, :] + 256 * misw[1, :]
                    if misw[1] == 5 and misw[2] == self.__idConverterLogical(nodeId):
                        failed = 0
                        return {
                            'node': int(misw[2]),
                            'adc0': round(float(misw[5] * 2.5 / 4096), 3),
                            'adc1': round(float(misw[6] * 2.5 / 4096), 3),
                            'adc2': round(float(misw[7] * 2.5 / 4096), 3),
                            'adc3': round(float(misw[8] * 2.5 / 4096), 3),
                            'par': round(float(misw[9] * 3125 / 512), 0),
                            'tsr': round(float(misw[10] * 625 / 1024), 0),
                            'adc6': round(float(misw[11] * 2.5 / 4096), 3),
                            'adc7': round(float(misw[12] * 2.5 / 4096), 3),
                            'temperature': round(float(misw[13] / 100 - 39.6), 1),
                            'humidity': round(
                                float(misw[14] * 405 / 10000) - float(misw[14] * misw[14] * 28 / 10000000 - 4), 1),
                            'battery': round(float(misw[15] * 2.5 / 2048), 3),
                            'internal-temperature': round(float((misw[16] * 2500 / 4096 - 986) * 0.2817), 1),
                            'timestamp': str(datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
                        }
                    else:
                        failed += 1
                        if failed >= self.num_nodes * 2:
                            failed = 0
                            self.__startSampling(nodeId)

                mis = mis[mis[2] + 16:]
        except Exception, e:
            print 'Exception processing element! '+str(e)
            print traceback.print_exc()
            pass

        return {}
