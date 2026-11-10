"""Real optional Windows memory and NVIDIA samples; missing signals stay null."""
import ctypes
import os
import shutil
import subprocess
import time


def sample(process_ids=()):
    result={'monotonic_seconds':time.monotonic(),'available_ram_bytes':None,'total_ram_bytes':None,'process_working_set_bytes':{},'gpu':None}
    if os.name=='nt':
        from ctypes import wintypes
        class Memory(ctypes.Structure):
            _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD)]+[(name,ctypes.c_ulonglong) for name in ('total','available','total_page','available_page','total_virtual','available_virtual','extended')]
        status=Memory();status.length=ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            result.update(available_ram_bytes=status.available,total_ram_bytes=status.total)
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ('peak','working','quota_peak_paged','quota_paged','quota_peak_nonpaged','quota_nonpaged','pagefile','peak_pagefile')]
        kernel=ctypes.windll.kernel32;kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        ctypes.windll.psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
        for identifier in process_ids:
            handle=kernel.OpenProcess(0x1000|0x0010,False,int(identifier))
            if handle:
                try:
                    counter=Counters();counter.cb=ctypes.sizeof(counter)
                    if ctypes.windll.psapi.GetProcessMemoryInfo(handle,ctypes.byref(counter),counter.cb):result['process_working_set_bytes'][str(identifier)]=counter.working
                finally:kernel.CloseHandle(handle)
    executable=shutil.which('nvidia-smi')
    if executable:
        try:
            completed=subprocess.run([executable,'--query-gpu=memory.used,memory.total,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=3,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=False)
            if completed.returncode==0:
                result['gpu']=[dict(zip(('memory_used_mib','memory_total_mib','utilization_percent'),[float(value.strip()) for value in line.split(',')])) for line in completed.stdout.splitlines()]
        except (OSError,ValueError,subprocess.TimeoutExpired):pass
    return result
