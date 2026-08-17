"""
Splash Screen — экран загрузки с индикатором прогресса
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor


class SplashScreen(QWidget):
    """Экран загрузки с индикатором прогресса"""
    
    def __init__(self):
        super().__init__()
        self.config = None
        self._setup_ui()
        
    def _setup_ui(self):
        """Инициализирует UI"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        # Размер
        self.setFixedSize(400, 300)
        
        # Стиль в духе TeacherSupport: светлая карточка с бирюзовым акцентом
        self.setStyleSheet("""
            SplashScreen {
                background-color: #fffdfa;
                border: 1px solid #ded8cd;
                border-radius: 24px;
            }
            QLabel { background: transparent; }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Название приложения
        title = QLabel("Nevada")
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title.setStyleSheet("color: #0f172a;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Статус
        self.status_label = QLabel("Инициализация...")
        self.status_label.setFont(QFont("Segoe UI", 11))
        self.status_label.setStyleSheet("color: #66605a;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #efeae1;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #0f766e;
                border-radius: 4px;
            }
        """)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Подробно
        self.detail_label = QLabel("")
        self.detail_label.setFont(QFont("Segoe UI", 9))
        self.detail_label.setStyleSheet("color: #8a8174;")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.detail_label)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Центрируем на экране
        self._center_on_screen()
    
    def _center_on_screen(self):
        """Центрирует окно на экране"""
        from PyQt6.QtGui import QGuiApplication
        screen_geometry = QGuiApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
    
    def update_progress(self, step: int, message: str, detail: str = ""):
        """
        Обновляет прогресс
        
        Args:
            step: Процент (0-100)
            message: Основное сообщение
            detail: Детальное сообщение (опционально)
        """
        self.progress_bar.setValue(step)
        self.status_label.setText(message)
        if detail:
            self.detail_label.setText(detail)
        
        # Обновляем UI
        from PyQt6.QtCore import QCoreApplication
        QCoreApplication.processEvents()
    
    def show_and_center(self):
        """Показывает splash и центрирует его"""
        self._center_on_screen()
        self.show()
        from PyQt6.QtCore import QCoreApplication
        QCoreApplication.processEvents()
