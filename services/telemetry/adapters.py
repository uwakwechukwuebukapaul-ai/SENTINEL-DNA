from .normalizer import EventNormalizer
class _Adapter:
    source = "generic"
    def normalize(self, event): return EventNormalizer().normalize(event, self.source)
class WindowsEventAdapter(_Adapter): source = "windows"
class LinuxEventAdapter(_Adapter): source = "linux"
class SyslogAdapter(_Adapter): source = "syslog"
