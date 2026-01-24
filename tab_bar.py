# Custom kitty tab bar with right-side system stats
# Pure Python implementation - no external shell scripts

import os
import threading
import time
from kitty.boss import get_boss
from kitty.fast_data_types import Screen, add_timer
from kitty.tab_bar import (
    DrawData,
    ExtraData,
    Formatter,
    TabBarData,
    as_rgb,
    draw_attributed_string,
    draw_title,
)

# Tab separator character
# TAB_SEPARATOR = "│"
TAB_SEPARATOR = "⡇"


# Global state
timer_id = None
cached_status = ""
status_lock = threading.Lock()
last_fetch_time = 0.0
REFRESH_INTERVAL = 2.0

# Cache for disk/network rate calculations
_prev_disk = {"time": 0, "read": 0, "write": 0}
_prev_net = {"time": 0, "rx": 0, "tx": 0}

MEMORY_THRESHOLD = 80.0  # percentage

# Pre-calculate colors (will be set on first draw)
_colors_cached = False
_tab_bg_active = 0
_tab_fg_active = 0

# Get CPU core count once at startup
try:
    with open("/proc/cpuinfo", "r") as f:
        cpu_cores = sum(1 for line in f if line.startswith("processor\t:"))
except:
    cpu_cores = 8  # fallback


def _clean_title(title: str) -> str:
    """Extract process name from command with arguments."""
    if not title:
        return title

    # Split by spaces and take first part
    first_part = title.split()[0]

    # If it's a path, extract just the executable name
    if "/" in first_part:
        first_part = first_part.split("/")[-1]

    return first_part


def _human_bytes(b: float, suffix: str = "B") -> str:
    """Convert bytes to human readable format."""
    for unit in ("", "K", "M", "G", "T"):
        if abs(b) < 1024:
            if unit == "":
                return f"{b:.0f}{suffix}"
            return f"{b:.1f}{unit}{suffix}"
        b /= 1024
    return f"{b:.1f}P{suffix}"


def _get_cpu_load() -> str:
    """Get CPU load average."""
    try:
        with open("/proc/loadavg", "r") as f:
            load = float(f.read().split()[0])
        return f"L:{load:.2f}"
    except Exception:
        return ""


def _get_memory() -> str:
    """Get memory usage percentage."""
    try:
        with open("/proc/meminfo", "r") as f:
            info = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    info[parts[0].rstrip(":")] = int(parts[1])

        total = info.get("MemTotal", 0)
        available = info.get("MemAvailable", 0)

        if total > 0 and available > 0:
            used_pct = (total - available) / total * 100
            return f"M:{used_pct:.0f}%"
    except Exception:
        pass
    return ""


def _get_uptime() -> str:
    """Get system uptime."""
    try:
        with open("/proc/uptime", "r") as f:
            uptime_sec = int(float(f.read().split()[0]))

        days = uptime_sec // 86400
        hours = (uptime_sec % 86400) // 3600
        minutes = (uptime_sec % 3600) // 60

        if days > 0:
            return f"{days}d{hours}h"
        if hours > 0:
            return f"{hours}h{minutes}m"
        return f"{minutes}m"
    except Exception:
        return ""


def _get_disk_io() -> str:
    """Get disk I/O rates."""
    global _prev_disk
    try:
        now = time.monotonic()
        read_sectors = 0
        write_sectors = 0

        for entry in os.listdir("/sys/block"):
            if any(skip in entry for skip in ("ram", "loop", "md", "dm-", "sr")):
                continue
            stat_path = f"/sys/block/{entry}/stat"
            if os.path.exists(stat_path):
                with open(stat_path, "r") as f:
                    parts = f.read().split()
                    if len(parts) >= 7:
                        read_sectors += int(parts[2])
                        write_sectors += int(parts[6])

        elapsed = now - _prev_disk["time"] if _prev_disk["time"] > 0 else 1
        if elapsed < 0.1:
            elapsed = 1

        read_bytes = (read_sectors - _prev_disk["read"]) * 512 / elapsed
        write_bytes = (write_sectors - _prev_disk["write"]) * 512 / elapsed

        # Handle first run or negative values
        if _prev_disk["time"] == 0 or read_bytes < 0:
            read_bytes = 0
        if _prev_disk["time"] == 0 or write_bytes < 0:
            write_bytes = 0

        _prev_disk = {"time": now, "read": read_sectors, "write": write_sectors}

        return f"IO:◂{_human_bytes(read_bytes)} ▸{_human_bytes(write_bytes)}"
    except Exception:
        return ""


def _get_net_speed() -> str:
    """Get network speed."""
    global _prev_net
    try:
        now = time.monotonic()
        rx_bytes = 0
        tx_bytes = 0

        net_dir = "/sys/class/net"
        for iface in os.listdir(net_dir):
            if iface == "lo":
                continue
            rx_path = f"{net_dir}/{iface}/statistics/rx_bytes"
            tx_path = f"{net_dir}/{iface}/statistics/tx_bytes"
            if os.path.exists(rx_path):
                with open(rx_path, "r") as f:
                    rx_bytes += int(f.read().strip())
            if os.path.exists(tx_path):
                with open(tx_path, "r") as f:
                    tx_bytes += int(f.read().strip())

        elapsed = now - _prev_net["time"] if _prev_net["time"] > 0 else 1
        if elapsed < 0.1:
            elapsed = 1

        rx_rate = (rx_bytes - _prev_net["rx"]) / elapsed
        tx_rate = (tx_bytes - _prev_net["tx"]) / elapsed

        # Handle first run or negative values
        if _prev_net["time"] == 0 or rx_rate < 0:
            rx_rate = 0
        if _prev_net["time"] == 0 or tx_rate < 0:
            tx_rate = 0

        _prev_net = {"time": now, "rx": rx_bytes, "tx": tx_bytes}

        return f"▾{_human_bytes(rx_rate)}/s ▴{_human_bytes(tx_rate)}/s"
    except Exception:
        return ""


def _get_temp() -> str:
    """Get CPU temperature."""
    try:
        # Try hwmon (most reliable)
        hwmon_dir = "/sys/class/hwmon"
        if os.path.exists(hwmon_dir):
            for hw in os.listdir(hwmon_dir):
                hw_path = f"{hwmon_dir}/{hw}"
                name_path = f"{hw_path}/name"
                if os.path.exists(name_path):
                    with open(name_path, "r") as f:
                        name = f.read().strip()
                    if name in ("coretemp", "k10temp", "zenpower"):
                        temps = []
                        for entry in os.listdir(hw_path):
                            if entry.startswith("temp") and entry.endswith("_input"):
                                with open(f"{hw_path}/{entry}", "r") as f:
                                    temps.append(int(f.read().strip()) / 1000)
                        if temps:
                            avg_temp = sum(temps) / len(temps)
                            return f"{avg_temp:.0f}°C"

        # Fallback: thermal zones
        thermal_dir = "/sys/class/thermal"
        if os.path.exists(thermal_dir):
            for tz in os.listdir(thermal_dir):
                if tz.startswith("thermal_zone"):
                    temp_path = f"{thermal_dir}/{tz}/temp"
                    if os.path.exists(temp_path):
                        with open(temp_path, "r") as f:
                            temp = int(f.read().strip()) / 1000
                            return f"{temp:.0f}°C"
    except Exception:
        pass
    return ""


def _get_battery() -> str:
    """Get battery percentage."""
    try:
        bat_path = "/sys/class/power_supply/BAT0"
        if os.path.isdir(bat_path):
            uevent_path = f"{bat_path}/uevent"
            if os.path.exists(uevent_path):
                info = {}
                with open(uevent_path, "r") as f:
                    for line in f:
                        if "=" in line:
                            key, val = line.strip().split("=", 1)
                            info[key] = val

                # Try POWER_SUPPLY_CAPACITY first
                if "POWER_SUPPLY_CAPACITY" in info:
                    pct = int(info["POWER_SUPPLY_CAPACITY"])
                    if pct < 99:
                        return f"B:{pct}%"
                # Fallback to calculating from energy/charge
                else:
                    now = None
                    full = None
                    for key, val in info.items():
                        if "_NOW" in key and now is None:
                            now = int(val)
                        if "_FULL" in key and full is None:
                            full = int(val)
                    if now and full:
                        pct = now / full * 100
                        if pct < 99:
                            return f"B:{pct:.0f}%"
    except Exception:
        pass
    return ""


def _check_reboot_required() -> str:
    """Check if reboot is required."""
    if os.path.exists("/var/run/reboot-required"):
        return "⟳"
    return ""


def _fetch_status() -> None:
    """Gather all system stats and update cache."""
    global cached_status, last_fetch_time, cpu_load_is_high

    try:
        parts = []

        # Temperature
        temp = _get_temp()
        if temp:
            parts.append(temp)

        # Battery
        battery = _get_battery()
        if battery:
            parts.append(battery)

        # Uptime
        uptime = _get_uptime()
        if uptime:
            parts.append(uptime)

        # Reboot required
        reboot = _check_reboot_required()
        if reboot:
            parts.append(reboot)

        # CPU load and check if high
        cpu_load_is_high = False
        load_str = _get_cpu_load()
        if load_str:
            # Extract load value and check against cached cores
            try:
                load_value = float(load_str.split(":")[1])
                cpu_load_is_high = load_value > cpu_cores
            except:
                pass
            parts.append(load_str)

        # Memory and check if high
        global memory_is_high
        mem = _get_memory()
        if mem:
            # Extract memory percentage and check against threshold
            try:
                mem_value = float(mem.split(":")[1].rstrip("%"))
                memory_is_high = mem_value > MEMORY_THRESHOLD
            except Exception:
                memory_is_high = False
                pass
            parts.append(mem)

        # Disk I/O
        disk = _get_disk_io()
        if disk:
            parts.append(disk)

        # Network
        net = _get_net_speed()
        if net:
            parts.append(net)

        status = " ⡇ ".join(parts)

        with status_lock:
            cached_status = status
            last_fetch_time = time.monotonic()
    except Exception:
        pass


def get_system_status() -> str:
    """Return cached status (non-blocking)."""
    with status_lock:
        return cached_status


def draw_tab(
    draw_data: DrawData,
    screen: Screen,
    tab: TabBarData,
    before: int,
    max_title_length: int,
    index: int,
    is_last: bool,
    extra_data: ExtraData,
) -> int:
    global timer_id

    if timer_id is None:
        timer_id = add_timer(_redraw_tab_bar, REFRESH_INTERVAL, True)
        # Fetch initial status
        threading.Thread(target=_fetch_status, daemon=True).start()

    # Set colors based on active/inactive state
    if tab.is_active:
        fg = as_rgb(int(draw_data.active_fg))
        bg = as_rgb(int(draw_data.active_bg))
    else:
        fg = as_rgb(int(draw_data.inactive_fg))
        bg = as_rgb(int(draw_data.inactive_bg))

    screen.cursor.fg = fg
    screen.cursor.bg = bg

    # Draw leading space
    if draw_data.leading_spaces:
        screen.draw(" " * draw_data.leading_spaces)

    # Draw tab title with index (cleaned to show only process name)
    title = _clean_title(tab.title)
    formatted_title = f"{index}: {title}"
    screen.draw(formatted_title)

    # Handle trailing spaces and truncation
    trailing_spaces = min(max_title_length - 1, draw_data.trailing_spaces)
    max_title_length -= trailing_spaces
    extra = screen.cursor.x - before - max_title_length
    if extra > 0:
        screen.cursor.x -= extra + 1
        screen.draw("…")
    if trailing_spaces:
        screen.draw(" " * trailing_spaces)

    end = screen.cursor.x

    # Draw separator
    screen.cursor.bold = screen.cursor.italic = False
    if not is_last:
        screen.cursor.fg = as_rgb(int(draw_data.active_fg))
        screen.cursor.bg = as_rgb(int(draw_data.default_bg))
        screen.draw(f" {TAB_SEPARATOR} ")
    screen.cursor.bg = 0

    if is_last:
        draw_right_status(draw_data, screen)

    return end


def draw_right_status(draw_data: DrawData, screen: Screen) -> None:
    global _colors_cached, _tab_bg_active, _tab_fg_active, cpu_load_is_high, memory_is_high

    # Reset any formats left by tabs
    draw_attributed_string(Formatter.reset, screen)

    status = get_system_status()
    if not status:
        return

    # Calculate padding
    status_length = len(status) + 2  # +2 for padding
    padding = screen.columns - screen.cursor.x - status_length

    if padding < 0:
        # Not enough space, truncate status
        available = screen.columns - screen.cursor.x - 2
        if available > 5:
            status = status[: available - 1] + "…"
        else:
            return
        padding = 0

    if padding > 0:
        screen.draw(" " * padding)

    # Cache colors on first use - always use active colors for right status
    if not _colors_cached:
        _tab_bg_active = as_rgb(int(draw_data.active_bg))
        _tab_fg_active = as_rgb(int(draw_data.active_fg))
        _colors_cached = True

    # Draw status with conditional coloring for CPU load and memory
    screen.cursor.bg = _tab_bg_active
    screen.cursor.fg = _tab_fg_active
    screen.draw(" ")

    current_pos = 0
    separator = " ⡇ "

    while current_pos < len(status):
        next_sep = status.find(separator, current_pos)
        if next_sep == -1:
            segment = status[current_pos:]
            current_pos = len(status)
        else:
            segment = status[current_pos:next_sep]
            current_pos = next_sep + len(separator)

        # Determine color for this segment
        if cpu_load_is_high and segment.startswith("L:"):
            # CPU load - red
            screen.cursor.fg = as_rgb(0xFF0000)
            screen.cursor.bold = True
            screen.draw(segment)
            screen.cursor.fg = _tab_fg_active
            screen.cursor.bold = False
        elif memory_is_high and segment.startswith("M:"):
            # Memory - red
            screen.cursor.fg = as_rgb(0xFF0000)
            screen.cursor.bold = True
            screen.draw(segment)
            screen.cursor.fg = _tab_fg_active
            screen.cursor.bold = False
        else:
            # Normal - yellow
            screen.cursor.fg = _tab_fg_active
            screen.draw(segment)

        if next_sep != -1:
            screen.draw(separator)

    screen.draw(" ")


def _redraw_tab_bar(timer_id) -> None:
    # Only fetch if enough time has passed
    current_time = time.monotonic()
    with status_lock:
        time_since_fetch = current_time - last_fetch_time

    if time_since_fetch >= REFRESH_INTERVAL - 0.1:
        threading.Thread(target=_fetch_status, daemon=True).start()

    # Mark tab bar for redraw
    for tm in get_boss().all_tab_managers:
        tm.mark_tab_bar_dirty()
