# coding:utf-8
import re
import os
import glob
import shutil
import logging
import itertools
import pprint
import time

import functools
import threading
import tempfile

import nuke
from netApi import get_connection
import TaskOp

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
            # 生成文件夹
            if not os.path.exists(os.path.dirname(target_file)):
                os.makedirs(os.path.dirname(target_file))
            try:
                shutil.copyfile(source_file, target_file)
            except Exception, e:
                # 复制失败
                logger.info(e)
                return False
            else:
                return True
        else:
            # 不需要被复制
            return True
    else:
        # 传入无效参数
        return False


def get_target_copy_path(local_path, **kwargs):
    """
    # 根据一些信息，获取要复制的目标路径
    # 函数的参数这种形式可以适合partial函数，非关键字参数不适合partial
    :param local_path:
    :param kwargs: read,targetDir
    :return:
    """
    if _is_image_on_shared_drive(local_path):
        # 为true,不需要复制
        return None
    if "read" in kwargs:
        # 提供了read参数，表明函数需要read信息
        readName = kwargs["read"]
    # -------------------------------
    copy_dir = tempfile.gettempdir()
    if "targetDir" in kwargs:
        if kwargs["targetDir"] and os.path.isdir(kwargs["targetDir"]):
            copy_dir = kwargs["targetDir"]

    # fileBaseName = os.path.splitext(os.path.basename(local_path))[0]
    # ext = os.path.splitext(os.path.basename(local_path))[-1]
    _data = os.path.basename(local_path).split(".")
    fileBaseName = _data[0]
    folders_in_folder = [d for d in os.listdir(copy_dir) if os.path.isdir(d)]
    # 逻辑为文件夹编号自动提升,文件夹格式为{basename}_{index}
    baseNameFolder = filter(lambda x: re.match("{}_\d+".format(fileBaseName), x), folders_in_folder)
    baseNameFolderIndex = map(lambda x: re.match("{}_(\d+)".format(fileBaseName), x).group(1), baseNameFolder)
    if baseNameFolderIndex:
        maxIndex = max(baseNameFolderIndex, key=lambda x: int(x))
    else:
        maxIndex = None
    if maxIndex:
        # 已经有复制过同名文件
        nextIndex = int(maxIndex) + 1
    else:
        # 没有复制过
        nextIndex = 0
    targetFolderName = "{}_{}".format(fileBaseName, nextIndex)
    targetFilePath = os.path.join(copy_dir, targetFolderName, os.path.basename(local_path))
    return targetFilePath


def _copy_in_thread(sourcePath, targetDir=None, read=None):
    with threading.Lock():
        targetPath = get_target_copy_path(sourcePath, targetDir=targetDir, read=read)
    print  read,sourcePath, targetPath,
    return _copy_file(sourcePath, targetPath)


# --------------------------------------------------
def copy_read_files(targetDir=None):
    """
    复制read files到target dir中，默认targetdir为temp目录
    :param targetDir:
    :return:
    """
    # 收集read信息,
    allRead = nuke.allNodes('Read')
    # 按read进行顺序复制
    # 每个read复制过程启用线程
    results = {}
    for read in allRead:
        readName = read.name()
        files = get_read_files(readName)  # 获取复制文件
        _function_args = map(lambda x: ((x,), {"targetDir": targetDir, "read": readName}), files)
        copyJob = TaskOp.Job(_copy_in_thread, _function_args)
        result = copyJob.run()
        while not copyJob.isFinished:
            time.sleep(0.1)

        results[readName] = result

    # pprint.pprint(results)
