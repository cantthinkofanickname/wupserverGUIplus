from pathlib import Path
import errno
import socket
import os
import sys
import struct
import time
import json
import hashlib
import threading
import queue
import posixpath
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def make_buffer(size):
    return bytearray([0x00] * size)


def copy_string(buffer, s, offset):
    s += "\0"
    buffer[offset:offset + len(s)] = bytearray(s, "ascii")


def copy_word(buffer, w, offset):
    buffer[offset:offset + 4] = struct.pack(">I", w)


def get_string(buffer, offset):
    s = buffer[offset:]
    if b"\x00" in s:
        return s[:s.index(b"\x00")].decode("utf-8", errors="replace")
    return s.decode("utf-8", errors="replace")


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def format_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def format_time(ts):
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def md5_of_file(path, chunk=0x10000):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


class CopyCancelled(Exception):
    """Raised when the user asks to stop a copy operation."""


# ---------------------------------------------------------------------------
# Локализация
# ---------------------------------------------------------------------------

TRANSLATIONS = {
    "ru": {
        "app_title": "Wii U File Manager",
        "ip_label": "IP Wii U:",
        "port_label": "Порт:",
        "volume_label": "Том:",
        "connect": "Подключиться",
        "disconnect": "Отключиться",
        "status_disconnected": "Не подключено.",
        "status_connected": "Подключено",
        "settings": "Настройки",
        "settings_title": "Настройки",
        "settings_language": "Язык / Language:",
        "settings_log_to_file": "Логировать в файл ({path})",
        "settings_verify_md5": "Проверять MD5 после загрузки (медленно)",
        "settings_file_path": "Файл настроек: {path}",
        "settings_save": "Сохранить",
        "settings_cancel": "Отмена",
        "settings_saved": "Сохранено.",
        "settings_saved_restart": "Сохранено. Некоторые изменения вступят в силу после перезапуска.",
        "new_folder_remote": "Новая папка Wii U (F7)",
        "new_folder_local": "Новая папка ПК",
        "panel_wiiu": "Wii U",
        "panel_local": "Этот компьютер",
        "col_name": "Имя",
        "col_kind": "Тип",
        "col_size": "Размер",
        "col_mtime": "Изменён",
        "kind_file": "Файл",
        "kind_dir": "Папка",
        "kind_parent": "Родительская",
        "log_label": "Сообщения:",
        "progress_waiting": "Ожидание",
        "progress_done": "Операция завершена",
        "progress_stopped": "Остановлено",
        "menu_view": "Просмотр (F3)",
        "menu_edit": "Редактировать (F4)",
        "menu_download": "Скачать на ПК (F5)",
        "menu_upload": "Загрузить на Wii U (F5)",
        "menu_move_to_local": "Переместить на ПК (F6)",
        "menu_move_to_remote": "Переместить на Wii U (F6)",
        "menu_rename": "Переименовать… (F2)",
        "menu_delete_remote": "Удалить на Wii U (Del)",
        "menu_delete_local": "Удалить на ПК (Del)",
        "menu_mkdir_remote": "Новая папка (F7)",
        "menu_mkdir_local": "Новая папка (F7)",
        "menu_refresh": "Обновить",
        "menu_mount_sd": "Смонтировать SD-карту",
        "dialog_error": "Ошибка",
        "dialog_info": "Информация",
        "dialog_wait": "Подождите",
        "dialog_no_connection": "Нет подключения",
        "dialog_no_connection_msg": "Сначала подключись к Wii U.",
        "dialog_busy_msg": "Другая операция ещё выполняется.",
        "dialog_error_port": "Порт должен быть числом от 1 до 65535.",
        "dialog_select_file": "Выбор файла",
        "dialog_select_remote": "Выбери файл или папку в панели Wii U.",
        "dialog_select_local": "Выбери файл или папку в панели ПК.",
        "dialog_view": "Просмотр",
        "dialog_view_one": "Выбери один файл.",
        "dialog_edit": "Редактирование",
        "dialog_edit_one": "Выбери один файл.",
        "dialog_edit_question": "Файл открыт:\n{path}\n\nЗагрузить изменения обратно на Wii U?",
        "dialog_upload_confirm": "Скопировать на Wii U ({count} объектов)?\n\n{preview}\n\n→ {path}",
        "dialog_upload_title": "Загрузить на Wii U",
        "dialog_delete_remote": "Удаление на Wii U",
        "dialog_delete_local": "Удаление на ПК",
        "dialog_delete_confirm": "Удалить без возможности восстановления?\n\n{preview}",
        "dialog_new_folder_remote": "Новая папка Wii U",
        "dialog_new_folder_local": "Новая папка ПК",
        "dialog_folder_name": "Имя папки:",
        "dialog_folder_bad": "Укажи имя одной папки без разделителей пути.",
        "dialog_rename": "Переименовать",
        "dialog_rename_new": "Новое имя:",
        "dialog_rename_one": "Выбери ровно один файл или папку.",
        "dialog_select": "Выбор",
        "dialog_mount_sd_title": "Монтирование SD-карты",
        "dialog_mount_sd_ok": "SD-карта успешно смонтирована.",
        "dialog_unmount_sd_title": "Отмонтирование SD-карты",
        "status_connecting": "Подключение…",
        "status_disconnecting": "Отключение…",
        "status_connected_to": "Подключено к {ip}:{port} ({volume})",
        "status_disconnected_ok": "Не подключено",
        "status_connecting_fail": "Не удалось подключиться к {ip}:{port}\n{exc}\n\nПроверь IP, порт и запущенный wupserver.",
        "status_stopping": "Остановка копирования и отключение…",
        "status_stopping_op": "Остановка операции и закрытие…",
        "status_error_op": "Ошибка операции",
        "status_copy_stopped": "Копирование остановлено",
        "status_copy_stopping": "Копирование остановлено пользователем",
        "status_op_done": "Операция завершена",
        "status_operation_done": "Операция завершена",
        "log_connected": "Подключение установлено: {ip}:{port}, том {volume}",
        "log_disconnected": "Соединение с Wii U закрыто.",
        "log_reconnect": "⚠ Соединение с Wii U потеряно. Пытаюсь переподключиться…",
        "log_reconnect_ok": "✔ Переподключение успешно",
        "log_reconnect_fail": "✘ Переподключение не удалось: {exc}",
        "log_download": "Скачивание: {path}",
        "log_upload": "Загрузка: {path}",
        "log_delete": "Удаление: {path}",
        "log_deleted_remote": "Удалено на Wii U: {count}",
        "log_deleted_local": "Удалено на ПК: {count}",
        "log_moved_to_local": "Перемещено на ПК: {count}",
        "log_moved_to_remote": "Перемещено на Wii U: {count}",
        "log_downloaded": "Скачано объектов: {count}",
        "log_uploaded": "Загружено объектов: {count}",
        "log_renamed": "Переименовано: {old} → {new}",
        "log_md5": "MD5 {name}: {hash}",
        "log_md5_fail": "MD5 не посчитан: {exc}",
        "log_folder_created": "Папка создана: {path}",
        "log_folder_create_fail": "Не удалось создать папку {path} (код 0x{code:08X})",
        "log_rename_fail": "Не удалось переименовать (код 0x{code:08X})",
        "log_delete_fail": "Ошибка удаления {path} (код 0x{code:08X})",
        "log_open_dir": "Открыта папка Wii U: {path}",
        "log_read_remote_fail": "Ошибка чтения Wii U: {exc}",
        "log_read_local_fail": "Ошибка чтения ПК: {exc}",
        "log_volume_switched": "Переключено на том: {volume}",
        "log_changes_uploaded": "Изменения загружены: {path}",
        "log_mount_sd_ok": "SD-карта смонтирована в /vol/storage_sdcard",
        "log_mount_sd_fail": "Не удалось смонтировать SD-карту (код 0x{code:08X})",
        "log_unmount_sd_ok": "SD-карта отмонтирована",
        "log_unmount_sd_fail": "Не удалось отмонтировать SD-карту (код 0x{code:08X})",
        "progress_title_download": "Скачивание на ПК",
        "progress_title_upload": "Загрузка на Wii U",
        "progress_title_move_local": "Перемещение Wii U → ПК",
        "progress_title_move_remote": "Перемещение ПК → Wii U",
        "progress_title_delete_remote": "Удаление на Wii U",
        "progress_title_rename_remote": "Переименование на Wii U",
        "progress_title_mkdir_remote": "Создание папки Wii U",
        "progress_title_volume": "Переключение тома Wii U",
        "progress_title_navigate": "Открытие папки Wii U",
        "progress_title_view": "Скачивание для просмотра",
        "progress_title_edit": "Скачивание для редактирования",
        "progress_title_upload_changes": "Загрузка изменений",
        "progress_title_mount_sd": "Монтирование SD-карты",
        "progress_ready": "готово",
        "progress_prefix": "{title}…",
        "eta_sec": "{n} с",
        "eta_min": "{m} мин {s} с",
        "eta_hour": "{h} ч {m} мин",
        "progress_format_full": "{name} — {done} / {total} — {speed} — осталось ~{eta}",
        "progress_format_simple": "{name} — {done} — {speed}",
    },
    "en": {
        "app_title": "Wii U File Manager",
        "ip_label": "Wii U IP:",
        "port_label": "Port:",
        "volume_label": "Volume:",
        "connect": "Connect",
        "disconnect": "Disconnect",
        "status_disconnected": "Not connected.",
        "status_connected": "Connected",
        "settings": "Settings",
        "settings_title": "Settings",
        "settings_language": "Language:",
        "settings_log_to_file": "Log to file ({path})",
        "settings_verify_md5": "Verify MD5 after upload (slow)",
        "settings_file_path": "Config file: {path}",
        "settings_save": "Save",
        "settings_cancel": "Cancel",
        "settings_saved": "Saved.",
        "settings_saved_restart": "Saved. Some changes take effect after restart.",
        "new_folder_remote": "New Wii U folder (F7)",
        "new_folder_local": "New PC folder",
        "panel_wiiu": "Wii U",
        "panel_local": "This PC",
        "col_name": "Name",
        "col_kind": "Type",
        "col_size": "Size",
        "col_mtime": "Modified",
        "kind_file": "File",
        "kind_dir": "Folder",
        "kind_parent": "Parent",
        "log_label": "Messages:",
        "progress_waiting": "Idle",
        "progress_done": "Operation complete",
        "progress_stopped": "Stopped",
        "menu_view": "View (F3)",
        "menu_edit": "Edit (F4)",
        "menu_download": "Download to PC (F5)",
        "menu_upload": "Upload to Wii U (F5)",
        "menu_move_to_local": "Move to PC (F6)",
        "menu_move_to_remote": "Move to Wii U (F6)",
        "menu_rename": "Rename… (F2)",
        "menu_delete_remote": "Delete on Wii U (Del)",
        "menu_delete_local": "Delete on PC (Del)",
        "menu_mkdir_remote": "New folder (F7)",
        "menu_mkdir_local": "New folder (F7)",
        "menu_refresh": "Refresh",
        "menu_mount_sd": "Mount SD card",
        "dialog_error": "Error",
        "dialog_info": "Information",
        "dialog_wait": "Please wait",
        "dialog_no_connection": "No connection",
        "dialog_no_connection_msg": "Connect to the Wii U first.",
        "dialog_busy_msg": "Another operation is still running.",
        "dialog_error_port": "Port must be a number between 1 and 65535.",
        "dialog_select_file": "Select file",
        "dialog_select_remote": "Select a file or folder in the Wii U panel.",
        "dialog_select_local": "Select a file or folder in the PC panel.",
        "dialog_view": "View",
        "dialog_view_one": "Select a single file.",
        "dialog_edit": "Edit",
        "dialog_edit_one": "Select a single file.",
        "dialog_edit_question": "File opened:\n{path}\n\nUpload changes back to the Wii U?",
        "dialog_upload_confirm": "Copy to Wii U ({count} objects)?\n\n{preview}\n\n→ {path}",
        "dialog_upload_title": "Upload to Wii U",
        "dialog_delete_remote": "Delete on Wii U",
        "dialog_delete_local": "Delete on PC",
        "dialog_delete_confirm": "Delete permanently?\n\n{preview}",
        "dialog_new_folder_remote": "New Wii U folder",
        "dialog_new_folder_local": "New PC folder",
        "dialog_folder_name": "Folder name:",
        "dialog_folder_bad": "Enter a single folder name without path separators.",
        "dialog_rename": "Rename",
        "dialog_rename_new": "New name:",
        "dialog_rename_one": "Select exactly one file or folder.",
        "dialog_select": "Selection",
        "dialog_mount_sd_title": "Mounting SD card",
        "dialog_mount_sd_ok": "SD card mounted successfully.",
        "dialog_unmount_sd_title": "Unmounting SD card",
        "status_connecting": "Connecting…",
        "status_disconnecting": "Disconnecting…",
        "status_connected_to": "Connected to {ip}:{port} ({volume})",
        "status_disconnected_ok": "Not connected",
        "status_connecting_fail": "Failed to connect to {ip}:{port}\n{exc}\n\nCheck the IP, port, and running wupserver.",
        "status_stopping": "Stopping copy and disconnecting…",
        "status_stopping_op": "Stopping operation and closing…",
        "status_error_op": "Operation failed",
        "status_copy_stopped": "Copy stopped",
        "status_copy_stopping": "Copy stopped by user",
        "status_op_done": "Operation complete",
        "status_operation_done": "Operation complete",
        "log_connected": "Connection established: {ip}:{port}, volume {volume}",
        "log_disconnected": "Connection to Wii U closed.",
        "log_reconnect": "⚠ Connection to Wii U lost. Reconnecting…",
        "log_reconnect_ok": "✔ Reconnected successfully",
        "log_reconnect_fail": "✘ Reconnect failed: {exc}",
        "log_download": "Downloading: {path}",
        "log_upload": "Uploading: {path}",
        "log_delete": "Deleting: {path}",
        "log_deleted_remote": "Deleted on Wii U: {count}",
        "log_deleted_local": "Deleted on PC: {count}",
        "log_moved_to_local": "Moved to PC: {count}",
        "log_moved_to_remote": "Moved to Wii U: {count}",
        "log_downloaded": "Downloaded objects: {count}",
        "log_uploaded": "Uploaded objects: {count}",
        "log_renamed": "Renamed: {old} → {new}",
        "log_md5": "MD5 {name}: {hash}",
        "log_md5_fail": "MD5 not computed: {exc}",
        "log_folder_created": "Folder created: {path}",
        "log_folder_create_fail": "Failed to create folder {path} (code 0x{code:08X})",
        "log_rename_fail": "Failed to rename (code 0x{code:08X})",
        "log_delete_fail": "Failed to delete {path} (code 0x{code:08X})",
        "log_open_dir": "Wii U folder opened: {path}",
        "log_read_remote_fail": "Error reading Wii U: {exc}",
        "log_read_local_fail": "Error reading PC: {exc}",
        "log_volume_switched": "Switched to volume: {volume}",
        "log_changes_uploaded": "Changes uploaded: {path}",
        "log_mount_sd_ok": "SD card mounted at /vol/storage_sdcard",
        "log_mount_sd_fail": "Failed to mount SD card (code 0x{code:08X})",
        "log_unmount_sd_ok": "SD card unmounted",
        "log_unmount_sd_fail": "Failed to unmount SD card (code 0x{code:08X})",
        "progress_title_download": "Downloading to PC",
        "progress_title_upload": "Uploading to Wii U",
        "progress_title_move_local": "Moving Wii U → PC",
        "progress_title_move_remote": "Moving PC → Wii U",
        "progress_title_delete_remote": "Deleting on Wii U",
        "progress_title_rename_remote": "Renaming on Wii U",
        "progress_title_mkdir_remote": "Creating Wii U folder",
        "progress_title_volume": "Switching Wii U volume",
        "progress_title_navigate": "Opening Wii U folder",
        "progress_title_view": "Downloading for viewing",
        "progress_title_edit": "Downloading for editing",
        "progress_title_upload_changes": "Uploading changes",
        "progress_title_mount_sd": "Mounting SD card",
        "progress_ready": "done",
        "progress_prefix": "{title}…",
        "eta_sec": "{n} s",
        "eta_min": "{m} min {s} s",
        "eta_hour": "{h} h {m} min",
        "progress_format_full": "{name} — {done} / {total} — {speed} — ~{eta} left",
        "progress_format_simple": "{name} — {done} — {speed}",
    },
}


# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".wiiu_file_manager.json")
LOG_PATH = os.path.join(os.path.expanduser("~"), "wiiu_file_manager.log")

DEFAULT_CONFIG = {
    "ip": "192.168.3.1",
    "port": "1337",
    "volume": "/vol/storage_mlc01",
    "local_path": os.path.abspath(os.path.expanduser("~")),
    "log_to_file": False,
    "verify_md5": False,
    "language": "ru",
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg = dict(DEFAULT_CONFIG)
            cfg.update(data)
            if cfg.get("language") not in TRANSLATIONS:
                cfg["language"] = "ru"
            return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# wupclient
# ---------------------------------------------------------------------------

class wupclient:
    def __init__(self, ip="192.168.3.132", port=1337, cwd="/vol/storage_mlc01"):
        self.fsa_handle = None
        self.s = socket.socket()
        self.s.settimeout(6)
        try:
            self.s.connect((ip, port))
        except Exception:
            self.s.close()
            raise
        self.s.settimeout(None)
        self.cwd = cwd
        self.closed = False

    def __del__(self):
        try:
            self.disconnect()
        except Exception:
            pass

    def disconnect(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.fsa_handle is not None:
                try:
                    self.close(self.fsa_handle)
                except Exception:
                    pass
                self.fsa_handle = None
        finally:
            try:
                self.s.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.s.close()
            except Exception:
                pass

    def is_alive(self):
        if self.closed:
            return False
        try:
            self.s.settimeout(2)
            self.send(4, struct.pack(">III", 0, 0, 0))
            self.s.settimeout(None)
            return True
        except Exception:
            return False

    # fundamental comms
    def send(self, command, data):
        if self.closed:
            raise ConnectionError("Wii U connection closed")
        request = struct.pack(">I", command) + data
        self.s.sendall(request)
        response = self.s.recv(0x600)
        if not response or len(response) < 4:
            raise ConnectionError("Wii U closed the connection or sent an incomplete response")
        ret = struct.unpack(">I", response[:4])[0]
        return ret, response[4:]

    # core commands
    def read(self, addr, count):
        data = struct.pack(">II", addr, count)
        ret, data = self.send(1, data)
        if ret == 0:
            return data
        print("read error : %08X" % ret)
        return None

    def write(self, addr, data):
        data = struct.pack(">I", addr) + data
        ret, _ = self.send(0, data)
        if ret == 0:
            return ret
        print("write error : %08X" % ret)
        return None

    def svc(self, svc_id, arguments):
        data = struct.pack(">I", svc_id)
        for a in arguments:
            data += struct.pack(">I", a)
        ret, data = self.send(2, data)
        if ret == 0:
            if len(data) < 4:
                raise OSError("Short SVC response")
            return struct.unpack(">I", data[:4])[0]
        print("svc error : %08X" % ret)
        return None

    def kill(self):
        ret, _ = self.send(3, bytearray())
        return ret

    def memcpy(self, dst, src, count):
        data = struct.pack(">III", dst, src, count)
        ret, _ = self.send(4, data)
        if ret == 0:
            return ret
        print("memcpy error : %08X" % ret)
        return None

    def repeatwrite(self, dst, val, n):
        data = struct.pack(">III", dst, val, n)
        ret, _ = self.send(5, data)
        if ret == 0:
            return ret
        print("repeatwrite error : %08X" % ret)
        return None

    # derivatives
    def alloc(self, size, align=None):
        if size == 0:
            return 0
        if align is None:
            return self.svc(0x27, [0xCAFF, size])
        return self.svc(0x28, [0xCAFF, size, align])

    def free(self, address):
        if address == 0:
            return 0
        return self.svc(0x29, [0xCAFF, address])

    def load_buffer(self, b, align=None):
        if len(b) == 0:
            return 0
        address = self.alloc(len(b), align)
        if address is None:
            raise OSError("Failed to allocate memory on Wii U")
        if self.write(address, b) is None:
            raise OSError("Failed to write data to Wii U memory")
        return address

    def load_string(self, s, align=None):
        return self.load_buffer(bytearray(s + "\0", "ascii"), align)

    def open(self, device, mode):
        address = self.load_string(device)
        try:
            return self.svc(0x33, [address, mode])
        finally:
            self.free(address)

    def close(self, handle):
        return self.svc(0x34, [handle])

    def ioctl(self, handle, cmd, inbuf, outbuf_size):
        in_address = self.load_buffer(inbuf)
        out_address = 0
        try:
            if outbuf_size > 0:
                out_address = self.alloc(outbuf_size)
                ret = self.svc(
                    0x38,
                    [handle, cmd, in_address, len(inbuf), out_address, outbuf_size],
                )
                out_data = self.read(out_address, outbuf_size)
            else:
                ret = self.svc(0x38, [handle, cmd, in_address, len(inbuf), 0, 0])
                out_data = None
            return ret, out_data
        finally:
            self.free(out_address)
            self.free(in_address)

    def iovec(self, vecs):
        data = bytearray()
        for address, size in vecs:
            data += struct.pack(">III", address, size, 0)
        return self.load_buffer(data)

    def ioctlv(self, handle, cmd, inbufs, outbuf_sizes, inbufs_ptr=None, outbufs_ptr=None):
        if inbufs_ptr is None:
            inbufs_ptr = []
        if outbufs_ptr is None:
            outbufs_ptr = []

        loaded_in = []
        allocated_out = []
        iovecs = 0
        try:
            loaded_in = [(self.load_buffer(b, 0x40), len(b)) for b in inbufs]
            allocated_out = [(self.alloc(s, 0x40), s) for s in outbuf_sizes]
            iovecs = self.iovec(loaded_in + inbufs_ptr + outbufs_ptr + allocated_out)
            ret = self.svc(
                0x39,
                [
                    handle,
                    cmd,
                    len(loaded_in) + len(inbufs_ptr),
                    len(allocated_out) + len(outbufs_ptr),
                    iovecs,
                ],
            )
            out_data = []
            for address, size in allocated_out:
                data = self.read(address, size)
                out_data.append(data if data is not None else bytearray())
            return ret, out_data
        finally:
            for address, _ in loaded_in + allocated_out:
                self.free(address)
            self.free(iovecs)

    # fsa
    def FSA_Mount(self, handle, device_path, volume_path, flags):
        inbuffer = make_buffer(0x520)
        copy_string(inbuffer, device_path, 0x0004)
        copy_string(inbuffer, volume_path, 0x0284)
        copy_word(inbuffer, flags, 0x0504)
        ret, _ = self.ioctlv(handle, 0x01, [inbuffer, bytearray()], [0x293])
        return ret

    def FSA_Unmount(self, handle, path, flags):
        inbuffer = make_buffer(0x520)
        copy_string(inbuffer, path, 0x4)
        copy_word(inbuffer, flags, 0x284)
        ret, _ = self.ioctl(handle, 0x02, inbuffer, 0x293)
        return ret

    def FSA_RawOpen(self, handle, device):
        inbuffer = make_buffer(0x520)
        copy_string(inbuffer, device, 0x4)
        ret, data = self.ioctl(handle, 0x6A, inbuffer, 0x293)
        return ret, struct.unpack(">I", data[4:8])[0]

    def FSA_OpenDir(self, handle, path):
        inbuffer = make_buffer(0x520)
        copy_string(inbuffer, path, 0x4)
        ret, data = self.ioctl(handle, 0x0A, inbuffer, 0x293)
        if ret != 0 or data is None or len(data) < 8:
            return ret, 0
        return ret, struct.unpack(">I", data[4:8])[0]

    def FSA_ReadDir(self, handle, dir_handle):
        inbuffer = make_buffer(0x520)
        copy_word(inbuffer, dir_handle, 0x4)
        ret, data = self.ioctl(handle, 0x0B, inbuffer, 0x293)
        data = bytearray(data[4:])
        unk = data[:0x64]
        if ret == 0:
            return ret, {
                "name": get_string(data, 0x64),
                "is_file": (unk[0] & 128) != 128,
                "unk": unk,
            }
        return ret, None

    def FSA_CloseDir(self, handle, dir_handle):
        inbuffer = make_buffer(0x520)
        copy_word(inbuffer, dir_handle, 0x4)
        ret, _ = self.ioctl(handle, 0x0D, inbuffer, 0x293)
        return ret

    def FSA_OpenFile(self, handle, path, mode):
        inbuffer = make_buffer(0x520)
        copy_string(inbuffer, path, 0x4)
        copy_string(inbuffer, mode, 0x284)
        ret, data = self.ioctl(handle, 0x0E, inbuffer, 0x293)
        if ret != 0 or data is None or len(data) < 8:
            return ret, 0
        return ret, struct.unpack(">I", data[4:8])[0]

    def FSA_MakeDir(self, handle, path, flags):
        inbuffer = make_buffer(0x520)
        copy_string(inbuffer, path, 0x4)
        copy_word(inbuffer, flags, 0x284)
        ret, _ = self.ioctl(handle, 0x07, inbuffer, 0x293)
        return ret

    def FSA_ReadFile(self, handle, file_handle, size, cnt):
        inbuffer = make_buffer(0x520)
        copy_word(inbuffer, size, 0x08)
        copy_word(inbuffer, cnt, 0x0C)
        copy_word(inbuffer, file_handle, 0x14)
        ret, data = self.ioctlv(handle, 0x0F, [inbuffer], [size * cnt, 0x293])
        return ret, data[0]

    def FSA_WriteFile(self, handle, file_handle, data):
        inbuffer = make_buffer(0x520)
        copy_word(inbuffer, 1, 0x08)
        copy_word(inbuffer, len(data), 0x0C)
        copy_word(inbuffer, file_handle, 0x14)
        ret, _ = self.ioctlv(handle, 0x10, [inbuffer, data], [0x293])
        return ret

    def FSA_ReadFilePtr(self, handle, file_handle, size, cnt, ptr):
        inbuffer = make_buffer(0x520)
        copy_word(inbuffer, size, 0x08)
        copy_word(inbuffer, cnt, 0x0C)
        copy_word(inbuffer, file_handle, 0x14)
        ret, data = self.ioctlv(
            handle, 0x0F, [inbuffer], [0x293], [], [(ptr, size * cnt)]
        )
        return ret, data[0]

    def FSA_WriteFilePtr(self, handle, file_handle, size, cnt, ptr):
        inbuffer = make_buffer(0x520)
        copy_word(inbuffer, size, 0x08)
        copy_word(inbuffer, cnt, 0x0C)
        copy_word(inbuffer, file_handle, 0x14)
        ret, _ = self.ioctlv(
            handle, 0x10, [inbuffer], [0x293], [(ptr, size * cnt)], []
        )
        return ret

    def FSA_GetStatFile(self, handle, file_handle):
        inbuffer = make_buffer(0x520)
        copy_word(inbuffer, file_handle, 0x4)
        ret, data = self.ioctl(handle, 0x14, inbuffer, 0x64)
        return ret, struct.unpack(">IIIIIIIIIIIIIIIIIIIIIIIII", data)

    def FSA_CloseFile(self, handle, file_handle):
        inbuffer = make_buffer(0x520)
        copy_word(inbuffer, file_handle, 0x4)
        ret, _ = self.ioctl(handle, 0x15, inbuffer, 0x293)
        return ret

    def FSA_ChangeMode(self, handle, path, mode):
        mask = 0x777
        inbuffer = make_buffer(0x520)
        copy_string(inbuffer, path, 0x0004)
        copy_word(inbuffer, mode, 0x0284)
        copy_word(inbuffer, mask, 0x0288)
        ret, _ = self.ioctl(handle, 0x20, inbuffer, 0x293)
        return ret

    def FSA_Remove(self, handle, path):
        inbuffer = make_buffer(0x520)
        copy_string(inbuffer, path, 0x4)
        ret, _ = self.ioctl(handle, 0x08, inbuffer, 0x293)
        return ret

    def FSA_RemoveDir(self, handle, path):
        inbuffer = make_buffer(0x520)
        copy_string(inbuffer, path, 0x4)
        ret, _ = self.ioctl(handle, 0x08, inbuffer, 0x293)
        return ret

    def FSA_Rename(self, handle, path_old, path_new):
        inbuffer = make_buffer(0x520)
        copy_string(inbuffer, path_old, 0x4)
        copy_string(inbuffer, path_new, 0x284)
        ret, _ = self.ioctl(handle, 0x13, inbuffer, 0x293)
        return ret

    def FSA_FlushVolume(self, handle, path):
        inbuffer = make_buffer(0x520)
        copy_string(inbuffer, path, 0x04)
        ret, _ = self.ioctl(handle, 0x1B, inbuffer, 0x293)
        return ret

    # mcp
    def MCP_InstallGetInfo(self, handle, path):
        inbuffer = make_buffer(0x27F)
        copy_string(inbuffer, path, 0x0)
        ret, data = self.ioctlv(handle, 0x80, [inbuffer], [0x16])
        return ret, struct.unpack(">IIIIIH", data[0])

    def MCP_Install(self, handle, path):
        inbuffer = make_buffer(0x27F)
        copy_string(inbuffer, path, 0x0)
        ret, _ = self.ioctlv(handle, 0x81, [inbuffer], [])
        return ret

    def MCP_InstallGetProgress(self, handle):
        ret, data = self.ioctl(handle, 0x82, [], 0x24)
        return ret, struct.unpack(">IIIIIIIII", data)

    # file management
    def get_fsa_handle(self):
        if self.fsa_handle is None:
            self.fsa_handle = self.open("/dev/fsa", 0)
            if self.fsa_handle is None:
                raise OSError("Failed to open /dev/fsa")
        return self.fsa_handle

    # --- SD card helpers (отдельный дескриптор + задержка + проверка) ---
    def mount_sd(self, retries=5, delay=0.4):
        """Смонтировать SD-карту в /vol/storage_sdcard через отдельный дескриптор."""
        handle = self.open("/dev/fsa", 0)
        if handle is None:
            raise OSError("Failed to open /dev/fsa for SD mount")
        try:
            ret = self.FSA_Mount(handle, "/dev/sdcard01", "/vol/storage_sdcard", 2)
        finally:
            try:
                self.close(handle)
            except Exception:
                pass
        if ret != 0:
            raise OSError(f"SD mount failed (code 0x{ret:08X})")

        fsa = self.get_fsa_handle()
        last_ret = None
        for _ in range(retries):
            time.sleep(delay)
            check_ret, dir_handle = self.FSA_OpenDir(fsa, "/vol/storage_sdcard")
            if check_ret == 0:
                self.FSA_CloseDir(fsa, dir_handle)
                return ret
            last_ret = check_ret
        raise OSError(f"SD mount returned 0 but volume not openable (opendir 0x{last_ret:08X})")

    def unmount_sd(self):
        """Отмонтировать /vol/storage_sdcard через отдельный дескриптор."""
        handle = self.open("/dev/fsa", 0)
        if handle is None:
            raise OSError("Failed to open /dev/fsa for SD unmount")
        try:
            ret = self.FSA_Unmount(handle, "/vol/storage_sdcard", 2)
        finally:
            try:
                self.close(handle)
            except Exception:
                pass
        if ret != 0:
            raise OSError(f"SD unmount failed (code 0x{ret:08X})")
        time.sleep(0.3)
        return ret

    def mkdir(self, path, flags):
        fsa_handle = self.get_fsa_handle()
        if not path.startswith("/"):
            path = self.cwd + "/" + path
        ret = self.FSA_MakeDir(fsa_handle, path, flags)
        if ret != 0:
            print("mkdir error (%s, %08X)" % (path, ret))
        return ret

    def ls(self, path=None, return_data=False):
        fsa_handle = self.get_fsa_handle()
        if path is not None and not path.startswith("/"):
            path = self.cwd + "/" + path
        ret, dir_handle = self.FSA_OpenDir(fsa_handle, path if path is not None else self.cwd)
        if ret != 0:
            print("opendir error : " + hex(ret))
            return [] if return_data else None
        entries = []
        try:
            while True:
                ret, data = self.FSA_ReadDir(fsa_handle, dir_handle)
                if ret != 0:
                    break
                if not return_data:
                    print("     %s%s" % (data["name"], "/" if not data["is_file"] else ""))
                else:
                    entries.append(data)
        finally:
            self.FSA_CloseDir(fsa_handle, dir_handle)
        return entries if return_data else None

    def remove(self, path):
        fsa_handle = self.get_fsa_handle()
        if not path.startswith("/"):
            path = self.cwd + "/" + path
        ret, dir_handle = self.FSA_OpenDir(fsa_handle, path)
        if ret == 0:
            self.FSA_CloseDir(fsa_handle, dir_handle)
            entries = self.ls(path, True)
            for e in entries:
                name = e["name"]
                if name in (".", "..", ""):
                    continue
                child = path + "/" + name
                self.remove(child)
            return self.FSA_RemoveDir(fsa_handle, path)
        return self.FSA_Remove(fsa_handle, path)

    def rename(self, old_path, new_path):
        fsa_handle = self.get_fsa_handle()
        if not old_path.startswith("/"):
            old_path = self.cwd + "/" + old_path
        if not new_path.startswith("/"):
            new_path = self.cwd + "/" + new_path

        ret, dir_handle = self.FSA_OpenDir(fsa_handle, old_path)
        if ret == 0:
            self.FSA_CloseDir(fsa_handle, dir_handle)
            self.mkdir(new_path, 0x600)
            entries = self.ls(old_path, True) or []
            for e in entries:
                name = e["name"]
                if name in (".", "..", ""):
                    continue
                self.rename(old_path + "/" + name, new_path + "/" + name)
            return self.remove(old_path)

        ret, fh = self.FSA_OpenFile(fsa_handle, old_path, "r")
        if ret != 0:
            return ret
        self.FSA_CloseFile(fsa_handle, fh)

        ret, fh_out = self.FSA_OpenFile(fsa_handle, new_path, "w")
        if ret != 0:
            return ret
        block_size = 0x10000
        buf = self.alloc(block_size, 0x40)
        ret_read, fh_in = self.FSA_OpenFile(fsa_handle, old_path, "r")
        try:
            while True:
                ret, _ = self.FSA_ReadFilePtr(fsa_handle, fh_in, 1, block_size, buf)
                if ret <= 0:
                    break
                self.FSA_WriteFilePtr(fsa_handle, fh_out, 1, ret, buf)
                if ret < block_size:
                    break
        finally:
            self.FSA_CloseFile(fsa_handle, fh_in)
            self.FSA_CloseFile(fsa_handle, fh_out)
            self.free(buf)
        return self.remove(old_path)

    def stat_file(self, path):
        fsa_handle = self.get_fsa_handle()
        if not path.startswith("/"):
            path = self.cwd + "/" + path
        ret, fh = self.FSA_OpenFile(fsa_handle, path, "r")
        if ret != 0:
            return None
        try:
            ret, stats = self.FSA_GetStatFile(fsa_handle, fh)
            if ret != 0:
                return None
            return {
                "size": stats[5],
                "mtime": stats[6] if len(stats) > 6 else 0,
                "mode": stats[2],
                "flags": stats[1],
            }
        finally:
            self.FSA_CloseFile(fsa_handle, fh)

    def dl(self, filename, directorypath=None, local_filename=None,
           progress_callback=None, cancel_event=None):
        fsa_handle = self.get_fsa_handle()
        if not filename.startswith("/"):
            filename = self.cwd + "/" + filename
        if local_filename is None:
            local_filename = posixpath.basename(filename)
        ret, file_handle = self.FSA_OpenFile(fsa_handle, filename, "r")
        if ret != 0:
            raise OSError("dl error: could not open %s (FSA code 0x%08X)" % (filename, ret))

        buffer = bytearray()
        block_size = 0x400
        started = time.monotonic()
        try:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise CopyCancelled("Copy cancelled by user")
                ret, data = self.FSA_ReadFile(fsa_handle, file_handle, 1, block_size)
                if data is None:
                    raise OSError("File read error: " + filename)
                buffer += data[:ret]
                elapsed = max(time.monotonic() - started, 0.001)
                if progress_callback:
                    progress_callback(filename, len(buffer), None, len(buffer) / elapsed)
                if ret < block_size:
                    break
        finally:
            self.FSA_CloseFile(fsa_handle, file_handle)

        if directorypath is None:
            output_path = local_filename
        else:
            dir_path = os.path.dirname(os.path.abspath(sys.argv[0])).replace("\\", "/")
            fullpath = (dir_path + "/" + directorypath + "/").replace("//", "/")
            mkdir_p(fullpath)
            output_path = os.path.join(fullpath, local_filename)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as output:
            output.write(buffer)
        if progress_callback:
            elapsed = max(time.monotonic() - started, 0.001)
            progress_callback(filename, len(buffer), len(buffer), len(buffer) / elapsed)
        return len(buffer)

    def up(self, local_filename, filename=None, progress_callback=None, cancel_event=None):
        fsa_handle = self.get_fsa_handle()
        if filename is None:
            if "/" in local_filename:
                filename = local_filename[[i for i, x in enumerate(local_filename) if x == "/"][-1]+1:]
            else:
                filename = local_filename
        if filename[0] != "/":
            filename = self.cwd + "/" + filename
        f = open(local_filename, "rb")
        ret, file_handle = self.FSA_OpenFile(fsa_handle, filename, "w")
        if ret != 0x0:
            print("up error : could not open " + filename)
            return
        progress = 0
        block_size = 0x400
        total_size = os.path.getsize(local_filename)
        started = time.monotonic()
        while True:
            if cancel_event is not None and cancel_event.is_set():
                self.FSA_CloseFile(fsa_handle, file_handle)
                raise CopyCancelled("Copy cancelled by user")
            data = f.read(block_size)
            if not data:
                break
            ret = self.FSA_WriteFile(fsa_handle, file_handle, data)
            progress += len(data)
            if progress_callback:
                elapsed = max(time.monotonic() - started, 0.001)
                progress_callback(filename, progress, total_size, progress / elapsed)
            sys.stdout.write(hex(progress) + "\r"); sys.stdout.flush()
            if len(data) < block_size:
                break
        self.FSA_CloseFile(fsa_handle, file_handle)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

class WiiUFileManager:
    VOLUMES = [
        "/vol/storage_mlc01",
        "/vol/storage_usb01",
        "/vol/system_slc",
        "/vol/storage_sdcard",
    ]

    SD_MOUNT_PATH = "/vol/storage_sdcard"
    SD_DEVICE = "/dev/sdcard01"
    SD_FLAGS = 2

    def __init__(self, root):
        self.root = root
        self.cfg = load_config()

        self.lang = self.cfg.get("language", "ru")
        if self.lang not in TRANSLATIONS:
            self.lang = "ru"

        self.root.title(self.tr("app_title"))
        self.root.geometry("1024x768")
        self.root.minsize(1000, 620)

        self.client = None
        self.busy = False
        self.closing = False
        self.sd_mounted = False
        self.cancel_event = threading.Event()
        self.messages = queue.Queue()
        self.remote_path = self.cfg.get("volume", "/vol/storage_mlc01")
        self.local_path = self.cfg.get("local_path") or os.path.abspath(os.path.expanduser("~"))

        self.remote_sort = {"col": "name", "reverse": False}
        self.local_sort = {"col": "name", "reverse": False}

        self._build_ui()
        self._refresh_local()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self._poll_messages)
        self.root.after(2000, self._heartbeat)

        self._init_hotkeys()

    # ---------- локализация ----------
    def tr(self, key, **kwargs):
        text = TRANSLATIONS.get(self.lang, TRANSLATIONS["ru"]).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    def set_language(self, lang):
        if lang not in TRANSLATIONS:
            return
        self.lang = lang
        self.cfg["language"] = lang
        save_config(self.cfg)
        self._rebuild_ui()

    def _rebuild_ui(self):
        for child in self.root.winfo_children():
            child.destroy()
        self.root.title(self.tr("app_title"))
        self._build_ui()
        self._refresh_local()
        if self.client and not self.busy:
            self._refresh_remote()
        self.connect_btn.configure(
            text=self.tr("disconnect") if self.client else self.tr("connect")
        )
        if self.client:
            self.status_var.set(self.tr("status_connected"))
        else:
            self.status_var.set(self.tr("status_disconnected"))

    # ---------- UI ----------
    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("vista" if os.name == "nt" else "clam")
        except tk.TclError:
            pass

        try:
            style.configure("Thin.Vertical.TScrollbar", width=8, arrowsize=10)
            style.configure("Thin.Horizontal.TScrollbar", width=8, arrowsize=10)
        except tk.TclError:
            pass

        top = ttk.Frame(self.root, padding=(8, 8, 8, 4))
        top.pack(fill="x")

        ttk.Label(top, text=self.tr("ip_label")).pack(side="left")
        self.ip_var = tk.StringVar(value=self.cfg.get("ip", "192.168.3.132"))
        ttk.Entry(top, textvariable=self.ip_var, width=16).pack(side="left", padx=(5, 8))

        ttk.Label(top, text=self.tr("port_label")).pack(side="left")
        self.port_var = tk.StringVar(value=self.cfg.get("port", "1337"))
        ttk.Entry(top, textvariable=self.port_var, width=6).pack(side="left", padx=(5, 8))

        ttk.Label(top, text=self.tr("volume_label")).pack(side="left")
        self.connect_volume_var = tk.StringVar(value=self.cfg.get("volume", self.VOLUMES[0]))
        self.connect_volume_combo = ttk.Combobox(
            top, textvariable=self.connect_volume_var,
            values=self.VOLUMES, state="readonly", width=22,
        )
        self.connect_volume_combo.pack(side="left", padx=(5, 8))
        self.connect_volume_combo.bind("<<ComboboxSelected>>", self.on_connect_volume_selected)

        self.connect_btn = ttk.Button(top, text=self.tr("connect"), command=self.connection_button)
        self.connect_btn.pack(side="left")

        # self.mount_sd_btn = ttk.Button(top, text="SD", width=4, command=self.toggle_sd_mount)
        # self.mount_sd_btn.pack(side="left", padx=(6, 0))

        self.status_var = tk.StringVar(value=self.tr("status_disconnected"))
        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=12)

        ttk.Button(top, text="⚙", width=3, command=self.open_settings).pack(side="right")

        bar = ttk.Frame(self.root, padding=(8, 4))
        bar.pack(fill="x")

        panes = ttk.Panedwindow(self.root, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=8, pady=5)

        left = ttk.Frame(panes, padding=4)
        right = ttk.Frame(panes, padding=4)
        panes.add(left, weight=1)
        panes.add(right, weight=1)

        left_header = ttk.Frame(left, height=48)
        left_header.pack(fill="x")
        left_header.pack_propagate(False)

        ttk.Label(left_header, text=self.tr("panel_wiiu"), font=("Segoe UI", 11, "bold")).place(x=0, y=0)

        self.remote_location_var = tk.StringVar(value=self.remote_path)
        ttk.Label(
            left_header, textvariable=self.remote_location_var,
            anchor="w", foreground="#555",
        ).place(x=0, y=25, relwidth=1.0)

        self.remote_tree = self._make_tree(
            left,
            columns=("name", "kind", "size", "mtime"),
            headings=(self.tr("col_name"), self.tr("col_kind"), self.tr("col_size"), self.tr("col_mtime")),
            widths=(220, 80, 90, 130),
            on_sort=lambda c: self._sort_remote(c),
        )
        self.remote_tree.bind("<Double-1>", self.remote_double_click)
        self.remote_tree.bind("<Button-3>", self.remote_context_menu)

        right_header = ttk.Frame(right, height=48)
        right_header.pack(fill="x")
        right_header.pack_propagate(False)

        ttk.Label(right_header, text=self.tr("panel_local"), font=("Segoe UI", 11, "bold")).place(x=0, y=0)

        self.drive_var = tk.StringVar()
        self.drive_combo = ttk.Combobox(
            right_header, textvariable=self.drive_var,
            state="readonly", width=10,
        )
        self.drive_combo.place(relx=1.0, x=-1, y=25, anchor="ne", height=22)
        self.drive_combo.bind("<<ComboboxSelected>>", self.on_drive_selected)

        self.local_location_var = tk.StringVar(value=self.local_path)
        ttk.Label(
            right_header, textvariable=self.local_location_var,
            anchor="w", foreground="#555",
        ).place(x=0, y=25, relwidth=1.0, width=-140)

        self.local_tree = self._make_tree(
            right,
            columns=("name", "kind", "size", "mtime"),
            headings=(self.tr("col_name"), self.tr("col_kind"), self.tr("col_size"), self.tr("col_mtime")),
            widths=(300, 80, 90, 130),
            on_sort=lambda c: self._sort_local(c),
        )
        self.local_tree.bind("<Double-1>", self.local_double_click)
        self.local_tree.bind("<Button-3>", self.local_context_menu)

        self._populate_drives()

        actions = ttk.Frame(self.root, padding=(8, 3, 8, 8))
        actions.pack(fill="x")

        self.progress_var = tk.StringVar(value=self.tr("progress_waiting"))
        ttk.Label(actions, textvariable=self.progress_var).pack(side="right", padx=(10, 0))

        progress_frame = ttk.Frame(self.root, padding=(8, 0, 8, 5))
        progress_frame.pack(fill="x")
        self.progressbar = ttk.Progressbar(progress_frame, mode="determinate", maximum=100)
        self.progressbar.pack(fill="x")

        log_frame = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        log_frame.pack(fill="x")
        ttk.Label(log_frame, text=self.tr("log_label")).pack(anchor="w")
        self.log = tk.Text(log_frame, height=3, wrap="word", state="disabled",
                           font=("Consolas", 8))
        self.log.pack(fill="x")

    def _make_tree(self, parent, columns, headings, widths, on_sort):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(
            frame,
            columns=columns,
            show="tree headings",
            selectmode="extended",
        )
        tree.heading("#0", text="", command=lambda: on_sort("name"))
        tree.column("#0", width=30, minwidth=30, stretch=False)
        for col, head, w in zip(columns, headings, widths):
            tree.heading(col, text=head, command=lambda c=col: on_sort(c))
            anchor = "e" if col == "size" else "w"
            tree.column(col, width=w, anchor=anchor)

        vs = ttk.Scrollbar(
            frame, orient="vertical", command=tree.yview,
            style="Thin.Vertical.TScrollbar",
        )
        hs = ttk.Scrollbar(
            frame, orient="horizontal", command=tree.xview,
            style="Thin.Horizontal.TScrollbar",
        )
        tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        tree.grid(row=0, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        tree.tag_configure("dir", foreground="#1b5790")
        tree.tag_configure("file", foreground="#202020")
        tree.tag_configure("parent", foreground="#666666")

        return tree

    def _populate_drives(self):
        drives = []
        if os.name == "nt":
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                d = letter + ":\\"
                if os.path.exists(d):
                    drives.append(d)
        else:
            drives = ["/"]
        if not drives:
            drives = [os.path.abspath(os.sep)]
        self.drive_combo["values"] = drives
        cur = os.path.splitdrive(self.local_path)[0]
        selected = next((d for d in drives if d.rstrip("\\/").lower() == cur.lower()), drives[0])
        self.drive_var.set(selected)

    # ---------- логи ----------
    def _log(self, text):
        line = str(text)
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        if self.cfg.get("log_to_file"):
            try:
                with open(LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {line}\n")
            except Exception:
                pass

    # ---------- hotkeys ----------
    def _init_hotkeys(self):
        self.root.bind("<F3>", lambda e: self._view_focused())
        self.root.bind("<F4>", lambda e: self._edit_focused())
        self.root.bind("<F5>", lambda e: self._copy_focused())
        self.root.bind("<F6>", lambda e: self._move_focused())
        self.root.bind("<F7>", lambda e: self._mkdir_focused())
        self.root.bind("<Delete>", lambda e: self._delete_focused())
        self.root.bind("<Control-a>", lambda e: self._select_all_focused())
        self.root.bind("<Return>", lambda e: self._enter_focused())
        self.root.bind("<F2>", lambda e: self._rename_focused())

    def _focused_tree(self):
        w = self.root.focus_get()
        if w is self.remote_tree:
            return "remote"
        if w is self.local_tree:
            return "local"
        return None

    def _select_all_focused(self):
        w = self.root.focus_get()
        if w in (self.remote_tree, self.local_tree):
            w.selection_set(w.get_children())

    def _delete_focused(self):
        w = self.root.focus_get()
        if w is self.remote_tree:
            self.delete_remote()
        elif w is self.local_tree:
            self.delete_local()

    def _enter_focused(self):
        w = self.root.focus_get()
        if w is self.remote_tree:
            self.remote_double_click()
        elif w is self.local_tree:
            self.local_double_click()

    def _rename_focused(self):
        w = self.root.focus_get()
        if w is self.remote_tree:
            self.rename_remote()
        elif w is self.local_tree:
            self.rename_local()

    def _mkdir_focused(self):
        w = self.root.focus_get()
        if w is self.remote_tree:
            self.remote_mkdir()
        elif w is self.local_tree:
            self.local_mkdir()

    def _view_focused(self):
        side = self._focused_tree()
        if side == "remote":
            self._view_remote()
        elif side == "local":
            self._view_local()

    def _edit_focused(self):
        side = self._focused_tree()
        if side == "remote":
            self._edit_remote()
        elif side == "local":
            self._edit_local()

    def _copy_focused(self):
        side = self._focused_tree()
        if side == "remote":
            self.download_selected()
        elif side == "local":
            self.upload_selected()

    def _move_focused(self):
        side = self._focused_tree()
        if side == "remote":
            self._move_remote_to_local()
        elif side == "local":
            self._move_local_to_remote()

    # ---------- сортировка ----------
    def _sort_remote(self, col):
        s = self.remote_sort
        if s["col"] == col:
            s["reverse"] = not s["reverse"]
        else:
            s["col"] = col
            s["reverse"] = False
        self._refresh_remote()

    def _sort_local(self, col):
        s = self.local_sort
        if s["col"] == col:
            s["reverse"] = not s["reverse"]
        else:
            s["col"] = col
            s["reverse"] = False
        self._refresh_local()

    # ---------- периодические задачи ----------
    def _heartbeat(self):
        if self.client and not self.busy:
            try:
                alive = self.client.is_alive()
                if not alive:
                    self._log(self.tr("log_reconnect"))
                    self._try_reconnect()
            except Exception:
                pass
        if not self.closing:
            self.root.after(5000, self._heartbeat)

    def _try_reconnect(self):
        if not self.client:
            return
        old = self.client
        try:
            old.disconnect()
        except Exception:
            pass
        self.client = None
        try:
            new = wupclient(self.ip_var.get().strip(),
                            int(self.port_var.get().strip()),
                            cwd=self.remote_path)
            self.client = new
            self._log(self.tr("log_reconnect_ok"))
            self.messages.put(("refresh_remote", None))
        except Exception as exc:
            self._log(self.tr("log_reconnect_fail", exc=exc))
            self.status_var.set(self.tr("status_disconnected_ok"))

    # ---------- обработка сообщений из потоков ----------
    def _poll_messages(self):
        try:
            while True:
                kind, value = self.messages.get_nowait()
                if kind == "status":
                    self.status_var.set(value)
                elif kind == "log":
                    self._log(value)
                elif kind == "error":
                    messagebox.showerror(self.tr("dialog_error"), value, parent=self.root)
                elif kind == "info":
                    messagebox.showinfo(self.tr("dialog_info"), value, parent=self.root)
                elif kind == "refresh_remote":
                    self._refresh_remote()
                elif kind == "refresh_local":
                    self._refresh_local()
                elif kind == "progress":
                    filename, done, total, speed = value
                    size_text = format_size(done)
                    speed_text = format_size(int(speed)) + "/s"
                    if total:
                        percent = min(100, int(done * 100 / total)) if total else 0
                        remaining = max(0, total - done)
                        eta = remaining / speed if speed > 0 else 0
                        eta_text = self._format_eta(eta)
                        self.progressbar.configure(mode="determinate", maximum=100, value=percent)
                        self.progress_var.set(self.tr(
                            "progress_format_full",
                            name=os.path.basename(filename),
                            done=size_text,
                            total=format_size(total),
                            speed=speed_text,
                            eta=eta_text,
                        ))
                    else:
                        self.progressbar.configure(mode="indeterminate")
                        self.progressbar.start(10)
                        self.progress_var.set(self.tr(
                            "progress_format_simple",
                            name=os.path.basename(filename),
                            done=size_text,
                            speed=speed_text,
                        ))
                elif kind == "progress_done":
                    self.progressbar.stop()
                    self.progressbar.configure(mode="determinate", maximum=100, value=0)
                    self.progress_var.set(value or self.tr("progress_waiting"))
                elif kind == "operation_done":
                    self.busy = False
                    self.connect_btn.configure(state="normal")
                    self.connect_btn.configure(
                        text=self.tr("disconnect") if self.client else self.tr("connect")
                    )
                elif kind == "connect_done":
                    self.connect_btn.configure(state="normal")
                    self.connect_btn.configure(
                        text=self.tr("disconnect") if self.client else self.tr("connect")
                    )
                elif kind == "disconnected":
                    self.client = None
                    self.sd_mounted = False
                    self.connect_btn.configure(text=self.tr("connect"), state="normal")
                    self.remote_tree.delete(*self.remote_tree.get_children())
                    self.status_var.set(self.tr("status_disconnected_ok"))
                    self.remote_location_var.set(self.connect_volume_var.get() or self.remote_path)
                elif kind == "sd_state":
                    self.sd_mounted = bool(value)
                    try:
                        self.mount_sd_btn.configure(
                            text="SD⏏" if self.sd_mounted else "SD"
                        )
                    except Exception:
                        pass
        except queue.Empty:
            pass
        if not self.closing:
            self.root.after(100, self._poll_messages)

    def _format_eta(self, sec):
        sec = int(sec)
        if sec < 60:
            return self.tr("eta_sec", n=sec)
        if sec < 3600:
            return self.tr("eta_min", m=sec // 60, s=sec % 60)
        return self.tr("eta_hour", h=sec // 3600, m=(sec % 3600) // 60)

    # ---------- worker ----------
    def _run_worker(self, title_key, fn, after=None, **fmt):
        if self.busy:
            messagebox.showinfo(self.tr("dialog_wait"), self.tr("dialog_busy_msg"), parent=self.root)
            return
        if self.client is None:
            messagebox.showwarning(self.tr("dialog_no_connection"), self.tr("dialog_no_connection_msg"), parent=self.root)
            return
        title = self.tr(title_key, **fmt) if fmt else self.tr(title_key)
        self.busy = True
        self.cancel_event.clear()
        self.status_var.set(self.tr("progress_prefix", title=title))
        self.progressbar.stop()
        self.progressbar.configure(mode="determinate", value=0)

        def work():
            try:
                result = fn()
                self.messages.put(("log", result if result is not None else title + ": " + self.tr("progress_ready")))
                if after:
                    for msg in after:
                        self.messages.put((msg, None))
                if self.cancel_event.is_set():
                    self.messages.put(("status", self.tr("status_copy_stopped")))
                else:
                    self.messages.put(("status", self.tr("status_connected")))
            except CopyCancelled:
                self.messages.put(("log", self.tr("status_copy_stopping")))
                self.messages.put(("status", self.tr("status_copy_stopped")))
                self.messages.put(("refresh_local", None))
                self.messages.put(("refresh_remote", None))
            except Exception as exc:
                self.messages.put(("error", str(exc)))
                self.messages.put(("status", self.tr("status_error_op")))
            finally:
                self.messages.put(
                    ("progress_done",
                     self.tr("progress_done") if not self.cancel_event.is_set() else self.tr("progress_stopped"))
                )
                self.messages.put(("operation_done", None))
                if self.closing:
                    self._close_client_from_worker()

        threading.Thread(target=work, daemon=True).start()

    # ---------- SD card ----------
    def toggle_sd_mount(self):
        if self.client is None:
            messagebox.showwarning(self.tr("dialog_no_connection"), self.tr("dialog_no_connection_msg"), parent=self.root)
            return
        if self.busy:
            messagebox.showinfo(self.tr("dialog_wait"), self.tr("dialog_busy_msg"), parent=self.root)
            return
        if self.sd_mounted:
            self._unmount_sd()
        else:
            self._mount_sd()

    def _mount_sd(self):
        def work():
            self.client.mount_sd()
            self.messages.put(("sd_state", True))
            self._log(self.tr("log_mount_sd_ok"))
            return self.tr("log_mount_sd_ok")

        self._run_worker("progress_title_mount_sd", work)
        self.root.after(300, lambda: self.messages.put(("info", self.tr("dialog_mount_sd_ok"))))

    def _unmount_sd(self):
        def work():
            self.client.unmount_sd()
            self.messages.put(("sd_state", False))
            if self.remote_path.startswith(self.SD_MOUNT_PATH):
                self.remote_path = "/vol/storage_mlc01"
                try:
                    self.client.cwd = self.remote_path
                except Exception:
                    pass
            self._log(self.tr("log_unmount_sd_ok"))
            self.messages.put(("refresh_remote", None))
            return self.tr("log_unmount_sd_ok")

        self._run_worker("progress_title_mount_sd", work)

    # ---------- подключение ----------
    def connection_button(self):
        if self.busy:
            self.cancel_event.set()
            self.connect_btn.configure(state="disabled")
            self.status_var.set(self.tr("status_stopping"))
            self._log(self.tr("status_stopping"))
            return
        if self.client is not None:
            self.connect_btn.configure(state="disabled")
            self.status_var.set(self.tr("status_disconnecting"))

            def work():
                client = self.client
                self.client = None
                if client is not None:
                    try:
                        client.disconnect()
                    except Exception:
                        pass
                self.messages.put(("disconnected", None))
                self.messages.put(("log", self.tr("log_disconnected")))

            threading.Thread(target=work, daemon=True).start()
            return
        self.connect()

    def connect(self):
        if self.busy:
            return
        ip = self.ip_var.get().strip()
        try:
            port = int(self.port_var.get().strip())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror(self.tr("dialog_error"), self.tr("dialog_error_port"), parent=self.root)
            return
        volume = self.connect_volume_var.get().strip() or self.VOLUMES[0]

        self.status_var.set(self.tr("status_connecting"))
        self.connect_btn.configure(state="disabled")

        def work():
            new_client = None
            try:
                new_client = wupclient(ip, port, cwd=volume)
                if self.closing:
                    new_client.disconnect()
                    return
                self.client = new_client
                self.remote_path = volume
                self.messages.put(("status", self.tr("status_connected_to", ip=ip, port=port, volume=volume)))
                self.messages.put(("log", self.tr("log_connected", ip=ip, port=port, volume=volume)))

                # Автоматически монтируем SD-карту сразу после подключения
                try:
                    new_client.mount_sd()
                    self.sd_mounted = True
                    self.messages.put(("sd_state", True))
                    self._log(self.tr("log_mount_sd_ok"))
                except Exception as exc:
                    self.sd_mounted = False
                    self.messages.put(("sd_state", False))
                    self._log(self.tr("log_mount_sd_fail", code=0) + f" — {exc}")

                self.root.after(0, lambda v=volume: self.remote_location_var.set(v))
                self.messages.put(("refresh_remote", None))
                self.cfg["ip"] = ip
                self.cfg["port"] = str(port)
                self.cfg["volume"] = volume
                save_config(self.cfg)
            except Exception as exc:
                if new_client:
                    try:
                        new_client.disconnect()
                    except Exception:
                        pass
                self.client = None
                self.messages.put(
                    ("error", self.tr("status_connecting_fail", ip=ip, port=port, exc=exc))
                )
                self.messages.put(("status", self.tr("status_disconnected_ok")))
            finally:
                self.messages.put(("connect_done", None))

        threading.Thread(target=work, daemon=True).start()

    def _close_client_from_worker(self):
        client = self.client
        self.client = None
        if client is not None:
            try:
                client.disconnect()
            except Exception:
                pass

    # ---------- настройки ----------
    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title(self.tr("settings_title"))
        win.geometry("460x200")
        win.transient(self.root)
        win.grab_set()

        lang_frame = ttk.Frame(win)
        lang_frame.pack(anchor="w", padx=12, pady=(12, 6), fill="x")
        ttk.Label(lang_frame, text=self.tr("settings_language")).pack(side="left")
        lang_var = tk.StringVar(value=self.lang)
        lang_combo = ttk.Combobox(
            lang_frame, textvariable=lang_var, state="readonly", width=16,
            values=("ru", "en"),
        )
        lang_combo.pack(side="left", padx=(8, 0))

        logfile_var = tk.BooleanVar(value=self.cfg.get("log_to_file", False))
        md5_var = tk.BooleanVar(value=self.cfg.get("verify_md5", False))

        ttk.Checkbutton(win, text=self.tr("settings_log_to_file", path=LOG_PATH), variable=logfile_var).pack(anchor="w", padx=12, pady=2)
        ttk.Checkbutton(win, text=self.tr("settings_verify_md5"), variable=md5_var).pack(anchor="w", padx=12, pady=2)

        ttk.Label(win, text=self.tr("settings_file_path", path=CONFIG_PATH), foreground="#666").pack(anchor="w", padx=12, pady=(12, 0))

        def apply():
            new_lang = lang_var.get()
            self.cfg["log_to_file"] = logfile_var.get()
            self.cfg["verify_md5"] = md5_var.get()
            lang_changed = new_lang != self.lang
            self.cfg["language"] = new_lang
            save_config(self.cfg)
            win.destroy()
            if lang_changed:
                self.lang = new_lang
                self._rebuild_ui()
            messagebox.showinfo(self.tr("settings_title"), self.tr("settings_saved"), parent=self.root)

        btns = ttk.Frame(win)
        btns.pack(fill="x", pady=12, padx=12)
        ttk.Button(btns, text=self.tr("settings_save"), command=apply).pack(side="right")
        ttk.Button(btns, text=self.tr("settings_cancel"), command=win.destroy).pack(side="right", padx=6)

    # ---------- обновление дерева ----------
    def _refresh_remote(self):
        if not self.client:
            self.remote_tree.delete(*self.remote_tree.get_children())
            return
        path = self.remote_path
        try:
            raw = self.client.ls(path, True) or []
            entries = []
            for e in raw:
                name = e["name"]
                if name in (".", "..", ""):
                    continue
                entries.append({
                    "name": name,
                    "is_file": e["is_file"],
                    "is_dir": not e["is_file"],
                    "size": 0,
                    "mtime": 0,
                })

            col = self.remote_sort["col"]
            rev = self.remote_sort["reverse"]

            def sort_key(e):
                name_key = e["name"].lower()
                if col == "name":
                    inner = name_key
                elif col == "kind":
                    inner = "1" if e["is_file"] else "0"
                elif col == "size":
                    inner = e.get("size", 0)
                elif col == "mtime":
                    inner = e.get("mtime", 0)
                else:
                    inner = name_key
                return (0 if e["is_dir"] else 1, inner)

            entries.sort(key=sort_key, reverse=rev)

            self.remote_tree.delete(*self.remote_tree.get_children())
            if path != "/":
                self.remote_tree.insert(
                    "", "end", iid="__remote_parent__",
                    text="📁", values=("..", self.tr("kind_parent"), "", ""),
                    tags=("parent",),
                )
            for e in entries:
                icon = "📄" if e["is_file"] else "📁"
                iid = posixpath.join(path, e["name"])
                size_txt = format_size(e["size"]) if e["is_file"] and e["size"] else ""
                self.remote_tree.insert(
                    "", "end", iid=iid, text=icon,
                    values=(e["name"], self.tr("kind_file") if e["is_file"] else self.tr("kind_dir"), size_txt, ""),
                    tags=("file" if e["is_file"] else "dir",),
                )
            self.remote_location_var.set(path)
        except Exception as exc:
            self._log(self.tr("log_read_remote_fail", exc=exc))

    def _refresh_local(self):
        self.local_path = os.path.abspath(self.local_path)
        self.local_location_var.set(self.local_path)
        self.local_tree.delete(*self.local_tree.get_children())
        try:
            parent = os.path.dirname(self.local_path.rstrip(os.sep))
            if parent and parent != self.local_path:
                self.local_tree.insert(
                    "", "end", iid="__local_parent__",
                    text="📁", values=("..", self.tr("kind_parent"), "", ""),
                    tags=("parent",),
                )
            entries = []
            for entry in os.scandir(self.local_path):
                is_dir = entry.is_dir(follow_symlinks=False)
                try:
                    st = entry.stat(follow_symlinks=False)
                    size = st.st_size
                    mtime = st.st_mtime
                except OSError:
                    size = 0
                    mtime = 0
                entries.append({
                    "name": entry.name,
                    "is_file": not is_dir,
                    "is_dir": is_dir,
                    "size": size,
                    "mtime": mtime,
                    "path": entry.path,
                })

            col = self.local_sort["col"]
            rev = self.local_sort["reverse"]

            def sort_key(e):
                name_key = e["name"].lower()
                if col == "name":
                    inner = name_key
                elif col == "kind":
                    inner = "1" if e["is_file"] else "0"
                elif col == "size":
                    inner = e.get("size", 0)
                elif col == "mtime":
                    inner = e.get("mtime", 0)
                else:
                    inner = name_key
                return (0 if e["is_dir"] else 1, inner)

            entries.sort(key=sort_key, reverse=rev)

            for e in entries:
                icon = "📄" if e["is_file"] else "📁"
                size_txt = format_size(e["size"]) if e["is_file"] else ""
                self.local_tree.insert(
                    "", "end", iid=os.path.abspath(e["path"]),
                    text=icon,
                    values=(e["name"], self.tr("kind_file") if e["is_file"] else self.tr("kind_dir"),
                            size_txt, format_time(e["mtime"])),
                    tags=("file" if e["is_file"] else "dir",),
                )
            if os.name == "nt":
                drive = os.path.splitdrive(self.local_path)[0] + "\\"
                if drive and drive in self.drive_combo["values"]:
                    self.drive_var.set(drive)
        except Exception as exc:
            self._log(self.tr("log_read_local_fail", exc=exc))

    # ---------- навигация ----------
    def on_drive_selected(self, event=None):
        drive = self.drive_var.get()
        if drive and os.path.isdir(drive):
            self.local_path = os.path.abspath(drive)
            self._refresh_local()

    def on_connect_volume_selected(self, event=None):
        new_volume = self.connect_volume_var.get().strip()
        if not new_volume:
            return
        self.remote_location_var.set(new_volume)
        if not self.client:
            self.remote_path = new_volume
            self.cfg["volume"] = new_volume
            save_config(self.cfg)
            return
        if self.busy:
            messagebox.showinfo(self.tr("dialog_wait"), self.tr("dialog_busy_msg"), parent=self.root)
            return
        if new_volume == self.remote_path:
            return

        # SD: перемонтировать перед входом
        if new_volume == self.SD_MOUNT_PATH:
            def work():
                try:
                    self.client.unmount_sd()
                except Exception:
                    pass
                self.client.mount_sd()
                self.messages.put(("sd_state", True))
                self.client.cwd = new_volume
                self.remote_path = new_volume
                self.cfg["volume"] = new_volume
                save_config(self.cfg)
                self.messages.put(("refresh_remote", None))
                return self.tr("log_mount_sd_ok")

            self._run_worker("progress_title_mount_sd", work)
            return

        def work():
            ret, handle = self.client.FSA_OpenDir(self.client.get_fsa_handle(), new_volume)
            if ret != 0:
                raise OSError(f"Volume {new_volume} unavailable (FSA code 0x{ret:08X})")
            self.client.FSA_CloseDir(self.client.get_fsa_handle(), handle)
            self.client.cwd = new_volume
            self.remote_path = new_volume
            self.cfg["volume"] = new_volume
            save_config(self.cfg)
            self.messages.put(("refresh_remote", None))
            return self.tr("log_volume_switched", volume=new_volume)

        self._run_worker("progress_title_volume", work)

    def navigate_remote(self, target):
        if not self.client:
            return
        target = posixpath.normpath(target.replace("\\", "/"))
        if not target.startswith("/"):
            target = posixpath.join(self.remote_path, target)

        def work():
            ret, handle = self.client.FSA_OpenDir(self.client.get_fsa_handle(), target)
            if ret != 0:
                raise OSError(f"Failed to open directory {target} (code 0x{ret:08X})")
            self.client.FSA_CloseDir(self.client.get_fsa_handle(), handle)
            self.remote_path = target
            self.messages.put(("refresh_remote", None))
            return self.tr("log_open_dir", path=target)

        self._run_worker("progress_title_navigate", work)

    def navigate_local(self, target):
        if os.path.isdir(target):
            self.local_path = os.path.abspath(target)
            self.cfg["local_path"] = self.local_path
            save_config(self.cfg)
            self._refresh_local()

    def remote_double_click(self, event=None):
        sel = self.remote_tree.selection()
        if not sel:
            return
        item = sel[0]
        if item == "__remote_parent__":
            self.navigate_remote(posixpath.dirname(self.remote_path.rstrip("/")) or "/")
            return
        vals = self.remote_tree.item(item, "values")
        kind = vals[1] if len(vals) > 1 else ""
        if kind == self.tr("kind_dir"):
            self.navigate_remote(item)
        else:
            self.download_selected()

    def local_double_click(self, event=None):
        sel = self.local_tree.selection()
        if not sel:
            return
        item = sel[0]
        if item == "__local_parent__":
            self.navigate_local(os.path.dirname(self.local_path.rstrip(os.sep)) or os.path.abspath(os.sep))
        elif os.path.isdir(item):
            self.navigate_local(item)
        else:
            self.upload_selected()

    # ---------- контекстное меню ----------
    def remote_context_menu(self, event):
        iid = self.remote_tree.identify_row(event.y)
        if iid:
            if iid not in self.remote_tree.selection():
                self.remote_tree.selection_set(iid)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=self.tr("menu_view"), command=self._view_remote)
        menu.add_command(label=self.tr("menu_edit"), command=self._edit_remote)
        menu.add_separator()
        menu.add_command(label=self.tr("menu_download"), command=self.download_selected)
        menu.add_command(label=self.tr("menu_move_to_local"), command=self._move_remote_to_local)
        menu.add_separator()
        menu.add_command(label=self.tr("menu_rename"), command=self.rename_remote)
        menu.add_command(label=self.tr("menu_delete_remote"), command=self.delete_remote)
        menu.add_separator()
        menu.add_command(label=self.tr("menu_mkdir_remote"), command=self.remote_mkdir)
        menu.add_command(label=self.tr("menu_refresh"), command=self._refresh_remote)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def local_context_menu(self, event):
        iid = self.local_tree.identify_row(event.y)
        if iid:
            if iid not in self.local_tree.selection():
                self.local_tree.selection_set(iid)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=self.tr("menu_view"), command=self._view_local)
        menu.add_command(label=self.tr("menu_edit"), command=self._edit_local)
        menu.add_separator()
        menu.add_command(label=self.tr("menu_upload"), command=self.upload_selected)
        menu.add_command(label=self.tr("menu_move_to_remote"), command=self._move_local_to_remote)
        menu.add_separator()
        menu.add_command(label=self.tr("menu_rename"), command=self.rename_local)
        menu.add_command(label=self.tr("menu_delete_local"), command=self.delete_local)
        menu.add_separator()
        menu.add_command(label=self.tr("menu_mkdir_local"), command=self.local_mkdir)
        menu.add_command(label=self.tr("menu_refresh"), command=self._refresh_local)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ---------- операции ----------
    def remote_mkdir(self):
        if not self.client:
            messagebox.showwarning(self.tr("dialog_no_connection"), self.tr("dialog_no_connection_msg"), parent=self.root)
            return
        if self.busy:
            return
        name = simpledialog.askstring(self.tr("dialog_new_folder_remote"),
                                      self.tr("dialog_folder_name"), parent=self.root)
        if not name:
            return
        if "/" in name or "\\" in name or name in (".", ".."):
            messagebox.showerror(self.tr("dialog_error"), self.tr("dialog_folder_bad"), parent=self.root)
            return
        target = posixpath.join(self.remote_path, name)

        def work():
            ret = self.client.mkdir(target, 0x600)
            if ret != 0:
                raise OSError(self.tr("log_folder_create_fail", path=target, code=ret))
            return self.tr("log_folder_created", path=target)

        self._run_worker("progress_title_mkdir_remote", work, ["refresh_remote"])

    def local_mkdir(self):
        name = simpledialog.askstring(self.tr("dialog_new_folder_local"),
                                      self.tr("dialog_folder_name"), parent=self.root)
        if not name:
            return
        try:
            os.makedirs(os.path.join(self.local_path, name), exist_ok=False)
            self._refresh_local()
        except Exception as exc:
            messagebox.showerror(self.tr("dialog_error"), str(exc), parent=self.root)

    def rename_remote(self):
        if not self.client:
            return
        sel = self._selected_remote(return_list=True)
        if len(sel) != 1:
            messagebox.showinfo(self.tr("dialog_rename"), self.tr("dialog_rename_one"), parent=self.root)
            return
        old = sel[0]
        old_name = posixpath.basename(old)
        new_name = simpledialog.askstring(self.tr("dialog_rename"),
                                          self.tr("dialog_rename_new"),
                                          initialvalue=old_name, parent=self.root)
        if not new_name or new_name == old_name:
            return
        new_path = posixpath.join(posixpath.dirname(old), new_name)

        def work():
            ret = self.client.rename(old, new_path)
            if ret != 0:
                raise OSError(self.tr("log_rename_fail", code=ret))
            return self.tr("log_renamed", old=old, new=new_path)

        self._run_worker("progress_title_rename_remote", work, ["refresh_remote"])

    def rename_local(self):
        sel = self._selected_local(return_list=True)
        if len(sel) != 1:
            messagebox.showinfo(self.tr("dialog_rename"), self.tr("dialog_rename_one"), parent=self.root)
            return
        old = sel[0]
        old_name = os.path.basename(old.rstrip(os.sep))
        new_name = simpledialog.askstring(self.tr("dialog_rename"),
                                          self.tr("dialog_rename_new"),
                                          initialvalue=old_name, parent=self.root)
        if not new_name or new_name == old_name:
            return
        new_path = os.path.join(os.path.dirname(old.rstrip(os.sep)), new_name)
        try:
            os.rename(old, new_path)
            self._refresh_local()
            self._log(self.tr("log_renamed", old=old, new=new_path))
        except Exception as exc:
            messagebox.showerror(self.tr("dialog_error"), str(exc), parent=self.root)

    def _selected_remote(self, return_list=False):
        sel = [i for i in self.remote_tree.selection() if i != "__remote_parent__"]
        if return_list:
            return sel
        return sel[0] if sel else None

    def _selected_local(self, return_list=False):
        sel = [i for i in self.local_tree.selection() if i != "__local_parent__"]
        if return_list:
            return sel
        return sel[0] if sel else None

    # ---------- просмотр / редактирование ----------
    def _open_external(self, path):
        try:
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            messagebox.showerror(self.tr("dialog_view"), str(exc), parent=self.root)

    def _view_local(self):
        sel = self._selected_local(return_list=True)
        if len(sel) != 1 or os.path.isdir(sel[0]):
            return
        self._open_external(sel[0])

    def _edit_local(self):
        sel = self._selected_local(return_list=True)
        if len(sel) != 1 or os.path.isdir(sel[0]):
            return
        self._open_external(sel[0])

    def _view_remote(self):
        if not self.client:
            return
        sel = self._selected_remote(return_list=True)
        if len(sel) != 1:
            messagebox.showinfo(self.tr("dialog_view"), self.tr("dialog_view_one"), parent=self.root)
            return
        remote = sel[0]
        vals = self.remote_tree.item(remote, "values")
        if len(vals) < 2 or vals[1] != self.tr("kind_file"):
            return

        def work():
            import tempfile
            tmpdir = tempfile.mkdtemp(prefix="wiiu_view_")
            local = os.path.join(tmpdir, posixpath.basename(remote))
            self.client.dl(remote, local_filename=local,
                           progress_callback=self._progress_callback,
                           cancel_event=self.cancel_event)
            return local

        self._run_worker_with_callback("progress_title_view", work,
                                       lambda p: self._open_external(p))

    def _edit_remote(self):
        if not self.client:
            return
        sel = self._selected_remote(return_list=True)
        if len(sel) != 1:
            messagebox.showinfo(self.tr("dialog_edit"), self.tr("dialog_edit_one"), parent=self.root)
            return
        remote = sel[0]
        vals = self.remote_tree.item(remote, "values")
        if len(vals) < 2 or vals[1] != self.tr("kind_file"):
            return

        def work():
            import tempfile
            tmpdir = tempfile.mkdtemp(prefix="wiiu_edit_")
            local = os.path.join(tmpdir, posixpath.basename(remote))
            self.client.dl(remote, local_filename=local,
                           progress_callback=self._progress_callback,
                           cancel_event=self.cancel_event)
            return local

        self._run_worker_with_callback("progress_title_edit", work,
                                       lambda p: self._do_edit_remote(remote, p))

    def _do_edit_remote(self, remote, local):
        self._open_external(local)
        if not messagebox.askyesno(
            self.tr("dialog_edit"),
            self.tr("dialog_edit_question", path=local),
            parent=self.root,
        ):
            return

        def work():
            self.client.up(local, remote,
                           progress_callback=self._progress_callback,
                           cancel_event=self.cancel_event)
            return self.tr("log_changes_uploaded", path=remote)

        self._run_worker("progress_title_upload_changes", work, ["refresh_remote"])

    def _run_worker_with_callback(self, title_key, fn, callback):
        if self.busy:
            messagebox.showinfo(self.tr("dialog_wait"), self.tr("dialog_busy_msg"), parent=self.root)
            return
        if self.client is None:
            messagebox.showwarning(self.tr("dialog_no_connection"), self.tr("dialog_no_connection_msg"), parent=self.root)
            return
        title = self.tr(title_key)
        self.busy = True
        self.cancel_event.clear()
        self.status_var.set(self.tr("progress_prefix", title=title))
        self.progressbar.stop()
        self.progressbar.configure(mode="determinate", value=0)

        def work():
            try:
                result = fn()
                self.messages.put(("log", title + ": " + self.tr("progress_ready")))
                self.root.after(0, lambda r=result: callback(r))
                self.messages.put(("status", self.tr("status_connected")))
            except CopyCancelled:
                self.messages.put(("log", self.tr("status_copy_stopping")))
                self.messages.put(("status", self.tr("progress_stopped")))
            except Exception as exc:
                self.messages.put(("error", str(exc)))
                self.messages.put(("status", self.tr("status_error_op")))
            finally:
                self.messages.put(("progress_done", self.tr("progress_done")))
                self.messages.put(("operation_done", None))

        threading.Thread(target=work, daemon=True).start()

    # ---------- копирование ----------
    def download_selected(self):
        if not self.client:
            messagebox.showwarning(self.tr("dialog_no_connection"), self.tr("dialog_no_connection_msg"), parent=self.root)
            return
        items = self._selected_remote(return_list=True)
        if not items:
            messagebox.showinfo(self.tr("dialog_select_file"), self.tr("dialog_select_remote"), parent=self.root)
            return

        def work():
            for remote in items:
                if self.cancel_event.is_set():
                    raise CopyCancelled()
                name = posixpath.basename(remote.rstrip("/")) or "download"
                local_target = os.path.join(self.local_path, name)
                self._download_path(remote, local_target)
            return self.tr("log_downloaded", count=len(items))

        self._run_worker("progress_title_download", work, ["refresh_local"])

    def _download_path(self, remote, local):
        if self.cancel_event.is_set():
            raise CopyCancelled()
        fsa = self.client.get_fsa_handle()
        ret, dir_handle = self.client.FSA_OpenDir(fsa, remote)
        if ret == 0:
            os.makedirs(local, exist_ok=True)
            try:
                while True:
                    if self.cancel_event.is_set():
                        raise CopyCancelled()
                    r, entry = self.client.FSA_ReadDir(fsa, dir_handle)
                    if r != 0 or not entry:
                        break
                    name = entry["name"]
                    if name in (".", "..", ""):
                        continue
                    child_remote = posixpath.join(remote, name)
                    child_local = os.path.join(local, name)
                    if entry["is_file"]:
                        self.messages.put(("log", self.tr("log_download", path=child_remote)))
                        self.client.dl(
                            child_remote,
                            local_filename=child_local,
                            progress_callback=self._progress_callback,
                            cancel_event=self.cancel_event,
                        )
                    else:
                        self._download_path(child_remote, child_local)
            finally:
                self.client.FSA_CloseDir(fsa, dir_handle)
            return
        os.makedirs(os.path.dirname(os.path.abspath(local)), exist_ok=True)
        self.messages.put(("log", self.tr("log_download", path=remote)))
        self.client.dl(
            remote,
            local_filename=local,
            progress_callback=self._progress_callback,
            cancel_event=self.cancel_event,
        )
        if self.cfg.get("verify_md5"):
            try:
                m1 = md5_of_file(local)
                self._log(self.tr("log_md5", name=os.path.basename(local), hash=m1))
            except Exception as exc:
                self._log(self.tr("log_md5_fail", exc=exc))

    def upload_selected(self):
        if not self.client:
            messagebox.showwarning(self.tr("dialog_no_connection"), self.tr("dialog_no_connection_msg"), parent=self.root)
            return
        items = self._selected_local(return_list=True)
        if not items:
            messagebox.showinfo(self.tr("dialog_select_file"), self.tr("dialog_select_local"), parent=self.root)
            return
        preview = "\n".join(items[:5])
        if len(items) > 5:
            preview += f"\n… +{len(items) - 5}"
        if not messagebox.askyesno(
            self.tr("dialog_upload_title"),
            self.tr("dialog_upload_confirm", count=len(items), preview=preview, path=self.remote_path),
            parent=self.root,
        ):
            return

        def work():
            for local in items:
                if self.cancel_event.is_set():
                    raise CopyCancelled()
                target = posixpath.join(self.remote_path, os.path.basename(local.rstrip(os.sep)))
                self._upload_path(local, target)
            return self.tr("log_uploaded", count=len(items))

        self._run_worker("progress_title_upload", work, ["refresh_remote"])

    def _upload_path(self, local, remote):
        if self.cancel_event.is_set():
            raise CopyCancelled()
        if os.path.isdir(local):
            ret = self.client.mkdir(remote, 0x600)
            if ret != 0:
                fsa = self.client.get_fsa_handle()
                check, handle = self.client.FSA_OpenDir(fsa, remote)
                if check != 0:
                    raise OSError(self.tr("log_folder_create_fail", path=remote, code=ret))
                self.client.FSA_CloseDir(fsa, handle)
            for name in os.listdir(local):
                if self.cancel_event.is_set():
                    raise CopyCancelled()
                self._upload_path(os.path.join(local, name), posixpath.join(remote, name))
        else:
            self.messages.put(("log", self.tr("log_upload", path=local)))
            self.client.up(
                local, remote,
                progress_callback=self._progress_callback,
                cancel_event=self.cancel_event,
            )

    # ---------- перемещение ----------
    def _move_remote_to_local(self):
        if not self.client:
            return
        items = self._selected_remote(return_list=True)
        if not items:
            messagebox.showinfo(self.tr("dialog_select"), self.tr("dialog_select_remote"), parent=self.root)
            return

        def work():
            for remote in items:
                if self.cancel_event.is_set():
                    raise CopyCancelled()
                name = posixpath.basename(remote.rstrip("/")) or "download"
                local_target = os.path.join(self.local_path, name)
                self._download_path(remote, local_target)
                ret = self.client.remove(remote)
                if ret != 0:
                    raise OSError(self.tr("log_delete_fail", path=remote, code=ret))
            return self.tr("log_moved_to_local", count=len(items))

        self._run_worker("progress_title_move_local", work, ["refresh_local", "refresh_remote"])

    def _move_local_to_remote(self):
        if not self.client:
            messagebox.showwarning(self.tr("dialog_no_connection"), self.tr("dialog_no_connection_msg"), parent=self.root)
            return
        items = self._selected_local(return_list=True)
        if not items:
            messagebox.showinfo(self.tr("dialog_select"), self.tr("dialog_select_local"), parent=self.root)
            return

        def work():
            for local in items:
                if self.cancel_event.is_set():
                    raise CopyCancelled()
                target = posixpath.join(self.remote_path, os.path.basename(local.rstrip(os.sep)))
                self._upload_path(local, target)
                try:
                    if os.path.isdir(local):
                        shutil.rmtree(local)
                    else:
                        os.remove(local)
                except Exception as exc:
                    self.messages.put(("log", self.tr("log_delete_fail", path=local, code=0)))
            return self.tr("log_moved_to_remote", count=len(items))

        self._run_worker("progress_title_move_remote", work, ["refresh_local", "refresh_remote"])

    # ---------- удаление ----------
    def delete_remote(self):
        if not self.client:
            return
        items = self._selected_remote(return_list=True)
        if not items:
            messagebox.showinfo(self.tr("dialog_select"), self.tr("dialog_select_remote"), parent=self.root)
            return
        preview = "\n".join(items[:5])
        if not messagebox.askyesno(
            self.tr("dialog_delete_remote"),
            self.tr("dialog_delete_confirm", preview=preview),
            parent=self.root,
        ):
            return

        def work():
            for path in items:
                if self.cancel_event.is_set():
                    raise CopyCancelled()
                self.messages.put(("log", self.tr("log_delete", path=path)))
                ret = self.client.remove(path)
                if ret != 0:
                    raise OSError(self.tr("log_delete_fail", path=path, code=ret))
            return self.tr("log_deleted_remote", count=len(items))

        self._run_worker("progress_title_delete_remote", work, ["refresh_remote"])

    def delete_local(self):
        items = self._selected_local(return_list=True)
        if not items:
            messagebox.showinfo(self.tr("dialog_select"), self.tr("dialog_select_local"), parent=self.root)
            return
        preview = "\n".join(items[:5])
        if not messagebox.askyesno(
            self.tr("dialog_delete_local"),
            self.tr("dialog_delete_confirm", preview=preview),
            parent=self.root,
        ):
            return
        try:
            for p in items:
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
            self._refresh_local()
            self._log(self.tr("log_deleted_local", count=len(items)))
        except Exception as exc:
            messagebox.showerror(self.tr("dialog_error"), str(exc), parent=self.root)

    # ---------- прочее ----------
    def _progress_callback(self, filename, done, total, speed):
        self.messages.put(("progress", (filename, done, total, speed)))

    def on_close(self):
        self.closing = True
        try:
            self.cfg["ip"] = self.ip_var.get().strip()
            self.cfg["port"] = self.port_var.get().strip()
            self.cfg["volume"] = self.connect_volume_var.get().strip()
            self.cfg["local_path"] = self.local_path
            save_config(self.cfg)
        except Exception:
            pass

        if self.busy:
            self.cancel_event.set()
            self.status_var.set(self.tr("status_stopping_op"))
            self.connect_btn.configure(state="disabled")
            self.root.after(100, self._wait_and_destroy)
            return
        self._close_client_from_worker()
        self.root.destroy()

    def _wait_and_destroy(self):
        if self.busy:
            self.root.after(100, self._wait_and_destroy)
        else:
            self._close_client_from_worker()
            self.root.destroy()


# ---------------------------------------------------------------------------

def main_gui():
    root = tk.Tk()
    WiiUFileManager(root)
    root.mainloop()


if __name__ == "__main__":
    main_gui()