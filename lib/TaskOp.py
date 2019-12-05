# coding:utf-8
import threading
import Queue
import time
import sys
from collections import deque


# 每个job串行运行（现阶段）
# job内部并发运行

class Worker(threading.Thread):
    def __init__(self, inQueue, outQueue):
        super(Worker, self).__init__()
        self.inQueue = inQueue
        self.outQueue = outQueue

    def run(self):
        # 线程不持续运行时，会自动退出
        while not self.inQueue.empty():
            task = self.inQueue.get(block=True, timeout=20)  # 接收消息,无需长时间等待
            # 获取了task
            result = task.run()
            self.inQueue.task_done()
            if self.inQueue.empty():
                nextJob.set()
                # 所有task完成，设置执行下一个job
            self.outQueue.put((task, result))
            # sys.stdout.write("work done:{}->{}\n".format(task, result))
            # sys.stdout.flush()
            # res = self.queue.qsize()  # 判断消息队列大小
            # if res > 0:
            #     print "still has job to do"


class Task(object):
    # worker 和task时相对应的
    def __init__(self, func, *args, **kwargs):
        super(Task, self).__init__()
        self._func = func
        self._args = args if args else ()
        self._kwarg = kwargs if kwargs else {}

    def run(self):
        try:
            result = self._func(*self._args, **self._kwarg)
        except Exception, e:
            result = e
        return result

    def __repr__(self):
        return "<Task at {}>[{}({},{})]".format(id(self), self._func.func_name, self._args, self._kwarg)


# -----------------------------------------
class Job(object):
    def __init__(self):
        super(Job, self).__init__()
        # thread
        self._input = Queue.Queue()
        self._output = Queue.Queue()
        self.numWorker = 6
        # status
        self._isFinished = False

        # data
        self._result = []

    @property
    def isFinished(self):
        return self._isFinished

    @property
    def input(self):
        return self._input

    def run(self):
        # worker
        for n in range(self.numWorker):
            w = Worker(self._input, self._output)
            w.start()

        # 运行
        # while not self._input.empty():
        #     time.sleep(0.1)
        self._input.join()
        self._isFinished = True
        output = []
        while self._output.qsize() > 0:
            output.append(self._output.get())
            # self._output.task_done()
        return output


nextJob = threading.Event()


class SerialProducer(threading.Thread):
    def __init__(self, jobDetails, queue):
        super(SerialProducer, self).__init__()
        # jobDetails = [(func,iters),...]
        self._jobDetails = jobDetails
        self._containter = queue

    def run(self):
        # 容器空了，并不表示任务完成了
        # 只有确定任务完成了，才可以进行下一步
        jobDetails = deque(self._jobDetails)
        while True:
            if jobDetails:
                # 数据没有消耗完
                if len(jobDetails) == len(self._jobDetails):
                    jobDetail = jobDetails.popleft()
                else:
                    if nextJob.is_set():
                        # 只有再event设置的情况下进行下一步
                        jobDetail = jobDetails.popleft()
                    else:
                        continue
                func, args_kwargs_iter = jobDetail
                for a in args_kwargs_iter:
                    args, kwargs = a
                    task = Task(func, *args, **kwargs)
                    self._containter.put(task)
                nextJob.clear()
                # --------------------------
                sys.stdout.write("{:-^30}\n".format("next job"))
                sys.stdout.flush()
            else:
                # 消耗完了
                break


class SerialJobManager(object):
    def __init__(self):
        super(SerialJobManager, self).__init__()
        self.mainJob = Job()
        self.jobDetails = []

    def addJob(self, jobDetail):
        self.jobDetails.append(jobDetail)

    def execute(self):
        # 需要生产线程
        generate_data = SerialProducer(self.jobDetails, self.mainJob.input)
        generate_data.start()

        # 开始执行任务
        result = self.mainJob.run()
        return result


if __name__ == "__main__":
    def sum(a, b):
        time.sleep(2)
        return a + b


    jobA_data = [((1, 2), {}),
                 ((3, "2"), {}),
                 ((1, 3), {}),
                 ((1, 4), {})
                 ]
    jobB_data = [((1, 2), {}),
                 ((3, "2"), {}),
                 ((1, 3), {}),
                 ((1, 4), {}),
                 ((1, 2), {})
                 ]

    m = SerialJobManager()
    m.addJob((sum, jobA_data))
    m.addJob((sum, jobB_data))
    result = m.execute()
    print result
