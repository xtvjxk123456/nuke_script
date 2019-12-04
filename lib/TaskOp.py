# coding:utf-8
import threading
import Queue
import time
import sys


# Manager管理任务
# 每个任务串行运行（现阶段）
# 任务内部并发运行

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
            self.inQueue.task_done()  # 完成一个任务
            self.outQueue.put((task, result))
            # print "work done:{}->{}".format(task, result)
            sys.stdout.write("work done:{}->{}\n".format(task, result))
            sys.stdout.flush()
            # res = self.queue.qsize()  # 判断消息队列大小
            # if res > 0:
            #     print "still has job to do"


class Task(object):
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


class Job(object):
    def __init__(self, func, argsIter):
        super(Job, self).__init__()

        # data
        self._func = func
        self._data = argsIter  # 可迭代 .元素为(arg,kwarg)
        self._result = []

        # thread
        self._input = Queue.Queue()
        self._output = Queue.Queue()
        self.numWorker = 6

        # status
        self._isStart = False
        self._isFinished = False

    @property
    def isStart(self):
        return self._isStart

    @property
    def isFinished(self):
        return self._isFinished

    def run(self):
        # 数据
        for data in self._data:
            arg, kwarg = data
            self._input.put_nowait(Task(self._func, *arg, **kwarg))
        # worker
        for n in range(self.numWorker):
            w = Worker(self._input, self._output)
            w.start()

        # 运行
        # while not self._input.empty():
        #     time.sleep(0.1)
        self._input.join()
        output = []
        while self._output.qsize() > 0:
            output.append(self._output.get())
            # self._output.task_done()
        return output

    # class SerialTaskManager(object):


#     # 串行运行task,task使用仅有的quene
#     def __init__(self):
#         super(SerialTaskManager, self).__init__()
#         self.jobs = []
#
#
#     def addJob(self, _Job):
#         if _Job not in self.jobs:
#             self.jobs.append(_Job)
#
#     def wait(self):
#         for j in self.


if __name__ == "__main__":
    def sum(a, b):
        time.sleep(2)
        return a + b


    data = [((1, 2), {}),
            ((3, "2"), {}),
            ((1, 3), {}),
            ((1, 4), {})
            ]
    job = Job(sum, data)
    result = job.run()
    print result
