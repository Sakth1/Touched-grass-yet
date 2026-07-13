import platform
import socket
import psutil
import getpass
import os
from datetime import datetime


from src.utils.models import WindowsSystemInfo


def get_system_info() -> WindowsSystemInfo:

    return WindowsSystemInfo(
        OS=platform.system(),
        Release=platform.release(),
        Version=platform.version(),
        Platform=platform.platform(),
        Machine=platform.machine(),
        Architecture=platform.architecture(),
        Processor=platform.processor(),
        Node=platform.node(),
        Hostname=socket.gethostname(),
        CurrentUser=getpass.getuser(),
        CurrentDirectory=os.getcwd(),
        CurrentTime=datetime.now(),
        UTC=datetime.utcnow(),
        BootTime=datetime.fromtimestamp(psutil.boot_time()),
    )
