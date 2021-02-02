import queue
import threading,time

que = queue.Queue()


def printQueue():
    while not que.empty():
        try:
            time.sleep(1)
            print(f"Get {que.get(block=False)}")
        except queue.Empty: 
            print("Que empty Exception occurred")

for i in range(11):
    que.put(i)
    print(f"{i} is put")

for _ in range(2):
    t = threading.Thread(target=printQueue)
    t.start()

