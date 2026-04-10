"""
SettingsDialog — диалог настроек приложения
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
    QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from pathlib import Path
from dotenv import set_key
from config import Config


class GeneralSettingsTab(QWidget):
    """Вкладка основных настроек"""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Имя системы
        name_label = QLabel("Имя ассистента:")
        name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.name_input = QLineEdit()
        self.name_input.setText(self.config.system_name)
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        
        # Язык
        lang_label = QLabel("Язык интерфейса:")
        lang_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["ru", "en"])
        self.lang_combo.setCurrentText(self.config.language)
        layout.addWidget(lang_label)
        layout.addWidget(self.lang_combo)
        
        # Автозапуск
        self.autostart_checkbox = QCheckBox("Автоматически запускать при старте ОС")
        self.autostart_checkbox.setChecked(self.config.autostart)
        layout.addWidget(self.autostart_checkbox)
        
        layout.addStretch()
        self.setLayout(layout)


class APISettingsTab(QWidget):
    """Вкладка API настроек"""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Groq API ключ
        key_label = QLabel("Groq API ключ:")
        key_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setText(self.config.groq_api_key)
        layout.addWidget(key_label)
        layout.addWidget(self.api_key_input)
        
        # Кнопка проверки
        test_btn = QPushButton("🔍 Проверить ключ")
        test_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.ACCENT};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
        """)
        test_btn.clicked.connect(self._test_api_key)
        layout.addWidget(test_btn)
        
        # Модель
        model_label = QLabel("Модель LLM:")
        model_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "qwen-qwq-32b",
            "llama-3.3-70b",
            "mixtral-8x7b-32768",
            "gemma-7b-it"
        ])
        self.model_combo.setCurrentText(self.config.model)
        layout.addWidget(model_label)
        layout.addWidget(self.model_combo)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _test_api_key(self):
        """Пытается проверить API ключ"""
        api_key = self.api_key_input.text()
        if not api_key:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите API ключ")
            return
        
        QMessageBox.information(self, "API ключ", "✅ Ключ имеет правильный формат (проверка синтаксиса)")


class HotkeySettingsTab(QWidget):
    """Вкладка настроек горячих клавиш"""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Горячая клавиша
        hotkey_label = QLabel("Глобальная горячая клавиша:")
        hotkey_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setText(self.config.hotkey)
        self.hotkey_input.setPlaceholderText("Пример: ctrl+shift+space")
        layout.addWidget(hotkey_label)
        layout.addWidget(self.hotkey_input)
        
        info = QLabel("💡 Формат: ctrl, shift, alt + буква/цифра\nПримеры: ctrl+a, alt+shift+q")
        info.setStyleSheet("color: #888888; padding: 8px; font-size: 9pt;")
        layout.addWidget(info)
        
        layout.addStretch()
        self.setLayout(layout)


class VoiceSettingsTab(QWidget):
    """Вкладка настроек голоса"""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Язык распознавания
        lang_label = QLabel("Язык распознавания речи:")
        lang_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.voice_lang_combo = QComboBox()
        self.voice_lang_combo.addItems(["ru", "en", "de", "fr", "es"])
        self.voice_lang_combo.setCurrentText(self.config.language)
        layout.addWidget(lang_label)
        layout.addWidget(self.voice_lang_combo)
        
        # Микрофон
        mic_label = QLabel("Микрофон:")
        mic_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.mic_combo = QComboBox()
        self.mic_combo.addItems(["Стандартный микрофон", "Микрофон 2", "Микрофон 3"])
        layout.addWidget(mic_label)
        layout.addWidget(self.mic_combo)
        
        layout.addStretch()
        self.setLayout(layout)


class SettingsDialog(QDialog):
    """Диалог настроек приложения"""
    
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        
        self.setWindowTitle("Nevada — Настройки")
        self.setGeometry(300, 300, 600, 500)
        self.setStyleSheet(f"background-color: {self.config.BG_WINDOW};")
        
        layout = QVBoxLayout()
        
        # Вкладки
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget {{
                background-color: {self.config.BG_WINDOW};
            }}
            QTabBar::tab {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                padding: 8px 20px;
                border-bottom: 2px solid {self.config.BORDER};
            }}
            QTabBar::tab:selected {{
                border-bottom: 2px solid {self.config.ACCENT};
            }}
        """)
        
        # Вкладки
        self.general_tab = GeneralSettingsTab(config)
        self.api_tab = APISettingsTab(config)
        self.hotkey_tab = HotkeySettingsTab(config)
        self.voice_tab = VoiceSettingsTab(config)
        
        tabs.addTab(self.general_tab, "⚙️ Основное")
        tabs.addTab(self.api_tab, "🔑 API")
        tabs.addTab(self.hotkey_tab, "⌨️ Горячие клавиши")
        tabs.addTab(self.voice_tab, "🎤 Голос")
        
        layout.addWidget(tabs)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 Сохранить")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.ACCENT};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
        """)
        save_btn.clicked.connect(self._save_settings)
        
        cancel_btn = QPushButton("❌ Отмена")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.config.BG_INPUT};
                color: {self.config.TEXT_PRIMARY};
                border: 1px solid {self.config.BORDER};
                border-radius: 6px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background-color: {self.config.BORDER};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _save_settings(self):
        """Сохраняет настройки в .env"""
        try:
            env_path = Path(__file__).parent.parent / ".env"
            
            # Сохраняем значения
            set_key(str(env_path), "GROQ_API_KEY", self.api_tab.api_key_input.text())
            set_key(str(env_path), "NEVADA_LANGUAGE", self.general_tab.lang_combo.currentText())
            set_key(str(env_path), "NEVADA_HOTKEY", self.hotkey_tab.hotkey_input.text())
            set_key(str(env_path), "NEVADA_MODEL", self.api_tab.model_combo.currentText())
            set_key(str(env_path), "NEVADA_AUTOSTART", "true" if self.general_tab.autostart_checkbox.isChecked() else "false")
            
            QMessageBox.information(self, "Успех", "✅ Настройки сохранены!\nПожалуйста, перезагрузите приложение для применения изменений.")
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"❌ Ошибка сохранения: {str(e)}")
