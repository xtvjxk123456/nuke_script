# coding:utf-8
import re
import os
import glob
import nuke


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
        knobEvaluate = fileKnob.evaluate()
        # 使用此函数时已经可以确定可评估
        frame_flag = re.findall('\%\d+[d|D]', knobEvaluate)
        if frame_flag:
            # 序列类型
            if len(frame_flag) > 1:
                # 无法识别的评估类型
                return []
            frame_pad = int(re.match('\%(\d+)[d|D]', frame_flag[0]).group(1))
            glob_str = re.sub('\%\d+[d|D]', '?' * frame_pad, knobEvaluate)
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
