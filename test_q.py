import queue

que = queue.Queue()


def printQueue():
    while True: 
        try:
            print(f"Get {que.get(block=False)}")
        except queue.Empty: 
            print("Que empty Exception occurred")
            break
for i in range(5):
    que.put(i)
    print(f"{i} is put")

printQueue()
