import sys, os, json, time, logging, re, threading, ctypes, webbrowser, random
from datetime import datetime
from pathlib import Path
from io import BytesIO
from math import ceil
from collections import Counter

# ---------- UAC 提权辅助 ----------
if sys.platform == 'win32':
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except:
        is_admin = False
    if not is_admin:
        if getattr(sys, 'frozen', False):
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, "", None, 1)
        else:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
import requests
import qrcode

# ==================== 翻译 ====================
TRANSLATIONS = {
    'zh': {
        'app_title': 'B站批量取关助手',
        'login': '🔑 扫码登录', 'logout': '🚪 退出',
        'logged_in': '已登录: {}', 'not_logged_in': '未登录',
        'max_pages': '最大处理页数', 'delay': '操作延迟(秒)',
        'fetch_following': '获取关注列表', 'stop': '停止',
        'select_all': '全选', 'deselect_all': '取消全选',
        'unfollow_selected': '取关选中 ({})',
        'refreshing': '正在加载关注列表...', 'unfollowing': '正在取关 {}...',
        'done': '操作完成', 'error': '错误', 'no_login': '请先登录',
        'dark_mode': '🌙 暗色', 'light_mode': '☀️ 亮色',
        'log_view': '查看日志', 'clear_logs': '清理日志',
        'qr_title': 'B站扫码登录', 'qr_waiting': '等待扫码...',
        'qr_scanned': '已扫描，请确认', 'qr_expired': '二维码已过期',
        'lv': 'Lv.{}', 'vip': '大会员', 'follow_time': '关注时间',
        'open_space': '打开空间',
        'total_following': '总关注: {} 人', 'pages_needed': '预计需 {} 页',
        'search_placeholder': '搜索昵称或UID...',
        'search_tip': '💡 空格分隔多关键字',
        'filter_level': '按等级筛选', 'all_levels': '全部', 'unknown_level': '未知',
        'last_dynamic': '最新动态: {}', 'last_video': '最新视频: {}',
        'no_dynamic': '无动态', 'no_video': '无视频',
        'loading_detail': '加载中...',
        'stats_title': '等级分布',
        'confirm_unfollow': '确认要取关 {} 个用户吗？',
        'confirm_yes': '确认', 'confirm_no': '取消',
        'export_csv': '导出CSV',
        'all_levels_filter': '全部等级',
    },
    'en': {
        'app_title': 'Bili Mass Unfollower',
        'login': '🔑 QR Login', 'logout': '🚪 Logout',
        'logged_in': 'Logged in: {}', 'not_logged_in': 'Not logged in',
        'max_pages': 'Max pages', 'delay': 'Delay(sec)',
        'fetch_following': 'Fetch Following', 'stop': 'Stop',
        'select_all': 'Select All', 'deselect_all': 'Deselect All',
        'unfollow_selected': 'Unfollow Selected ({})',
        'refreshing': 'Loading following list...', 'unfollowing': 'Unfollowing {}...',
        'done': 'Done', 'error': 'Error', 'no_login': 'Please login first',
        'dark_mode': '🌙 Dark', 'light_mode': '☀️ Light',
        'log_view': 'View Log', 'clear_logs': 'Clear Logs',
        'qr_title': 'Scan QR Code', 'qr_waiting': 'Waiting...',
        'qr_scanned': 'Scanned, confirm', 'qr_expired': 'QR code expired',
        'lv': 'Lv.{}', 'vip': 'VIP', 'follow_time': 'Follow time',
        'open_space': 'Open Space',
        'total_following': 'Total following: {}', 'pages_needed': 'Approx. {} pages',
        'search_placeholder': 'Search by nickname or UID...',
        'search_tip': '💡 Separate keywords with spaces',
        'filter_level': 'Filter by level', 'all_levels': 'All', 'unknown_level': 'Unknown',
        'last_dynamic': 'Latest dynamic: {}', 'last_video': 'Latest video: {}',
        'no_dynamic': 'No dynamic', 'no_video': 'No video',
        'loading_detail': 'Loading...',
        'stats_title': 'Level Distribution',
        'confirm_unfollow': 'Confirm unfollow {} users?',
        'confirm_yes': 'Yes', 'confirm_no': 'No',
        'export_csv': 'Export CSV',
        'all_levels_filter': 'All Levels',
    }
}

def tr(key, lang='zh'):
    return TRANSLATIONS.get(lang, TRANSLATIONS['zh']).get(key, key)

# ==================== 日志 ====================
CURRENT_LOG_FILE = None
logger = logging.getLogger('BiliUnfollow')
logger.setLevel(logging.DEBUG)

def setup_logging():
    global CURRENT_LOG_FILE
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'unfollow_{timestamp}.log'
    CURRENT_LOG_FILE = log_file
    for h in logger.handlers[:]:
        logger.removeHandler(h)
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    logger.info(f"========== 启动 ==========")
    return log_file

# ==================== 配置 ====================
class Config:
    DEFAULT = {
        "theme": "dark", "lang": "zh",
        "window_size": [1200, 850], "window_pos": [100, 100],
        "sessdata": "", "bili_jct": "",
        "max_pages": 5, "delay": 1.5,
        "splitter_sizes": [500, 200],  # 保存分割条位置
    }
    def __init__(self):
        self.file = Path(__file__).parent / 'unfollow_set.info'
        self.data = self.load()
    def load(self):
        if self.file.exists():
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    for k, v in self.DEFAULT.items():
                        if k not in loaded: loaded[k] = v
                    return loaded
            except: pass
        return self.DEFAULT.copy()
    def save(self):
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    def get(self, key, default=None):
        return self.data.get(key, self.DEFAULT.get(key, default))
    def set(self, key, value):
        self.data[key] = value

# ==================== 主题 ====================
def get_theme_style(theme):
    dark = """
        QMainWindow { background-color: #121212; }
        QWidget { background-color: #121212; color: #e0e0e0; font-size: 14px; }
        QPushButton { background-color: #1f1f1f; border: 1px solid #333; border-radius: 6px; padding: 8px 16px; color: #e0e0e0; font-weight: bold; }
        QPushButton:hover { background-color: #2a2a2a; border-color: #0078d4; }
        QPushButton:pressed { background-color: #0078d4; }
        QPushButton:disabled { background-color: #1a1a1a; color: #666; }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background-color: #1f1f1f; border: 1px solid #333; border-radius: 6px; padding: 6px; color: #e0e0e0; }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView { background-color: #1f1f1f; color: #e0e0e0; selection-background-color: #0078d4; }
        QListWidget { background-color: #1a1a1a; border: 1px solid #333; border-radius: 6px; color: #e0e0e0; }
        QListWidget::item { border-bottom: 1px solid #2a2a2a; }
        QListWidget::item:hover { background-color: #2a2a2a; }
        QGroupBox { border: 1px solid #333; border-radius: 8px; margin-top: 10px; padding-top: 20px; color: #e0e0e0; font-weight: bold; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QCheckBox, QRadioButton { color: #e0e0e0; }
        QProgressBar { border: 1px solid #333; border-radius: 6px; text-align: center; background-color: #1f1f1f; color: #e0e0e0; }
        QProgressBar::chunk { background-color: #0078d4; border-radius: 5px; }
        QTextEdit { background-color: #1a1a1a; border: 1px solid #333; color: #e0e0e0; }
        QLabel#nickLabel { font-size: 18px; font-weight: bold; color: #ffffff; }
        QLabel#levelLabel { font-size: 14px; color: #b0b0b0; }
        QLabel#vipLabel { color: #f5a623; font-weight: bold; font-size: 14px; }
        QLabel#signLabel { font-size: 13px; color: #888; }
        QLabel#dynamicLabel, QLabel#videoLabel { font-size: 12px; color: #777; margin-top: 2px; }
        QLabel#searchTipLabel { font-size: 12px; color: #888; background: transparent; }
        QSplitter::handle { background-color: #333; }
        QLabel#statsLabel { font-size: 13px; color: #aaa; background: transparent; padding: 4px; }
    """
    light = """
        QMainWindow { background-color: #f0f0f0; }
        QWidget { background-color: #f0f0f0; color: #222; font-size: 14px; }
        QPushButton { background-color: #ffffff; border: 1px solid #ccc; border-radius: 6px; padding: 8px 16px; color: #222; font-weight: bold; }
        QPushButton:hover { background-color: #e6e6e6; border-color: #0078d4; }
        QPushButton:pressed { background-color: #0078d4; color: #fff; }
        QPushButton:disabled { background-color: #f5f5f5; color: #999; }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background-color: #ffffff; border: 1px solid #ccc; border-radius: 6px; padding: 6px; color: #222; }
        QComboBox QAbstractItemView { background-color: #ffffff; color: #222; selection-background-color: #0078d4; }
        QListWidget { background-color: #ffffff; border: 1px solid #ccc; border-radius: 6px; color: #222; }
        QListWidget::item { border-bottom: 1px solid #ddd; }
        QListWidget::item:hover { background-color: #f5f5f5; }
        QGroupBox { border: 1px solid #ccc; border-radius: 8px; margin-top: 10px; padding-top: 20px; color: #222; font-weight: bold; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        QCheckBox, QRadioButton { color: #222; }
        QProgressBar { border: 1px solid #ccc; border-radius: 6px; text-align: center; background-color: #ffffff; color: #222; }
        QProgressBar::chunk { background-color: #0078d4; border-radius: 5px; }
        QTextEdit { background-color: #ffffff; border: 1px solid #ccc; color: #222; }
        QLabel#nickLabel { font-size: 18px; font-weight: bold; color: #111; }
        QLabel#levelLabel { font-size: 14px; color: #555; }
        QLabel#vipLabel { color: #f5a623; font-weight: bold; font-size: 14px; }
        QLabel#signLabel { font-size: 13px; color: #555; }
        QLabel#dynamicLabel, QLabel#videoLabel { font-size: 12px; color: #666; margin-top: 2px; }
        QLabel#searchTipLabel { font-size: 12px; color: #666; background: transparent; }
        QSplitter::handle { background-color: #ccc; }
        QLabel#statsLabel { font-size: 13px; color: #555; background: transparent; padding: 4px; }
    """
    return dark if theme == 'dark' else light

# ==================== B站 API ====================
class BiliAPI:
    def __init__(self, sessdata, bili_jct):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://space.bilibili.com/',
        })
        if sessdata:
            self.session.cookies.set('SESSDATA', sessdata, domain='.bilibili.com')
        self.bili_jct = bili_jct
        if sessdata:
            try: self.uid = self._get_my_uid()
            except: self.uid = 0
        else: self.uid = 0

    def _get_my_uid(self):
        resp = self.session.get('https://api.bilibili.com/x/web-interface/nav')
        data = resp.json()
        if data['code'] != 0: raise Exception(f"登录失败: {data['message']}")
        return data['data']['mid']

    def get_following_count(self):
        params = {'vmid': self.uid}
        resp = self.session.get('https://api.bilibili.com/x/relation/stat', params=params)
        data = resp.json()
        if data['code'] != 0: raise Exception(data['message'])
        return data['data']['following']

    def get_followings(self, page=1, page_size=20):
        params = {'vmid': self.uid, 'pn': page, 'ps': page_size, 'order': 'desc'}
        resp = self.session.get('https://api.bilibili.com/x/relation/followings', params=params)
        data = resp.json()
        if data['code'] != 0: raise Exception(data['message'])
        return data['data']['list']

    def get_user_info(self, uid):
        resp = self.session.get(f'https://api.bilibili.com/x/space/acc/info?mid={uid}')
        data = resp.json()
        if data['code'] != 0: raise Exception(data['message'])
        return data['data']

    def get_last_dynamic(self, uid):
        params = {'host_mid': uid, 'offset': ''}
        resp = self.session.get('https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space', params=params)
        data = resp.json()
        if data['code'] == 0 and data['data']['items']:
            timestamp = data['data']['items'][0]['modules']['module_author']['pub_time']
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
        return None

    def get_last_video_time(self, uid):
        params = {'mid': uid, 'ps': 1, 'tid': 0, 'pn': 1, 'order': 'pubdate'}
        resp = self.session.get('https://api.bilibili.com/x/space/arc/search', params=params)
        data = resp.json()
        if data['code'] == 0 and data['data']['list']['vlist']:
            video = data['data']['list']['vlist'][0]
            return datetime.fromtimestamp(video['created']).strftime('%Y-%m-%d %H:%M')
        return None

    def unfollow(self, follow_uid):
        payload = {'fid': follow_uid, 'act': 2, 're_src': 11, 'csrf': self.bili_jct}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        resp = self.session.post('https://api.bilibili.com/x/relation/modify', data=payload, headers=headers)
        data = resp.json()
        if data['code'] != 0: raise Exception(data['message'])
        return True

# ==================== 自定义列表项Widget ====================
class FollowItemWidget(QWidget):
    checked_changed = pyqtSignal(int, bool)

    def __init__(self, uid, uname, face_url, mtime, parent=None):
        super().__init__(parent)
        self.uid = uid; self.uname = uname; self.face_url = face_url; self.mtime = mtime
        self.level = 0; self.vip = False; self.sign = ""
        self.dynamic_str = ""; self.video_str = ""
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(12)

        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(lambda state: self.checked_changed.emit(self.uid, state == Qt.Checked))
        main_layout.addWidget(self.checkbox)

        self.face_label = QLabel()
        self.face_label.setFixedSize(56, 56)
        self.face_label.setScaledContents(True)
        placeholder = self.make_placeholder_pixmap(56)
        self.face_label.setPixmap(placeholder)
        self.load_avatar()
        main_layout.addWidget(self.face_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        info_layout.setContentsMargins(0, 0, 0, 0)

        self.nick_label = QLabel(self.uname)
        self.nick_label.setObjectName("nickLabel")
        self.nick_label.setMaximumWidth(200)

        self.level_label = QLabel("")
        self.level_label.setObjectName("levelLabel")

        self.sign_label = QLabel("")
        self.sign_label.setObjectName("signLabel")
        self.sign_label.setWordWrap(True)
        self.sign_label.setMaximumWidth(280)
        self.sign_label.setMaximumHeight(32)

        self.dynamic_label = QLabel("")
        self.dynamic_label.setObjectName("dynamicLabel")
        self.video_label = QLabel("")
        self.video_label.setObjectName("videoLabel")

        info_layout.addWidget(self.nick_label)
        info_layout.addWidget(self.level_label)
        info_layout.addWidget(self.sign_label)
        info_layout.addWidget(self.dynamic_label)
        info_layout.addWidget(self.video_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        follow_time_str = datetime.fromtimestamp(self.mtime).strftime('%Y-%m-%d %H:%M') if self.mtime else "未知"
        self.follow_time_btn = QPushButton(follow_time_str)
        self.follow_time_btn.setFlat(True)
        self.follow_time_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.follow_time_btn.setStyleSheet("font-size:12px; color:#4ec9b0; text-decoration: underline; border:none; padding:0;")
        self.follow_time_btn.clicked.connect(lambda: QApplication.clipboard().setText(follow_time_str))

        self.open_space_btn = QPushButton(tr('open_space'))
        self.open_space_btn.setFlat(True)
        self.open_space_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.open_space_btn.setStyleSheet("font-size:12px; color:#569cd6; text-decoration: underline; border:none; padding:0;")
        self.open_space_btn.clicked.connect(lambda: webbrowser.open(f'https://space.bilibili.com/{self.uid}'))

        btn_layout.addWidget(self.follow_time_btn)
        btn_layout.addWidget(self.open_space_btn)
        btn_layout.addStretch()
        info_layout.addLayout(btn_layout)

        main_layout.addLayout(info_layout, 1)

        self.vip_label = QLabel("")
        self.vip_label.setObjectName("vipLabel")
        self.vip_label.setFixedWidth(60)
        self.vip_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.vip_label)

        self.setLayout(main_layout)

    def mousePressEvent(self, event):
        if not isinstance(self.childAt(event.pos()), QPushButton):
            self.checkbox.toggle()
        super().mousePressEvent(event)

    def make_placeholder_pixmap(self, size):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#555555"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, size, size, size/5, size/5)
        painter.end()
        return pixmap

    def load_avatar(self):
        manager = QNetworkAccessManager(self)
        manager.finished.connect(self.on_avatar_loaded)
        manager.get(QNetworkRequest(QUrl(self.face_url)))

    def on_avatar_loaded(self, reply):
        pixmap = QPixmap()
        pixmap.loadFromData(reply.readAll())
        if not pixmap.isNull():
            rounded = self.make_rounded_pixmap(pixmap, 56)
            self.face_label.setPixmap(rounded)

    def make_rounded_pixmap(self, pixmap, size):
        target = QPixmap(size, size)
        target.fill(Qt.transparent)
        painter = QPainter(target)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, size, size, size/5, size/5)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, size, size, pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        painter.end()
        return target

    def update_info(self, level, vip_status, sign=""):
        self.level = level
        self.vip = vip_status == 1
        self.sign = sign
        self.level_label.setText(tr('lv').format(level) if level else "")
        self.vip_label.setText(tr('vip') if self.vip else "")
        self.vip_label.setVisible(self.vip)
        self.sign_label.setText(sign if sign else "")

    def update_dynamic_video(self, dynamic_time=None, video_time=None):
        if dynamic_time:
            self.dynamic_label.setText(tr('last_dynamic').format(dynamic_time))
        else:
            self.dynamic_label.setText(tr('no_dynamic'))
        if video_time:
            self.video_label.setText(tr('last_video').format(video_time))
        else:
            self.video_label.setText(tr('no_video'))

# ==================== 线程 ====================
class QRLoginWorker(QThread):
    qr_image = pyqtSignal(QPixmap); status_text = pyqtSignal(str)
    login_success = pyqtSignal(str, str); login_failed = pyqtSignal(str)

    def __init__(self):
        super().__init__(); self._running = True

    def run(self):
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.bilibili.com/'})
        try:
            resp = session.get('https://passport.bilibili.com/x/passport-login/web/qrcode/generate')
            data = resp.json()
            if data['code'] != 0: raise Exception(data.get('message', '未知错误'))
            qr_url, qr_key = data['data']['url'], data['data']['qrcode_key']
            img = qrcode.make(qr_url)
            buf = BytesIO(); img.save(buf, format='PNG')
            pixmap = QPixmap(); pixmap.loadFromData(buf.getvalue())
            self.qr_image.emit(pixmap)
            self.status_text.emit(tr('qr_waiting'))
            while self._running:
                resp = session.get('https://passport.bilibili.com/x/passport-login/web/qrcode/poll', params={'qrcode_key': qr_key})
                poll_data = resp.json()['data']
                code = poll_data['code']
                if code == 0:
                    cookies = session.cookies.get_dict()
                    sessdata = cookies.get('SESSDATA', ''); bili_jct = cookies.get('bili_jct', '')
                    if sessdata and bili_jct: self.login_success.emit(sessdata, bili_jct)
                    else: self.login_failed.emit("未获取到完整 Cookie")
                    break
                elif code == 86038: self.status_text.emit(tr('qr_expired')); self.login_failed.emit('二维码已过期'); break
                elif code == 86090: self.status_text.emit(tr('qr_scanned'))
                else: self.status_text.emit(poll_data.get('message', '未知状态'))
                time.sleep(2)
        except Exception as e: self.login_failed.emit(str(e))

    def stop(self): self._running = False

class FetchFollowingWorker(QThread):
    finished = pyqtSignal(); page_loaded = pyqtSignal(list)
    error = pyqtSignal(str); progress = pyqtSignal(int, int)

    def __init__(self, api, max_pages):
        super().__init__(); self.api = api; self.max_pages = max_pages; self._cancelled = False

    def cancel(self): self._cancelled = True

    def run(self):
        page = 1
        while page <= self.max_pages and not self._cancelled:
            try:
                users = self.api.get_followings(page, 20)
                if not users: break
                user_list = [{'uid': u['mid'], 'uname': u['uname'], 'face': u['face'], 'mtime': u.get('mtime', 0)} for u in users]
                self.page_loaded.emit(user_list)
                self.progress.emit(page, self.max_pages)
                page += 1
            except Exception as e:
                self.error.emit(f"获取第{page}页失败: {e}")
                break
        self.finished.emit()

class UnfollowWorker(QThread):
    finished = pyqtSignal(); error = pyqtSignal(str)
    progress = pyqtSignal(int, int); current_user = pyqtSignal(str)

    def __init__(self, api, users, base_delay):
        super().__init__(); self.api = api; self.users = users; self.base_delay = base_delay; self._cancelled = False

    def cancel(self): self._cancelled = True

    def run(self):
        total = len(self.users)
        for i, user in enumerate(self.users):
            if self._cancelled: break
            self.current_user.emit(user['uname'])
            try:
                self.api.unfollow(user['uid'])
                self.progress.emit(i+1, total)
                delay = self.base_delay + random.uniform(-0.5, 0.5)
                delay = max(0.5, delay)
                time.sleep(delay)
            except Exception as e:
                self.error.emit(f"取关 {user['uname']} 失败: {e}")
        self.finished.emit()

class DetailWorker(QThread):
    detail_ready = pyqtSignal(int, int, int, str)
    dynamic_ready = pyqtSignal(int, str, str)

    def __init__(self, api):
        super().__init__(); self.api = api
        self._uids_queue = []; self._lock = threading.Lock(); self._running = True

    def add_uids(self, uids):
        with self._lock: self._uids_queue.extend(uids)

    def run(self):
        while self._running:
            with self._lock:
                if not self._uids_queue: time.sleep(0.5); continue
                uid = self._uids_queue.pop(0)
            retry = 0
            while retry < 3:
                try:
                    info = self.api.get_user_info(uid)
                    level = info.get('level', 0); vip = info.get('vip', {}).get('status', 0)
                    sign = info.get('sign', '')
                    self.detail_ready.emit(uid, level, vip, sign)
                    break
                except Exception as e:
                    logger.warning(f"获取用户 {uid} 详情失败 (重试 {retry+1}): {e}")
                    time.sleep(5 if '412' in str(e) else 0.8)
                    retry += 1
            try:
                dynamic_time = self.api.get_last_dynamic(uid); time.sleep(0.3)
            except: dynamic_time = None
            try:
                video_time = self.api.get_last_video_time(uid); time.sleep(0.3)
            except: video_time = None
            if dynamic_time or video_time:
                self.dynamic_ready.emit(uid, dynamic_time or "", video_time or "")
            time.sleep(0.8)

    def stop(self): self._running = False

# ==================== 主窗口 ====================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.lang = self.config.get('lang', 'zh')
        self.api = None; self.fetch_worker = None; self.unfollow_worker = None
        self.qr_worker = None; self.detail_worker = None
        self.widget_map = {}; self.selected_uids = set()
        self.filter_level_value = -1
        self.following_users = []
        self.animation = None  # 主题切换动画

        setup_logging()
        self.init_ui()
        self.load_settings()
        saved_sessdata = self.config.get('sessdata', ''); saved_jct = self.config.get('bili_jct', '')
        if saved_sessdata and saved_jct:
            try:
                self.api = BiliAPI(saved_sessdata, saved_jct)
                self.update_login_status()
                self.show_following_count()
            except: pass
        self.detail_worker = DetailWorker(self.api)
        self.detail_worker.detail_ready.connect(self.on_user_detail_ready)
        self.detail_worker.dynamic_ready.connect(self.on_user_dynamic_ready)
        self.detail_worker.start()
        logger.info("主窗口初始化完成")

    def t(self, key): return tr(key, self.lang)

    def init_ui(self):
        self.setWindowTitle(self.t('app_title'))
        self.setMinimumSize(1200, 850)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 10, 15, 10)

        # 登录区域
        login_group = QGroupBox("登录")
        login_layout = QHBoxLayout()
        self.login_btn = QPushButton(self.t('login')); self.logout_btn = QPushButton(self.t('logout'))
        self.login_status = QLabel(self.t('not_logged_in'))
        login_layout.addWidget(self.login_btn); login_layout.addWidget(self.logout_btn); login_layout.addWidget(self.login_status)
        login_layout.addStretch()
        self.theme_btn = QPushButton(); self.lang_btn = QPushButton('EN' if self.lang=='zh' else '中文'); self.lang_btn.setFixedWidth(60)
        login_layout.addWidget(self.lang_btn); login_layout.addWidget(self.theme_btn)
        login_group.setLayout(login_layout)
        main_layout.addWidget(login_group)

        # 设置行 + 搜索 + 统计
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(self.t('max_pages')))
        self.pages_spin = QSpinBox(); self.pages_spin.setRange(1, 70); self.pages_spin.setValue(self.config.get('max_pages', 5))
        top_row.addWidget(self.pages_spin)
        top_row.addWidget(QLabel(self.t('delay')))
        self.delay_spin = QDoubleSpinBox(); self.delay_spin.setRange(0.5, 10.0); self.delay_spin.setSingleStep(0.5)
        self.delay_spin.setValue(self.config.get('delay', 1.5))
        top_row.addWidget(self.delay_spin)
        top_row.addSpacing(20)

        search_layout = QVBoxLayout()
        search_input_layout = QHBoxLayout()
        search_input_layout.addWidget(QLabel("🔍"))
        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText(self.t('search_placeholder'))
        self.search_edit.textChanged.connect(self.apply_filter)
        search_input_layout.addWidget(self.search_edit)
        search_layout.addLayout(search_input_layout)
        self.search_tip_label = QLabel(self.t('search_tip')); self.search_tip_label.setObjectName("searchTipLabel")
        search_layout.addWidget(self.search_tip_label)
        top_row.addLayout(search_layout)

        top_row.addWidget(QLabel(self.t('filter_level')))
        self.level_combo = QComboBox()
        self.level_combo.addItem(self.t('all_levels'), -1)
        self.level_combo.addItem(self.t('unknown_level'), 0)
        for i in range(1, 7): self.level_combo.addItem(f'Lv{i}', i)
        self.level_combo.currentIndexChanged.connect(lambda: self.apply_filter())
        top_row.addWidget(self.level_combo)
        top_row.addStretch()

        self.total_following_label = QLabel(""); self.pages_needed_label = QLabel("")
        top_row.addWidget(self.total_following_label); top_row.addWidget(self.pages_needed_label)
        main_layout.addLayout(top_row)

        # 获取关注按钮
        fetch_layout = QHBoxLayout()
        self.fetch_btn = QPushButton(self.t('fetch_following')); self.stop_fetch_btn = QPushButton(self.t('stop')); self.stop_fetch_btn.setEnabled(False)
        fetch_layout.addWidget(self.fetch_btn); fetch_layout.addWidget(self.stop_fetch_btn); fetch_layout.addStretch()
        main_layout.addLayout(fetch_layout)

        # 分割区域
        self.splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(self.splitter, 1)

        # 关注列表
        list_group = QGroupBox("关注列表")
        list_layout = QVBoxLayout()
        self.follow_list = QListWidget()
        self.follow_list.setSelectionMode(QAbstractItemView.NoSelection)
        self.follow_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        list_layout.addWidget(self.follow_list)
        list_group.setLayout(list_layout)
        self.splitter.addWidget(list_group)

        # 统计面板 + 日志
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        # 统计标签
        self.stats_label = QLabel("")
        self.stats_label.setObjectName("statsLabel")
        bottom_layout.addWidget(self.stats_label)
        # 日志
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True); self.log_text.setMaximumHeight(120)
        bottom_layout.addWidget(self.log_text)
        self.splitter.addWidget(bottom_widget)

        # 恢复分割条位置
        sizes = self.config.get('splitter_sizes', [500, 200])
        self.splitter.setSizes(sizes)

        # 全选/取消与取关按钮
        select_layout = QHBoxLayout()
        self.select_all_btn = QPushButton(self.t('select_all')); self.deselect_all_btn = QPushButton(self.t('deselect_all'))
        self.unfollow_btn = QPushButton(self.t('unfollow_selected').format(0)); self.unfollow_btn.setStyleSheet("background-color: #d9534f; color: white;")
        self.export_csv_btn = QPushButton(self.t('export_csv'))
        select_layout.addWidget(self.select_all_btn); select_layout.addWidget(self.deselect_all_btn)
        select_layout.addWidget(self.export_csv_btn)
        select_layout.addStretch(); select_layout.addWidget(self.unfollow_btn)
        main_layout.addLayout(select_layout)

        # 进度条
        self.progress_bar = QProgressBar(); self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # 底部按钮
        bottom_btn = QHBoxLayout()
        self.log_view_btn = QPushButton(self.t('log_view')); self.clear_logs_btn = QPushButton(self.t('clear_logs'))
        bottom_btn.addWidget(self.log_view_btn); bottom_btn.addWidget(self.clear_logs_btn); bottom_btn.addStretch()
        main_layout.addLayout(bottom_btn)

        # 信号连接
        self.login_btn.clicked.connect(self.start_qr_login); self.logout_btn.clicked.connect(self.do_logout)
        self.fetch_btn.clicked.connect(self.fetch_following); self.stop_fetch_btn.clicked.connect(self.stop_fetch)
        self.unfollow_btn.clicked.connect(self.unfollow_selected)
        self.select_all_btn.clicked.connect(self.select_all); self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.theme_btn.clicked.connect(self.toggle_theme); self.lang_btn.clicked.connect(self.toggle_language)
        self.log_view_btn.clicked.connect(self.show_log_folder); self.clear_logs_btn.clicked.connect(self.clear_logs)

        self.apply_theme(); self.update_theme_button(); self.update_login_status()

    # ---------- 关注总数显示 ----------
    def show_following_count(self):
        if not self.api: return
        try:
            count = self.api.get_following_count()
            pages = ceil(count / 20)
            self.total_following_label.setText(self.t('total_following').format(count))
            self.pages_needed_label.setText(self.t('pages_needed').format(pages))
        except Exception as e:
            logger.warning(f"获取关注总数失败: {e}")

    # ---------- 搜索过滤 ----------
    def apply_filter(self):
        search_text = self.search_edit.text().strip().lower()
        self.filter_level_value = self.level_combo.currentData()
        keywords = [kw for kw in search_text.split(' ') if kw]
        for i in range(self.follow_list.count()):
            item = self.follow_list.item(i); widget = self.follow_list.itemWidget(item)
            if not widget: item.setHidden(True); continue
            match = True
            if keywords:
                match = any(kw in widget.uname.lower() or kw == str(widget.uid) for kw in keywords)
            if match and self.filter_level_value != -1:
                if self.filter_level_value == 0: match = (widget.level == 0)
                else: match = (widget.level == self.filter_level_value)
            item.setHidden(not match)
        self.update_stats()

    # ---------- 统计面板更新 ----------
    def update_stats(self):
        levels = []
        for widget in self.widget_map.values():
            if not widget.isHidden():
                levels.append(widget.level)
        cnt = Counter(levels)
        parts = []
        for lv in sorted(cnt.keys()):
            label = f"Lv{lv}" if lv > 0 else "未知"
            parts.append(f"{label}: {cnt[lv]}")
        self.stats_label.setText(" | ".join(parts) if parts else "")

    # ---------- 复选框管理 ----------
    def on_checkbox_changed(self, uid, checked):
        if checked: self.selected_uids.add(uid)
        else: self.selected_uids.discard(uid)
        self.unfollow_btn.setText(self.t('unfollow_selected').format(len(self.selected_uids)))

    def select_all(self):
        self.selected_uids.clear()
        for widget in self.widget_map.values():
            if not widget.isHidden():
                widget.checkbox.setChecked(True)
                self.selected_uids.add(widget.uid)
        self.unfollow_btn.setText(self.t('unfollow_selected').format(len(self.selected_uids)))

    def deselect_all(self):
        for widget in self.widget_map.values(): widget.checkbox.setChecked(False)
        self.selected_uids.clear()
        self.unfollow_btn.setText(self.t('unfollow_selected').format(0))

    # ---------- 导出CSV ----------
    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出CSV", "", "CSV (*.csv)")
        if not path: return
        with open(path, 'w', encoding='utf-8-sig') as f:
            f.write("UID,昵称,等级,大会员,签名,动态时间,视频时间,关注时间\n")
            for widget in self.widget_map.values():
                f.write(f"{widget.uid},{widget.uname},{widget.level},{widget.vip},{widget.sign},{widget.dynamic_label.text()},{widget.video_label.text()},{widget.follow_time_btn.text()}\n")
        QMessageBox.information(self, "成功", f"已导出到 {path}")

    # ---------- 扫码登录 ----------
    def start_qr_login(self):
        if self.qr_worker and self.qr_worker.isRunning(): return
        dlg = QDialog(self); dlg.setWindowTitle(self.t('qr_title')); dlg.setFixedSize(300, 350)
        layout = QVBoxLayout(dlg)
        qr_label = QLabel(); status_label = QLabel(self.t('qr_waiting'))
        layout.addWidget(qr_label); layout.addWidget(status_label)
        self.qr_worker = QRLoginWorker()
        self.qr_worker.qr_image.connect(lambda pix: qr_label.setPixmap(pix.scaled(250, 250, Qt.KeepAspectRatio)))
        self.qr_worker.status_text.connect(status_label.setText)
        self.qr_worker.login_success.connect(self.on_login_success)
        self.qr_worker.login_failed.connect(lambda msg: QMessageBox.warning(self, "登录失败", msg))
        self.qr_worker.start()
        dlg.finished.connect(lambda: self.qr_worker.stop() if self.qr_worker else None)
        dlg.exec_()

    def on_login_success(self, sessdata, bili_jct):
        self.config.set('sessdata', sessdata); self.config.set('bili_jct', bili_jct); self.config.save()
        self.api = BiliAPI(sessdata, bili_jct); self.detail_worker.api = self.api
        self.update_login_status(); self.show_following_count()
        QMessageBox.information(self, "登录成功", f"已登录，UID: {self.api.uid}")
        self.log_text.append(f"扫码登录成功，UID: {self.api.uid}")

    def do_logout(self):
        self.api = None; self.config.set('sessdata', ''); self.config.set('bili_jct', ''); self.config.save()
        self.following_users.clear(); self.follow_list.clear(); self.widget_map.clear(); self.selected_uids.clear()
        self.update_login_status(); self.total_following_label.setText(""); self.pages_needed_label.setText("")
        self.log_text.append("已退出登录")

    def update_login_status(self):
        if self.api and self.api.uid:
            try:
                resp = self.api.session.get('https://api.bilibili.com/x/space/acc/info?mid=' + str(self.api.uid))
                uname = resp.json()['data']['name']
                self.login_status.setText(self.t('logged_in').format(uname))
            except: self.login_status.setText(self.t('logged_in').format(self.api.uid))
            self.login_btn.setEnabled(False); self.logout_btn.setEnabled(True)
        else:
            self.login_status.setText(self.t('not_logged_in')); self.login_btn.setEnabled(True); self.logout_btn.setEnabled(False)

    # ---------- 获取关注列表 ----------
    def fetch_following(self):
        if not self.api: QMessageBox.warning(self, self.t('error'), self.t('no_login')); return
        max_pages = self.pages_spin.value(); self.config.set('max_pages', max_pages); self.config.set('delay', self.delay_spin.value()); self.config.save()
        self.fetch_btn.setEnabled(False); self.stop_fetch_btn.setEnabled(True)
        self.progress_bar.setVisible(True); self.progress_bar.setMaximum(max_pages); self.progress_bar.setValue(0)
        self.follow_list.clear(); self.following_users.clear(); self.widget_map.clear(); self.selected_uids.clear()
        self.unfollow_btn.setText(self.t('unfollow_selected').format(0))
        self.log_text.append(f"开始获取关注列表，最多 {max_pages} 页..."); self.show_following_count()
        if self.fetch_worker and self.fetch_worker.isRunning(): self.fetch_worker.cancel()
        self.fetch_worker = FetchFollowingWorker(self.api, max_pages)
        self.fetch_worker.page_loaded.connect(self.on_page_loaded)
        self.fetch_worker.progress.connect(lambda cur, total: self.progress_bar.setValue(cur))
        self.fetch_worker.finished.connect(self.on_fetch_finished)
        self.fetch_worker.error.connect(lambda e: QMessageBox.critical(self, self.t('error'), e))
        self.fetch_worker.start()

    def stop_fetch(self):
        if self.fetch_worker: self.fetch_worker.cancel(); self.fetch_worker = None; self.reset_fetch_ui()

    def on_page_loaded(self, users):
        uids = []
        for u in users:
            item = QListWidgetItem(); item.setSizeHint(QSize(0, 130))
            widget = FollowItemWidget(u['uid'], u['uname'], u['face'], u['mtime'])
            widget.checked_changed.connect(self.on_checkbox_changed)
            self.widget_map[u['uid']] = widget
            self.follow_list.addItem(item); self.follow_list.setItemWidget(item, widget)
            self.following_users.append(u); uids.append(u['uid'])
        if self.detail_worker: self.detail_worker.add_uids(uids)
        self.apply_filter()

    def on_fetch_finished(self):
        self.reset_fetch_ui(); self.log_text.append(f"所有页面加载完毕，共 {self.follow_list.count()} 个关注用户")
        self.update_stats()

    def on_user_detail_ready(self, uid, level, vip_status, sign):
        widget = self.widget_map.get(uid)
        if widget:
            widget.update_info(level, vip_status, sign)
            self.apply_filter()

    def on_user_dynamic_ready(self, uid, dynamic_time, video_time):
        widget = self.widget_map.get(uid)
        if widget: widget.update_dynamic_video(dynamic_time, video_time)

    def reset_fetch_ui(self):
        self.fetch_btn.setEnabled(True); self.stop_fetch_btn.setEnabled(False); self.progress_bar.setVisible(False)

    # ---------- 取关（含确认） ----------
    def unfollow_selected(self):
        if not self.api: QMessageBox.warning(self, self.t('error'), self.t('no_login')); return
        if not self.selected_uids: QMessageBox.warning(self, self.t('error'), "请选择要取关的用户"); return
        count = len(self.selected_uids)
        reply = QMessageBox.question(self, "确认", self.t('confirm_unfollow').format(count), QMessageBox.Yes|QMessageBox.No)
        if reply != QMessageBox.Yes: return
        users = [{'uid': uid, 'uname': self.widget_map[uid].uname} for uid in self.selected_uids.copy()]
        delay = self.delay_spin.value()
        self.unfollow_btn.setEnabled(False); self.progress_bar.setVisible(True); self.progress_bar.setMaximum(len(users))
        self.log_text.append(f"开始取关 {len(users)} 个用户...")
        self.unfollow_worker = UnfollowWorker(self.api, users, delay)
        self.unfollow_worker.current_user.connect(lambda name: self.log_text.append(tr('unfollowing').format(name)))
        self.unfollow_worker.progress.connect(lambda cur, total: self.progress_bar.setValue(cur))
        self.unfollow_worker.finished.connect(self.on_unfollow_finished)
        self.unfollow_worker.error.connect(lambda e: self.log_text.append(f"错误: {e}"))
        self.unfollow_worker.start()

    def on_unfollow_finished(self):
        self.unfollow_btn.setEnabled(True); self.progress_bar.setVisible(False); self.log_text.append("取关操作完成")
        self.fetch_following()

    # ---------- 主题切换动画 ----------
    def toggle_theme(self):
        new = 'light' if self.config.get('theme') == 'dark' else 'dark'
        self.config.set('theme', new)
        # 简单动画：先设置中间色，再立即应用目标主题（模拟闪烁过渡）
        mid_style = get_theme_style('dark' if new == 'light' else 'light')
        self.setStyleSheet(mid_style)
        QTimer.singleShot(80, lambda: self.setStyleSheet(get_theme_style(new)))
        self.update_theme_button()

    def apply_theme(self):
        theme = self.config.get('theme', 'dark')
        self.setStyleSheet(get_theme_style(theme))
        self.update_theme_button()

    def update_theme_button(self):
        theme = self.config.get('theme', 'dark')
        self.theme_btn.setText(self.t('dark_mode') if theme == 'light' else self.t('light_mode'))

    # ---------- 语言切换完整修复 ----------
    def toggle_language(self):
        self.lang = 'en' if self.lang == 'zh' else 'zh'
        self.config.set('lang', self.lang); self.lang_btn.setText('EN' if self.lang == 'zh' else '中文')
        self.setWindowTitle(self.t('app_title'))
        # 更新所有按钮和标签
        self.login_btn.setText(self.t('login')); self.logout_btn.setText(self.t('logout'))
        self.fetch_btn.setText(self.t('fetch_following')); self.stop_fetch_btn.setText(self.t('stop'))
        self.select_all_btn.setText(self.t('select_all')); self.deselect_all_btn.setText(self.t('deselect_all'))
        self.unfollow_btn.setText(self.t('unfollow_selected').format(len(self.selected_uids)))
        self.log_view_btn.setText(self.t('log_view')); self.clear_logs_btn.setText(self.t('clear_logs'))
        self.export_csv_btn.setText(self.t('export_csv'))
        self.search_edit.setPlaceholderText(self.t('search_placeholder'))
        self.search_tip_label.setText(self.t('search_tip'))
        self.level_combo.setItemText(0, self.t('all_levels')); self.level_combo.setItemText(1, self.t('unknown_level'))
        # 更新各follow item中的按钮文本
        for widget in self.widget_map.values():
            widget.open_space_btn.setText(self.t('open_space'))

    def show_log_folder(self):
        log_dir = Path(__file__).parent / 'logs'
        if log_dir.exists(): os.startfile(str(log_dir))

    def clear_logs(self): self.log_text.clear()

    def load_settings(self):
        self.apply_theme()
        s = self.config.get('window_size', [1200, 850]); p = self.config.get('window_pos', [100, 100])
        self.resize(s[0], s[1]); self.move(p[0], p[1])

    def closeEvent(self, e):
        self.config.set('window_size', [self.width(), self.height()]); self.config.set('window_pos', [self.x(), self.y()])
        self.config.set('splitter_sizes', self.splitter.sizes()); self.config.save()
        if self.detail_worker: self.detail_worker.stop()
        e.accept()

def main():
    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(True)
    w = MainWindow(); w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
    #绝大部分都是ai实现的代码,逻辑什么的就不要强求了,美观也是,能用就行
    #哔哩哔哩的接口实现是从别人的文档找到的
    #封号不负责,虽然没有恶意代码但我感觉这么频繁的请求会出事