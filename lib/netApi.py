# coding:utf-8
import ctypes
from ctypes import wintypes

# 初始化dll  -----------------------------------------
mpr = ctypes.WinDLL('mpr')

ERROR_SUCCESS = 0x0000
ERROR_MORE_DATA = 0x00EA

wintypes.LPDWORD = ctypes.POINTER(wintypes.DWORD)
mpr.WNetGetConnectionW.restype = wintypes.DWORD
mpr.WNetGetConnectionW.argtypes = (wintypes.LPCWSTR,
                                   wintypes.LPWSTR,
                                   wintypes.LPDWORD)


# ----------------------------------------------------
def get_connection(local_name):
    length = (wintypes.DWORD * 1)()
    result = mpr.WNetGetConnectionW(local_name, None, length)
    if result != ERROR_MORE_DATA:
        raise ctypes.WinError(result)
    remote_name = (wintypes.WCHAR * length[0])()
    result = mpr.WNetGetConnectionW(local_name, remote_name, length)
    if result != ERROR_SUCCESS:
        raise ctypes.WinError(result)
    return remote_name.value
