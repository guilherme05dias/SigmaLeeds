import hashlib
import socket

def get_hardware_id() -> str:
    try:
        import wmi
        c = wmi.WMI()
        disk_uuid = ""
        for disk in c.Win32_LogicalDisk(DeviceID="C:"):
            disk_uuid = disk.VolumeSerialNumber or ""
            break
            
        cpu_serial = ""
        for cpu in c.Win32_Processor():
            cpu_serial = cpu.ProcessorId or ""
            break
            
        hostname = socket.gethostname()
        raw_id = f"{disk_uuid}-{cpu_serial}-{hostname}"
    except Exception:
        # Fallback se WMI falhar
        import uuid
        hostname = socket.gethostname()
        mac = uuid.getnode()
        raw_id = f"fallback-{hostname}-{mac}"
        
    return hashlib.sha256(raw_id.encode('utf-8')).hexdigest()
