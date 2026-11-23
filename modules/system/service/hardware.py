import logging
import os
import platform
import socket
import subprocess
import time
from datetime import datetime

from django.core.cache import cache

try:
    import psutil
except ImportError:  # 未安装依赖时仍返回静态信息
    psutil = None

CACHE_KEY = 'sys:hardware'
CACHE_TTL = 8
CPU_SAMPLE_INTERVAL = 0.3

logger = logging.getLogger(__name__)


def _os_name():
    system = platform.system()
    if system == 'Darwin':
        version = platform.mac_ver()[0] or platform.release()
        return f'macOS {version}'
    if system == 'Windows':
        return f'Windows {platform.release()}'
    return f'{system} {platform.release()}'.strip()


def _cpu_model():
    if platform.system() == 'Darwin':
        try:
            output = subprocess.check_output(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                timeout=1,
                text=True,
            ).strip()
            if output:
                return output
        except Exception:
            pass

    if platform.system() == 'Linux':
        try:
            with open('/proc/cpuinfo', encoding='utf-8') as file:
                for line in file:
                    if line.lower().startswith('model name'):
                        return line.split(':', 1)[1].strip()
        except OSError:
            pass

    return platform.processor() or platform.machine()


def _static_info():
    return {
        'hostname': socket.gethostname(),
        'os': _os_name(),
        'arch': platform.machine(),
        'cpu': {
            'model': _cpu_model(),
            'cores': os.cpu_count() or 0,
            'percent': None,
            'loadAvg': [],
        },
        'memory': {'total': None, 'used': None, 'percent': None},
        'disk': {'total': None, 'used': None, 'percent': None},
        'uptimeSeconds': None,
        'battery': None,
        'collectedAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'available': False,
    }


def _load_avg():
    try:
        return [round(value, 2) for value in psutil.getloadavg()]
    except Exception:
        return []


def _battery_info():
    try:
        battery = psutil.sensors_battery()
    except Exception as exc:
        logger.warning('读取电池信息失败: %s', exc)
        return None
    if not battery:
        return None
    return {
        'percent': round(battery.percent),
        'charging': bool(battery.power_plugged),
    }


def _collect():
    data = _static_info()
    if psutil is None:
        return data

    data['available'] = True

    try:
        data['cpu']['percent'] = round(psutil.cpu_percent(interval=CPU_SAMPLE_INTERVAL), 1)
        data['cpu']['loadAvg'] = _load_avg()

        memory = psutil.virtual_memory()
        data['memory'] = {
            'total': memory.total,
            'used': memory.total - memory.available,
            'percent': round(memory.percent, 1),
        }

        disk = psutil.disk_usage(os.path.abspath(os.sep))
        data['disk'] = {
            'total': disk.total,
            'used': disk.used,
            'percent': round(disk.percent, 1),
        }

        data['uptimeSeconds'] = int(time.time() - psutil.boot_time())
        data['battery'] = _battery_info()
    except Exception as exc:
        logger.warning('读取硬件信息失败: %s', exc)
        data['available'] = False

    data['collectedAt'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return data


def get_hardware_data(force=False):
    if not force:
        cached = cache.get(CACHE_KEY)
        if cached:
            return cached

    data = _collect()
    cache.set(CACHE_KEY, data, CACHE_TTL)
    return data
