import socket
import traceback
import sys
# -*- coding: utf-8 -*-
import array
import time
import datetime
import numpy

__author__ = 'vhsousa'


class NodeInteractionModule:
    __connection_data = {}
    sampling_time = 1
    num_nodes = 3
    mailer = None
    responsible = ''
    locked = True
    __socket = None
    __max_retries = 5
    __retries = 0


    def __init__(self, ip, port, mode, num_nodes=-1, sampling_time=-1, max_retries=5):
        try:
            global failed
            failed = 0
            self.__connection_data = {'ip': ip, 'port': port}
            self.locked = True
            # print self.__connection_data['ip']
            # print self.__connection_data['port']

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

            self.__max_retries = max_retries
            self.__retries = 0
        except Exception, e:
            print 'Reconnecting...'
            print traceback.print_exc()
            self.__retries += 1
            if self.__retries == max_retries and self.mailer is not None:
                self.mailer.send_mail(self.responsible, '[Network IPv6] Connection Problem',
                                      'Hello Admin,\n\n The connection to the WSN has reached a maximum of ' + str(
                                          self.__retries) + '. Please check with is wrong.\n\nIP: ' + str(
                                          ip) + '\nPORT: ' + port + '\n\n Thanks')
            time.sleep(5)
            self.__init__(ip, port, mode, num_nodes, sampling_time, self.__max_retries)


    def closeup(self):
        self.locked = False
        for i in range(1, self.num_nodes + 1):
            self.__rebootNode(i)

        self.__socket.close()

    def get_data(self, nodeId):
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
                        self.__init__(self.__connection_data['ip'], self.__connection_data['port'], 'static',
                                      self.num_nodes,
                                      self.samplingTime,
                                      self.__max_retries)
                        time.sleep(5)


            except Exception, e:
                print '[Error] Fetching data: ' + str(e)
                self.__init__(self.__connection_data['ip'], self.__connection_data['port'], 'static', self.num_nodes,
                              self.samplingTime, self.__max_retries)
                continue

        return result

    def __bytes2int(self, str):
        return int(str.encode('hex'), 16)


    def __rebootNode(self, id):
        print 'Rebooting Node ' + str(self.__idConverterLogical(id))
        self.__socket.send(array.array('B', [102, self.__idConverterLogical(id), 0, 16, 0]).tostring())
        time.sleep(2)
        self.__socket.send(array.array('B', [102, self.__idConverterLogical(id), 0, 16, 0]).tostring())

    def __stopSampling(self, id):
        print 'Stopping Sampling Agent Node ' + str(self.__idConverterLogical(id))
        self.__socket.send(array.array('B', [102, self.__idConverterLogical(id), 0, 34, 0]).tostring())
        time.sleep(1)

    def __startSampling(self, id):
        print 'Starting Sampling Agent Node ' + str(self.__idConverterLogical(id))
        self.__socket.send(array.array('B', [102, self.__idConverterLogical(id), 0, 32, 0, 1, 0, 1, 0]).tostring())
        time.sleep(1)
        self.get_data(id)

    # Convert to WSN node number. Specific to IPv6 solutions. Must change this code to other solutions (e.g. Ginseng)
    def __idConverterLogical(self, id):
        return id + 100

    def get_units(self):
        return {'adc': 'volt',
                'par': 'lux',
                'tsr': 'lux',
                'temperature': 'C',
                'humidity': '%',
                'battery': 'volt',
                'internal-temperature': 'C'
                }

    def __processElement(self, mis, nodeId):
        global failed
        try:
            while len(mis) > 10:
                if mis[0] == 104:  # data message must begin with 104
                    misw = numpy.reshape(mis, (2, len(mis) / 2), order="F")  # message in word format
                    misw = misw[0, :] + 256 * misw[1, :]
                    if misw[1] == 5 and misw[2] == self.__idConverterLogical(nodeId):
                        failed = 0
                        from pytz import utc

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
                            'timestamp': str(
                                datetime.datetime.now().replace(tzinfo=utc).strftime("%Y-%m-%d %H:%M:%S %Z"))
                        }
                    else:
                        failed += 1
                        if failed >= self.num_nodes * 2:
                            failed = 0
                            self.__startSampling(nodeId)

                mis = mis[mis[2] + 16:]
        except Exception, e:
            print 'Exception processing element! ' + str(e)
            print traceback.print_exc()
            pass

        return {}
