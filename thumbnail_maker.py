# thumbnail_maker.py
import time
import os
import logging
from urllib.parse import urlparse
from urllib.request import urlretrieve
import PIL
from PIL import Image
from threading import Thread, Lock
from queue import Queue
import multiprocessing
import pdb
from imglst import IMG_URLS
logging.basicConfig(level=logging.DEBUG,format ="%(processName)s::%(threadName)s: %(message)s")
#logging.basicConfig(filename='logfile.log', level=logging.DEBUG)

class ThumbnailMakerService(object):
    def __init__(self, home_dir='.'):
        self.home_dir = home_dir
        self.input_dir = self.home_dir + os.path.sep + 'incoming'
        self.output_dir = self.home_dir + os.path.sep + 'outgoing'
        self.img_queue = multiprocessing.JoinableQueue()
        self.dl_size = 0
        self.resized_size =  multiprocessing.Value('i', 0)

    def download_image(self,dl_que, dl_size_lock):
        while not dl_que.empty():
            try:
                url = dl_que.get(block=False)
                img_filename = urlparse(url).path.split('/')[-1]
                dest_path = self.input_dir + os.path.sep + img_filename
                urlretrieve(url, dest_path)
                with dl_size_lock:
                    self.dl_size += os.path.getsize(dest_path)
                self.img_queue.put(img_filename)
                dl_que.task_done()
                logging.info(f"-{multiprocessing.current_process().pid}:: downloaded : {img_filename}")

            except queue.Empty:
                logging.info("Queue is Empty")


    def download_images(self, img_url_list):

        os.makedirs(self.input_dir, exist_ok=True)
        logging.info("beginning image downloads")

        start = time.perf_counter()
        for url in img_url_list:
            # download each image and save to the input dir 
            img_filename = urlparse(url).path.split('/')[-1]
            dest_path = self.input_dir + os.path.sep + img_filename
            urlretrieve(url, dest_path)
            self.img_queue.put(img_filename)
            logging.info(f"- downloaded: {img_filename}")
        end = time.perf_counter()

        self.img_queue.put(None)
        logging.info("downloaded {} images in {} seconds".format(len(img_url_list), end - start))

    def perform_resizing(self):
        # validate inputs
        if not os.listdir(self.input_dir):
            return
        os.makedirs(self.output_dir, exist_ok=True)

        logging.info("beginning image resizing")
        target_sizes = [32, 64, 200]
        num_images = len(os.listdir(self.input_dir))

        start = time.perf_counter()
        while True:
            filename =  self.img_queue.get()
            if filename:
                logging.info(f"resizing image :{filename}")
                orig_img = Image.open(self.input_dir + os.path.sep + filename)
                for basewidth in target_sizes:
                    img = orig_img
                    # calculate target height of the resized image to maintain the aspect ratio
                    wpercent = (basewidth / float(img.size[0]))
                    hsize = int((float(img.size[1]) * float(wpercent)))
                    # perform resizing
                    img = img.resize((basewidth, hsize), PIL.Image.LANCZOS)

                    # save the resized image to the output dir with a modified file name 
                    new_filename = os.path.splitext(filename)[0] + \
                        '_' + str(basewidth) + os.path.splitext(filename)[1]
                    dest_file = self.output_dir + os.path.sep + new_filename
                    img.save(dest_file)

                    with self.resized_size.get_lock():
                        self.resized_size.value += os.path.getsize(dest_file)

                os.remove(self.input_dir + os.path.sep + filename)
                logging.info(f"done resizing:{multiprocessing.current_process().pid}: {self.input_dir + os.path.sep + new_filename}")
                self.img_queue.task_done()

            else:
                self.img_queue.task_done()
                break

        end = time.perf_counter()
        logging.info("created thumbnails in {} seconds".format(end - start))
        

    def make_thumbnails(self, img_url_list):
        logging.info("START make_thumbnails")
        start = time.perf_counter()

        dl_que = Queue()
        dl_size_lock = Lock()
        for img_url in img_url_list:
            dl_que.put(img_url)

        num_dl_threads = 4 #
        for _ in range(num_dl_threads):
            t = Thread(target=self.download_image, args=(dl_que,dl_size_lock))
            t.start()

        num_cpu_core = multiprocessing.cpu_count()

        time.sleep(2) # 최초 다운로드가 완료되어 img_queue 에 몇개의 자료가 들어 갈 때까지 기다린다.
        for _ in range(num_cpu_core):
            print("----") # img_queue 에 파일이름이 들어가고 Process 가 만들어지는지체크
            p = multiprocessing.Process(target=self.perform_resizing)
            p.start()


        dl_que.join() # que 에 파일목록 작성 완료 대기
        # perform_resize 가 Poison pill: None 으로 중지 하므로 프로세스 개수만큼 None삽입

        for _ in range(num_cpu_core):
            self.img_queue.put(None)

        end = time.perf_counter()


        logging.info("END thumbnail created in {} seconds".format(end - start))
        logging.info(f"Total Downloaded File Size {self.dl_size} : Thumbnailed Size:{self.resized_size.value}")

if __name__ == "__main__":
    tt = ThumbnailMakerService()
    tt.make_thumbnails(IMG_URLS)
