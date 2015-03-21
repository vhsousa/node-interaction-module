from Queue import Queue
import threading
import time
from nim_ipv6 import NodeInteractionModule

__author__ = 'vhsousa'

dispatcher = NodeInteractionModule('10.3.3.112',12345,'static',3,1,5)

queue = Queue()
t = threading.Thread(target= dispatcher.get_data, args=(queue, ))


print 'Starting Thread'
t.start()

while True:
    time.sleep(1)
    node_reads = {}
    node_reads = dispatcher.process(queue)

    print node_reads

t.join()