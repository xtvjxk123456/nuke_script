# coding:utf-8
import re
import os
import glob
import shutil
import logging
from multiprocessing.dummy import Pool as ThreadPool

import nuke
from netApi import get_connection

logger = logging.getLogger("Nuke")
logger.setLevel(logging.DEBUG)


# -------------------------------------------------
def _check_read_file_resolve_type(read):
    # 检查read 类型
    # 一种是file knob(不可用，不能直接评估),需要读取sequence knob
    # 一种是file knob (可用,序列或单帧)，读取后需要计算出文件
    node = nuke.toNode(read)
    fileKnob = node["file"]
    seqKnob = node['sequence']
    read_resolve_type = "unknown"
    if fileKnob.evaluate() and fileKnob.value():
        # 可评估，有参数,优先使用
        # 类型A
        read_resolve_type = "file"
    else:
        seq_values = [p for p in seqKnob.value().split("\n") if p]
        if seq_values:
            # 使用了seq knob(udim import)
            read_resolve_type = "seq"
    return read_resolve_type


def _get_files_from_read(read, resolve_type):
    # 按类型获取文件
    if resolve_type == "file":
        fileKnob = nuke.toNode(read)["file"]
        knobValue = fileKnob.value()
        # 使用此函数时已经可以确定可评估
        frame_flag = re.findall('\%\d+[d|D]', knobValue)
        if frame_flag:
            # 序列类型
            if len(frame_flag) > 1:
                # 无法识别的评估类型
                return []
            frame_pad = int(re.match('\%(\d+)[d|D]', frame_flag[0]).group(1))
            glob_str = re.sub('\%\d+[d|D]', '?' * frame_pad, knobValue)
            files = glob.glob(glob_str)
            return files
        else:
            # 单文件类型
            if os.path.isfile(fileKnob.value()):
                # 可用文件
                return [os.path.normpath(fileKnob.value())]
            else:
                return []

    if resolve_type == "seq":
        # udim
        seqKnob = nuke.toNode(read)["sequence"]
        seq_values = [p for p in seqKnob.value().split("\n") if p and os.path.isfile(p)]
        return seq_values
    return []


def get_read_files(read):
    # 获取文件
    _type = _check_read_file_resolve_type(read)
    files = _get_files_from_read(read, _type)
    return files


# --------------------------------------------------
def _is_image_on_shared_drive(image):
    # 检查图片文件，如果是映射共享的文件，则放弃复制
    # 这里需要提前检测路径是否存在
    drive, _path = os.path.splitdrive(image)
    if drive:
        # 盘符开头
        try:
            get_connection(drive)
        except:
            # 本地路径
            return False
        else:
            return True
    else:
        # 非盘符开头，同时又能表面是存在的文件，则此路径是共享盘路径
        return True


def _copy_file(source_file, target_file):
    # 线程中用到的复制函数，用来复制文件
    # target file 可以接受None
    if source_file and os.path.isfile(source_file):
        # 可以被复制
        if target_file:
            # 需要被复制
            try:
                shutil.copyfile(source_file, target_file)
            except:
                # 复制失败
                return True
            else:
                return False
        else:
            # 不需要被复制
            return True
    else:
        # 传入无效参数
        return False


def get_target_copy_path(local_path, **kwargs):
    # 根据一些信息，获取要复制的目标路径
    return None


# --------------------------------------------------
def main():
    # 收集read信息,
    allRead = nuke.allNodes('Read')
    # 按read进行顺序复制
    # 每个read复制过程启用线程
    copy_thread_pool = ThreadPool()
    for read in allRead:
        readName = read.name()
        files = get_read_files(readName)  # 获取复制文件
        dataList = map(lambda x: (x, get_target_copy_path(x, )), files)  # 获取复制细节
        copyResult = copy_thread_pool.map(lambda x: _copy_file(x[0], x[1]), dataList)  # 这一句不应该发生错误，否则报错内容不太好看,执行复制
        for data, result in zip(dataList, copyResult):
            logger.info("Read:{}:\n\t{}->{}:{}".format(readName, data[0], data[1], result))
