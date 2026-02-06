#!/usr/bin/env python3
"""
Programmer's Calculator - A polished calculator with decimal/hex conversion
Updated with JSON config, pending op display, smart ESC, and Memory functions.
Enhanced with 3D buttons, gradient background, button animations, and LCD display.
"""

import sys
import json
import time
import ctypes
import base64
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QLabel, QDialog, QDialogButtonBox,
    QCheckBox, QFontDialog, QScrollArea, QFrame, QMessageBox,
    QGraphicsColorizeEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QByteArray, pyqtSignal, QPropertyAnimation, QSequentialAnimationGroup, QPauseAnimation
from PyQt6.QtGui import QFont, QKeyEvent, QAction, QIcon, QPixmap, QColor, QPalette, QLinearGradient
import qdarktheme
from icon import ICON_PNG_BASE64

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
    "proggercalc.proggercalc"
)

# Global constants for UI customization
BUTTON_MIN_WIDTH = 30  # Minimum button width
BUTTON_MIN_HEIGHT = 25  # Minimum button height
GRADIENT_INTENSITY = 0.65  # Gradient intensity multiplier (0.0 to 2.0, where 1.0 is default)
BUTTON_HISTORY_RATIO = 0.385  # Ratio of width for buttons vs history (0.0 to 1.0, where 0.5 is equal split)
WINDOW_MARGINS = 5  # Margin between window border and contents (in pixels)
LAYOUT_SPACING = 4  # Spacing between widgets and layouts (in pixels)

def icon_from_base64_png(b64: str) -> QIcon:
    raw = base64.b64decode(b64)
    ba = QByteArray(raw)

    pixmap = QPixmap()
    pixmap.loadFromData(ba, "PNG")

    return QIcon(pixmap)

def get_app_path():
    """Resolve the correct path for both script and frozen (PyInstaller) execution."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


def adjust_gradient_color(color_hex, intensity):
    """Adjust a hex color based on gradient intensity"""
    color = QColor(color_hex)
    h, s, v, a = color.getHsv()
    
    # Adjust value (brightness) based on intensity
    # intensity < 1.0 makes gradients flatter
    # intensity > 1.0 makes gradients more pronounced
    if intensity < 1.0:
        # Move toward middle value (128)
        v = int(v + (128 - v) * (1.0 - intensity))
    else:
        # Enhance the existing value
        if v > 128:
            v = min(255, int(v + (255 - v) * (intensity - 1.0) * 0.5))
        else:
            v = max(0, int(v - v * (intensity - 1.0) * 0.5))
    
    adjusted = QColor()
    adjusted.setHsv(h, s, v, a)
    return adjusted.name()


class ClickableLabel(QLabel):
    """A QLabel that emits a signal when clicked"""
    clicked = pyqtSignal(str)
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        # Keep your existing styling here...
        self.setStyleSheet("padding: 4px; background-color: #101010; border-radius: 3px;")
        
        # Setup the color effect for flashing
        self.effect = QGraphicsColorizeEffect(self)
        self.setGraphicsEffect(self.effect)
        self.effect.setStrength(0) # Invisible by default

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.text())
        super().mousePressEvent(event)
        self.flash()
        
    def flash(self):
        # Set the flash color (Green for success/copy)
        self.effect.setColor(QColor("#4CAF50")) 
        
        # Create the "Fade In" animation
        self.anim_in = QPropertyAnimation(self.effect, b"strength")
        self.anim_in.setDuration(50)
        self.anim_in.setStartValue(0)
        self.anim_in.setEndValue(0.8)

        # Create the "Fade Out" animation
        self.anim_out = QPropertyAnimation(self.effect, b"strength")
        self.anim_out.setDuration(500)
        self.anim_out.setStartValue(0.8)
        self.anim_out.setEndValue(0)

        # Sequence: Flash on quickly, pause for a split second, then fade out
        self.group = QSequentialAnimationGroup()
        self.group.addAnimation(self.anim_in)
        self.group.addPause(100)
        self.group.addAnimation(self.anim_out)
        self.group.start()


class AnimatedButton(QPushButton):
    """A QPushButton with a color flash animation when pressed"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Setup the color effect for flashing
        self.effect = QGraphicsColorizeEffect(self)
        self.setGraphicsEffect(self.effect)
        self.effect.setStrength(0)
    
    def flash(self):
        """Flash the button with a light gray color"""
        self.effect.setColor(QColor("#CCCCCC"))  # Light gray
        
        # Create the "Fade In" animation
        self.anim_in = QPropertyAnimation(self.effect, b"strength")
        self.anim_in.setDuration(50)
        self.anim_in.setStartValue(0)
        self.anim_in.setEndValue(0.6)

        # Create the "Fade Out" animation
        self.anim_out = QPropertyAnimation(self.effect, b"strength")
        self.anim_out.setDuration(300)
        self.anim_out.setStartValue(0.6)
        self.anim_out.setEndValue(0)

        # Sequence: Flash on quickly, then fade out
        self.group = QSequentialAnimationGroup()
        self.group.addAnimation(self.anim_in)
        self.group.addAnimation(self.anim_out)
        self.group.start()
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.flash()


class SettingsDialog(QDialog):
    """Settings dialog for calculator preferences"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(275, 150)
        
        layout = QVBoxLayout()
        
        # Hex prefix option
        self.hex_prefix_check = QCheckBox("Show '0x' prefix for hex numbers")
        self.hex_prefix_check.setChecked(parent.config.get("hex_prefix", True))
        layout.addWidget(self.hex_prefix_check)
        
        # Binary prefix option
        self.bin_prefix_check = QCheckBox("Show '0b' prefix for binary numbers")
        self.bin_prefix_check.setChecked(parent.config.get("bin_prefix", True))
        layout.addWidget(self.bin_prefix_check)

        # Commas option
        self.commas_check = QCheckBox("Show thousands separator (e.g. 1,000)")
        self.commas_check.setChecked(parent.config.get("show_commas", False))
        layout.addWidget(self.commas_check)
        
        # Font selection
        font_layout = QHBoxLayout()
        font_label = QLabel("Display Font:")
        self.font_button = QPushButton("Choose Font...")
        self.font_button.clicked.connect(self.choose_font)
        font_layout.addWidget(font_label)
        font_layout.addWidget(self.font_button)
        font_layout.addStretch()
        layout.addLayout(font_layout)
        
        hist_font_layout = QHBoxLayout()
        hist_font_label = QLabel("History Font:")
        self.hist_font_button = QPushButton("Choose History Font...")
        self.hist_font_button.clicked.connect(self.choose_history_font)
        hist_font_layout.addWidget(hist_font_label)
        hist_font_layout.addWidget(self.hist_font_button)
        hist_font_layout.addStretch()
        layout.addLayout(hist_font_layout)
        
        layout.addStretch()
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        self.selected_font = None
        self.selected_hist_font = None
    
    def choose_font(self):
        """Open font dialog"""
        current_font = self.parent().display.font()
        font, ok = QFontDialog.getFont(current_font, self)
        if ok:
            self.selected_font = font
            
    def choose_history_font(self):
        """Open font dialog for History"""
        # Get current history font from parent's config or panel
        current = self.parent().history_panel.current_font
        font, ok = QFontDialog.getFont(current, self)
        if ok:
            self.selected_hist_font = font


class HistoryPanel(QFrame):
    """History panel showing previous calculations"""
    
    entry_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        # Remove fixed width constraints - now controlled by layout stretch
        
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Title
        title = QLabel("History")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Scroll area for history items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.history_widget = QWidget()
        self.history_layout = QVBoxLayout()
        self.history_layout.setSpacing(4)
        self.history_layout.addStretch()
        self.history_widget.setLayout(self.history_layout)
        
        scroll.setWidget(self.history_widget)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        self.history_items = []
        self.current_font = QFont("Consolas", 9)
    
    def add_entry(self, text):
        """Add a history entry"""
        label = ClickableLabel(text) 
        label.clicked.connect(self.entry_clicked.emit) # Connect to panel signal

        label.setWordWrap(True)
        label.setStyleSheet("""
            QLabel { 
                padding: 4px; 
                background-color: #101010; 
                border-radius: 3px; 
            }
            QLabel:hover { 
                background-color: #2a2a2a; 
            }
        """)
        
        # Apply the current configured font
        label.setFont(self.current_font)
        
        # Insert at the top (before stretch)
        self.history_layout.insertWidget(0, label)
        self.history_items.insert(0, label)
        
        # Keep only last 50 items
        if len(self.history_items) > 50:
            old_label = self.history_items.pop()
            self.history_layout.removeWidget(old_label)
            old_label.deleteLater()
            
    def set_history_font(self, font: QFont):
        """Update font for all existing and future items"""
        self.current_font = font
        for label in self.history_items:
            label.setFont(font)
    
    def clear_history(self):
        """Clear all history"""
        for label in self.history_items:
            self.history_layout.removeWidget(label)
            label.deleteLater()
        self.history_items.clear()


class ProgrammerCalculator(QMainWindow):
    """Main calculator window"""
    
    def __init__(self):
        super().__init__()
        
        # Default config
        self.config = {
            "hex_prefix": True,
            "bin_prefix": True,
            "show_commas": False,
            "display_font": None,
            "hex_mode": False
        }
        self.config_file = get_app_path() / "config.json"

        # Calculator state
        self.current_value = 0
        self.stored_value = 0
        self.operation = None
        
        self.memory_value = 0
        
        self.clear_press_count = 0
        self.last_clear_time = 0
        
        # Repeat operation state
        self.last_operation = None
        self.last_operand = None
        self.shift_btn: AnimatedButton = None
        
        self.hex_mode = False  # False = decimal, True = hex
        self.new_number = True
        self.load_settings()

        self.init_ui()
        
        self.load_settings()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("ProggerCalc")
        
        # Central widget and main layout
        central = QWidget()
        self.setCentralWidget(central)
        
        # Set gradient background on central widget
        central.setAutoFillBackground(True)
        palette = central.palette()
        gradient = QLinearGradient(0, 0, 0, 600)
        gradient.setColorAt(0.0, QColor("#1a1a2e"))
        gradient.setColorAt(1.0, QColor("#0f0f1e"))
        palette.setBrush(QPalette.ColorRole.Window, gradient)
        central.setPalette(palette)
        
        # Main vertical layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(LAYOUT_SPACING)
        main_layout.setContentsMargins(WINDOW_MARGINS, WINDOW_MARGINS, WINDOW_MARGINS, WINDOW_MARGINS)
        
        # Display area (full width at top)
        self.display_frame = QFrame()
        self.display_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        
        # LCD-style background with subtle grid pattern
        self.display_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a3a1a, stop:0.5 #132813, stop:1 #0d1f0d);
                border: 2px solid #0a0a0a;
                border-radius: 8px;
            }
        """)
        
        self.display_layout = QVBoxLayout()
        self.display_layout.setContentsMargins(5, 5, 5, 5)
        
        # Top info row (Mode + Pending Op)
        info_layout = QHBoxLayout()
        
        # Mode indicator
        self.mode_label = QLabel("DEC")
        mode_font = QFont()
        mode_font.setBold(True)
        mode_font.setPointSize(9)
        self.mode_label.setFont(mode_font)
        self.mode_label.setStyleSheet("color: #00ff00; background: transparent; border: 0px solid #0a0a0a;")
        info_layout.addWidget(self.mode_label)
        
        info_layout.addStretch()
        
        # Pending Operation Indicator
        self.op_label = QLabel("")
        op_font = QFont("Tahoma", 14)
        op_font.setBold(True)
        self.op_label.setFont(op_font)
        self.op_label.setStyleSheet("color: #ffaa00; background: transparent; border: 0px solid #0a0a0a;")
        self.op_label.setMaximumHeight(22)
        self.op_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        info_layout.addWidget(self.op_label)
        
        self.display_layout.addLayout(info_layout)
        
        self.display_effect = None
        
        # Main display with LCD-style text
        self.display = QLabel("0")
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        display_font = QFont("Consolas", 24)
        display_font.setWeight(QFont.Weight.Bold)
        self.display.setFont(display_font)
        self.display.setMinimumHeight(60)
        # LCD green glow effect
        self.display.setStyleSheet("""
            QLabel {
                color: #00ff00;
                background: transparent;
                text-shadow: 0 0 10px #00ff00;
            }
        """)
        self.display_layout.addWidget(self.display)
        
        # Alternative representations with LCD styling
        self.alt_display = QLabel("HEX: 0x0  BIN: 0b0")
        alt_font = QFont("Consolas", 9)
        self.alt_display.setFont(alt_font)
        self.alt_display.setStyleSheet("""
            QLabel {
                padding: 1px; 
                background: rgba(0, 40, 0, 100);
                color: #66ff66;
                border-radius: 3px;
                border: 1px groove #0a0a0a;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #274027, stop:0.5 #264026, stop:1 #2d4f2d);
            }
        """)
        self.alt_display.setMaximumHeight(20)
        self.display_layout.addWidget(self.alt_display)
        
        self.display_frame.setLayout(self.display_layout)
        main_layout.addWidget(self.display_frame)
        
        # Horizontal layout for buttons and history (side by side)
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(LAYOUT_SPACING)
        
        # Left side - calculator buttons
        self.calc_layout = QVBoxLayout()
        self.calc_layout.setSpacing(LAYOUT_SPACING)
        self.calc_layout.setContentsMargins(0, 0, 0, 0)
        
        # Button grid
        button_layout = QGridLayout()
        button_layout.setSpacing(4)
        
        # 3D Button styling with adjustable gradient intensity
        button_3d_style = f"""
            QPushButton {{
                border: 1px solid #00000066;
                border-radius: 5px;
                font-size: 12pt;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {adjust_gradient_color('#4a4a4a', GRADIENT_INTENSITY)}, 
                    stop:0.5 {adjust_gradient_color('#3a3a3a', GRADIENT_INTENSITY)}, 
                    stop:1 {adjust_gradient_color('#2a2a2a', GRADIENT_INTENSITY)});
                color: #ffffff;
                padding: 2px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {adjust_gradient_color('#5a5a5a', GRADIENT_INTENSITY)}, 
                    stop:0.5 {adjust_gradient_color('#4a4a4a', GRADIENT_INTENSITY)}, 
                    stop:1 {adjust_gradient_color('#3a3a3a', GRADIENT_INTENSITY)});
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {adjust_gradient_color('#2a2a2a', GRADIENT_INTENSITY)}, 
                    stop:0.5 {adjust_gradient_color('#3a3a3a', GRADIENT_INTENSITY)}, 
                    stop:1 {adjust_gradient_color('#4a4a4a', GRADIENT_INTENSITY)});
                border: 1px solid #666666;
            }}
            QPushButton:disabled {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {adjust_gradient_color('#333333', GRADIENT_INTENSITY)}, 
                    stop:0.5 {adjust_gradient_color('#282828', GRADIENT_INTENSITY)}, 
                    stop:1 {adjust_gradient_color('#1e1e1e', GRADIENT_INTENSITY)});
                color: #666666;
            }}
        """
        
        # Button definitions (text, row, col, operation/value)
        buttons = [
            # Row 0 - Memory
            ("MS", 0, 0, "mem_store"), ("MR", 0, 1, "mem_recall"), ("M+", 0, 2, "mem_add"), ("M-", 0, 3, "mem_sub"),
            # Row 1
            ("C", 1, 0, "clear"), ("CE", 1, 1, "clear_entry"), ("%", 1, 2, "mod"), ("/", 1, 3, "div"),
            # Row 2
            ("7", 2, 0, 7), ("8", 2, 1, 8), ("9", 2, 2, 9), ("*", 2, 3, "mul"),
            # Row 3
            ("4", 3, 0, 4), ("5", 3, 1, 5), ("6", 3, 2, 6), ("-", 3, 3, "sub"),
            # Row 4
            ("1", 4, 0, 1), ("2", 4, 1, 2), ("3", 4, 2, 3), ("+", 4, 3, "add"),
            # Row 5
            ("0", 5, 0, 0), ("AND", 5, 1, "and"), ("OR", 5, 2, "or"), ("=", 5, 3, "equals"),
            # Row 6 - Hex digits
            ("A", 6, 0, "A"), ("B", 6, 1, "B"), ("C", 6, 2, "C"), ("D", 6, 3, "D"),
            # Row 7
            ("E", 7, 0, "E"), ("F", 7, 1, "F"), ("XOR", 7, 2, "xor"), ("<<", 7, 3, "lshift"),
        ]
        
        self.buttons = {}
        self.button_map = {}  # Map actions to buttons for keyboard flash
        
        for text, row, col, action in buttons:
            btn = AnimatedButton(text)
            btn.setMinimumSize(BUTTON_MIN_WIDTH, BUTTON_MIN_HEIGHT)
            btn.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding
            )
            btn.setStyleSheet(button_3d_style)
            
            if text == "<<":
                self.shift_btn = btn  # Save reference for later
            
            if isinstance(action, int):
                btn.clicked.connect(lambda checked, a=action: self.number_pressed(a))
                self.button_map[str(action)] = btn
            elif action in ["A", "B", "C", "D", "E", "F"]:
                btn.clicked.connect(lambda checked, a=action: self.hex_digit_pressed(a))
                self.buttons[action] = btn
                self.button_map[action] = btn
            elif action in ["add", "sub", "mul", "div", "mod", "and", "or", "xor", "lshift"]:
                btn.clicked.connect(lambda checked, a=action: self.operation_pressed(a))
                self.button_map[action] = btn
                if action in ["add", "sub", "mul", "div"]:
                    btn.setStyleSheet(button_3d_style + f"""
                        QPushButton {{
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {adjust_gradient_color('#3a4a56', GRADIENT_INTENSITY)}, 
                                stop:0.5 {adjust_gradient_color('#2a3a46', GRADIENT_INTENSITY)}, 
                                stop:1 {adjust_gradient_color('#1a2a36', GRADIENT_INTENSITY)});
                        }}
                        QPushButton:hover {{
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {adjust_gradient_color('#4a5a66', GRADIENT_INTENSITY)}, 
                                stop:0.5 {adjust_gradient_color('#3a4a56', GRADIENT_INTENSITY)}, 
                                stop:1 {adjust_gradient_color('#2a3a46', GRADIENT_INTENSITY)});
                        }}
                        QPushButton:pressed {{
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {adjust_gradient_color('#1a2a36', GRADIENT_INTENSITY)}, 
                                stop:0.5 {adjust_gradient_color('#2a3a46', GRADIENT_INTENSITY)}, 
                                stop:1 {adjust_gradient_color('#3a4a56', GRADIENT_INTENSITY)});
                        }}
                    """)
            elif action == "equals":
                btn.clicked.connect(self.equals_pressed)
                self.button_map["equals"] = btn
                btn.setStyleSheet(button_3d_style + f"""
                    QPushButton {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#2f4a37', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#1f3a27', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#0f2a17', GRADIENT_INTENSITY)});
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#3f5a47', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#2f4a37', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#1f3a27', GRADIENT_INTENSITY)});
                    }}
                    QPushButton:pressed {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#0f2a17', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#1f3a27', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#2f4a37', GRADIENT_INTENSITY)});
                    }}
                """)
            elif action == "clear":
                btn.clicked.connect(self.clear_all)
                self.button_map["clear"] = btn
            elif action == "clear_entry":
                btn.clicked.connect(self.handle_escape)
                self.button_map["clear_entry"] = btn
            elif action == "mem_store":
                btn.clicked.connect(self.memory_store)
                self.button_map["mem_store"] = btn
                btn.setStyleSheet(button_3d_style + f"""
                    QPushButton {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#5a4a30', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#4a3a20', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#3a2a10', GRADIENT_INTENSITY)});
                    }}
                    QPushButton:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#6a5a40', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#5a4a30', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#4a3a20', GRADIENT_INTENSITY)});
                    }}
                    QPushButton:pressed {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#3a2a10', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#4a3a20', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#5a4a30', GRADIENT_INTENSITY)});
                    }}
                """)
            elif action == "mem_recall":
                btn.clicked.connect(self.memory_recall)
                self.button_map["mem_recall"] = btn
                btn.setStyleSheet(button_3d_style + f"""
                    QPushButton {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#5a4a30', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#4a3a20', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#3a2a10', GRADIENT_INTENSITY)});
                    }}
                    QPushButton:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#6a5a40', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#5a4a30', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#4a3a20', GRADIENT_INTENSITY)});
                    }}
                    QPushButton:pressed {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#3a2a10', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#4a3a20', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#5a4a30', GRADIENT_INTENSITY)});
                    }}
                """)
            elif action == "mem_add":
                btn.clicked.connect(self.memory_add)
                self.button_map["mem_add"] = btn
                btn.setStyleSheet(button_3d_style + f"""
                    QPushButton {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#5a4a30', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#4a3a20', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#3a2a10', GRADIENT_INTENSITY)});
                    }}
                    QPushButton:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#6a5a40', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#5a4a30', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#4a3a20', GRADIENT_INTENSITY)});
                    }}
                    QPushButton:pressed {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#3a2a10', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#4a3a20', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#5a4a30', GRADIENT_INTENSITY)});
                    }}
                """)
            elif action == "mem_sub":
                btn.clicked.connect(self.memory_sub)
                self.button_map["mem_sub"] = btn
                btn.setStyleSheet(button_3d_style + f"""
                    QPushButton {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#5a4a30', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#4a3a20', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#3a2a10', GRADIENT_INTENSITY)});
                    }}
                    QPushButton:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#6a5a40', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#5a4a30', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#4a3a20', GRADIENT_INTENSITY)});
                    }}
                    QPushButton:pressed {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 {adjust_gradient_color('#3a2a10', GRADIENT_INTENSITY)}, 
                            stop:0.5 {adjust_gradient_color('#4a3a20', GRADIENT_INTENSITY)}, 
                            stop:1 {adjust_gradient_color('#5a4a30', GRADIENT_INTENSITY)});
                    }}
                """)
            
            button_layout.addWidget(btn, row, col)
        
        def handle_lshift():
            if self.shift_btn.text() == "<<":
                self.operation_pressed('lshift')
            elif self.shift_btn.text() == ">>":
                self.operation_pressed('rshift')
                
        # Remove existing connections
        self.shift_btn.clicked.disconnect()
        self.shift_btn.clicked.connect(handle_lshift)
        self.button_map["rshift"] = self.shift_btn
        
        self.calc_layout.addLayout(button_layout)
        
        # Create a container widget for buttons to control its width
        button_container = QWidget()
        button_container.setLayout(self.calc_layout)
        
        # Make sure buttons expand to fill available space
        for i in range(4):  # 4 columns
            button_layout.setColumnStretch(i, 1)
        for i in range(8):  # 8 rows
            button_layout.setRowStretch(i, 1)
        
        # Right side - history panel (now next to buttons)
        self.history_panel = HistoryPanel()
        self.history_panel.entry_clicked.connect(self.copy_history_value)
        
        # Add buttons and history to bottom layout with stretch factors based on ratio
        # Calculate stretch factors from ratio (e.g., 0.6 means buttons get 60%, history gets 40%)
        button_stretch = int(BUTTON_HISTORY_RATIO * 100)
        history_stretch = int((1.0 - BUTTON_HISTORY_RATIO) * 100)
        
        bottom_layout.addWidget(button_container, button_stretch)
        bottom_layout.addWidget(self.history_panel, history_stretch)
        
        # Add bottom layout to main layout
        main_layout.addLayout(bottom_layout)
        
        central.setLayout(main_layout)
        
        # Menu bar
        menubar = self.menuBar()
        
        # File menu with quit
        file_menu = menubar.addMenu("&File")
        
        quit_action = QAction("&Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        copy_action = QAction("&Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy_to_clipboard)
        edit_menu.addAction(copy_action)

        paste_action = QAction("&Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.paste_from_clipboard)
        edit_menu.addAction(paste_action)
        
        edit_menu.addSeparator()
        clear_history_action = QAction("Clear &History", self)
        clear_history_action.triggered.connect(self.history_panel.clear_history)
        edit_menu.addAction(clear_history_action)
        
        edit_menu.addSeparator()
        
        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcuts_action)
        
        # Set window properties
        size_w = 700
        size_h = 480
        self.setMinimumSize(size_w, size_h)
        self.setMaximumSize(size_w, size_h)
        self.resize(size_w, size_h)
        # Prevent resize
        self.setFixedSize(size_w, size_h)
        # Prevent maximize
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)
        
        self.update_display()
        self.update_hex_buttons()
        self.update_mode_label()
    
    def backspace(self):
        """Remove the rightmost digit from current_value"""
        if self.new_number:
            # If we're starting a new number, backspace does nothing
            return
        
        if self.hex_mode:
            # In hex mode, divide by 16 to remove rightmost hex digit
            self.current_value = self.current_value // 16
        else:
            # In decimal mode, divide by 10 to remove rightmost digit
            self.current_value = self.current_value // 10
        
        self.update_display()
        
    def flash_display(self, color_hex):
        """Creates a brief color flash on the main display."""
        # Create effect if it doesn't exist, or reuse
        if not hasattr(self, 'display_effect') or self.display_effect is None:
            self.display_effect = QGraphicsColorizeEffect(self.display_frame)
            self.display_frame.setGraphicsEffect(self.display_effect)
        
        self.display_effect.setColor(QColor(color_hex))
        
        # Animation: Quick fade in, then fade out
        self.anim_in = QPropertyAnimation(self.display_effect, b"strength")
        self.anim_in.setDuration(50)
        self.anim_in.setStartValue(0)
        self.anim_in.setEndValue(0.7)

        self.anim_out = QPropertyAnimation(self.display_effect, b"strength")
        self.anim_out.setDuration(400)
        self.anim_out.setStartValue(0.7)
        self.anim_out.setEndValue(0)

        self.flash_group = QSequentialAnimationGroup()
        self.flash_group.addAnimation(self.anim_in)
        self.flash_group.addAnimation(self.anim_out)
        self.flash_group.start()
        
    def copy_history_value(self, text):
        """Extract result from history string and copy to clipboard in current format"""
        if "=" not in text:
            return
            
        # 1. Extract the result part (after the last '=')
        result_str = text.split("=")[-1].strip()
        
        # 2. Parse the string into a raw integer
        # We need to handle 0x, 0b prefixes and commas
        clean_text = result_str.replace(",", "").replace(" ", "")
        
        try:
            val = 0
            # Try parsing based on prefixes first
            if clean_text.lower().startswith("0x"):
                val = int(clean_text, 16)
            elif clean_text.lower().startswith("0b"):
                val = int(clean_text, 2)
            else:
                # If no prefix, check if it has hex chars (A-F)
                is_hex = any(c in "ABCDEFabcdef" for c in clean_text)
                if is_hex:
                    val = int(clean_text, 16)
                else:
                    # Default to decimal if no obvious hex indicators
                    val = int(clean_text)
            
            # Convert from two's complement if it looks like a large value
            if val > (1 << 63):
                val = val - (1 << 64)
            
            # 3. Format the integer into the CURRENT active mode
            final_text = self.format_value(val)
            
            QApplication.clipboard().setText(final_text)
            
            print(f"Copied history value: {val} -> {final_text}")
            
        except ValueError:
            print(f"Failed to parse history value: {result_str}")
        
    def copy_to_clipboard(self):
        """Copy value to clipboard based on active state"""
        clipboard = QApplication.clipboard()
        val_to_copy = 0

        # Logic: Handle Pending Operations vs Idle State
        if self.operation is not None:
            # If op is pending, ONLY copy active right-hand operand if non-zero
            if self.current_value != 0:
                val_to_copy = self.current_value
            else:
                # Otherwise copy the left-hand operand (stored value)
                val_to_copy = self.stored_value
        else:
            # No operation pending, copy current value
            val_to_copy = self.current_value

        # Format and copy to clipboard
        clipboard.setText(self.format_value(val_to_copy))
        self.flash_display("#68AF4C") # Success Green

    def paste_from_clipboard(self):
        """Paste value from clipboard"""
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        
        if not text:
            return

        # Clean cleanup (remove commas, spaces)
        clean_text = text.replace(",", "").replace(" ", "")
        
        try:
            # Attempt to parse
            # Support 0x and 0b prefixes explicitly
            if clean_text.lower().startswith("0x"):
                new_val = int(clean_text, 16)
            elif clean_text.lower().startswith("0b"):
                new_val = int(clean_text, 2)
            else:
                # If in Hex mode, try base 16, otherwise base 10
                if self.hex_mode:
                    try:
                        new_val = int(clean_text, 16)
                    except ValueError:
                        # Fallback to decimal if hex parse fails
                        new_val = int(clean_text) 
                else:
                    new_val = int(clean_text)

            # Convert from two's complement if necessary
            if new_val > (1 << 63):
                new_val = new_val - (1 << 64)

            # Logic: Overwrite current value
            self.current_value = new_val
            self.new_number = False
            self.update_display()
            self.flash_display("#D39E2C") # Yellow/Orange
            
        except ValueError:
            print(f"Could not paste: {text}")
    
    def load_settings(self):
        """Load settings from JSON file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
            except Exception as e:
                print(f"Error loading config: {e}")

        self.hex_mode = self.config.get("hex_mode", False)

        # Apply Font
        font_str = self.config.get("display_font")
        if font_str:
            font = QFont()
            if font.fromString(font_str):
                if hasattr(self, "display"):
                    self.display.setFont(font)
        h_font_str = self.config.get("history_font")
        if h_font_str:
            if hasattr(self, "history_panel"):
                font = QFont()
                if font.fromString(h_font_str):
                    self.history_panel.set_history_font(font)
        else:
            if hasattr(self, "history_panel"):
                default_h_font = QFont("Consolas", 9)
                self.history_panel.set_history_font(default_h_font)
        self.update_display()
        self.update_mode_label()
        self.update_hex_buttons()
    
    def save_settings(self):
        """Save settings to JSON file"""
        self.config["display_font"] = self.display.font().toString()
        self.config["history_font"] = self.history_panel.current_font.toString()
        self.config["hex_mode"] = self.hex_mode
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
            
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Apply settings
            self.config["hex_prefix"] = dialog.hex_prefix_check.isChecked()
            self.config["bin_prefix"] = dialog.bin_prefix_check.isChecked()
            self.config["show_commas"] = dialog.commas_check.isChecked()
            
            if dialog.selected_font:
                self.display.setFont(dialog.selected_font)
                
            if dialog.selected_hist_font:
                self.history_panel.set_history_font(dialog.selected_hist_font)
            
            self.update_display()
    
    def show_shortcuts(self):
        """Show keyboard shortcuts help"""
        shortcuts = """
<h3>Keyboard Shortcuts</h3>
<table>
<tr><td><b>0-9</b></td><td>Number entry (numpad supported)</td></tr>
<tr><td><b>A-F</b></td><td>Hex digits (in HEX mode)</td></tr>
<tr><td><b>X</b></td><td>Toggle to HEX mode</td></tr>
<tr><td><b>R</b></td><td>Memory Recall</td></tr>
<tr><td><b>P</b></td><td>Memory Store</td></tr>
<tr><td><b>+, -, *, /</b></td><td>Basic operations (numpad supported)</td></tr>
<tr><td><b>%</b></td><td>Modulo</td></tr>
<tr><td><b>Enter</b></td><td>Equals</td></tr>
<tr><td><b>Backspace</b></td><td>Delete last digit</td></tr>
<tr><td><b>ESC</b></td><td>Clear pending op (1st), entry (2nd)</td></tr>
<tr><td><b>ESC x3</b></td><td>Clear Memory (within 2 secs)</td></tr>
<tr><td><b>Delete</b></td><td>Clear all</td></tr>
</table>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("Keyboard Shortcuts")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(shortcuts)
        msg.exec()
    
    # --- Memory Functions ---
    def memory_store(self):
        """Store current value to memory"""
        self.memory_value = self.current_value
        self.new_number = True
        self.update_mode_label()
        self.flash_display("#3D8CCC") # Blue-ish
    
    def memory_recall(self):
        """Recall memory"""
        if self.operation is not None or self.current_value == 0:
            self.current_value = self.memory_value
            self.new_number = False
            self.update_display()
            self.flash_display("#422775") # Purple-ish
            
    def memory_add(self):
        """Add current to memory"""
        self.memory_value += self.current_value
        self.new_number = True
        
    def memory_sub(self):
        """Subtract current from memory"""
        self.memory_value -= self.current_value
        self.new_number = True
        
    def check_clear_counter(self):
        """Handle 3x press logic to clear memory"""
        now = time.time()
        
        if now - self.last_clear_time > 1.0:
            self.clear_press_count = 0
            
        self.clear_press_count += 1
        self.last_clear_time = now
        
        if self.clear_press_count >= 3:
            self.memory_value = 0
            self.clear_press_count = 0
            self.update_mode_label()
    
    def flash_button_for_key(self, action_key):
        """Flash a button when its keyboard shortcut is used"""
        if action_key in self.button_map:
            self.button_map[action_key].flash()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard input"""
        key = event.key()
        text = event.text().upper()
        modifiers = event.modifiers()
        
        if event.key() == Qt.Key.Key_Shift:
            if hasattr(self, 'shift_btn'):
                self.shift_btn.setText(">>")
                
        if event.text() == "<":
            self.operation_pressed('lshift')
            self.flash_button_for_key('lshift')
        elif event.text() == ">":
            self.operation_pressed('rshift')
            self.flash_button_for_key('rshift')
        
        # Copy / Paste Shortcuts
        if (key == Qt.Key.Key_C and modifiers == Qt.KeyboardModifier.ControlModifier):
            self.copy_to_clipboard()
            return

        if (key == Qt.Key.Key_V and modifiers == Qt.KeyboardModifier.ControlModifier):
            self.paste_from_clipboard()
            return
        
        # Backspace key
        if key == Qt.Key.Key_Backspace:
            self.backspace()
            return

        # Number keys (including numpad)
        if key in [Qt.Key.Key_0, Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_4,
                   Qt.Key.Key_5, Qt.Key.Key_6, Qt.Key.Key_7, Qt.Key.Key_8, Qt.Key.Key_9]:
            num = int(text) if text.isdigit() else key - Qt.Key.Key_0
            self.number_pressed(num)
            self.flash_button_for_key(str(num))
        
        # Hex digits A-F
        elif text in "ABCDEF" and self.hex_mode:
            self.hex_digit_pressed(text)
            self.flash_button_for_key(text)
        
        # Mode switching
        elif text == 'C' and not self.hex_mode:
            self.clear_all()
            self.flash_button_for_key("clear")
        elif text == 'X':
            if self.hex_mode:
                self.switch_mode(False)
            else:
                self.switch_mode(True)

        elif text == 'R':
            self.memory_recall()
            self.flash_button_for_key("mem_recall")
        elif text == 'P':
            self.memory_store()
            self.flash_button_for_key("mem_store")
        
        # Operations
        elif key in [Qt.Key.Key_Plus, Qt.Key.Key_Equal] and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            self.operation_pressed("add")
            self.flash_button_for_key("add")
        elif key == Qt.Key.Key_Plus:
            self.operation_pressed("add")
            self.flash_button_for_key("add")
        elif key == Qt.Key.Key_Minus:
            self.operation_pressed("sub")
            self.flash_button_for_key("sub")
        elif key in [Qt.Key.Key_Asterisk, Qt.Key.Key_8] and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            self.operation_pressed("mul")
            self.flash_button_for_key("mul")
        elif key == Qt.Key.Key_Asterisk:
            self.operation_pressed("mul")
            self.flash_button_for_key("mul")
        elif key == Qt.Key.Key_Slash:
            self.operation_pressed("div")
            self.flash_button_for_key("div")
        elif key in [Qt.Key.Key_Percent, Qt.Key.Key_5] and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            self.operation_pressed("mod")
            self.flash_button_for_key("mod")
        
        # Equals
        elif key in [Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Equal]:
            self.equals_pressed()
            self.flash_button_for_key("equals")
        
        # Clear / Smart ESC
        elif key == Qt.Key.Key_Escape:
            self.handle_escape()
            self.flash_button_for_key("clear_entry")
        elif key == Qt.Key.Key_Delete:
            self.clear_all()
            self.flash_button_for_key("clear")
        
        else:
            super().keyPressEvent(event)
            
    def keyReleaseEvent(self, event: QKeyEvent):
        # Revert button label when Shift is released
        if event.key() == Qt.Key.Key_Shift:
            if hasattr(self, 'shift_btn'):
                self.shift_btn.setText("<<")
        super().keyReleaseEvent(event)
        
    def changeEvent(self, event):
        # Revert button label if app loses focus while shift is held
        if event.type() == event.Type.ActivationChange:
            if not self.isActiveWindow() and hasattr(self, 'shift_btn'):
                self.shift_btn.setText("<<")
        super().changeEvent(event)
    
    def switch_mode(self, to_hex):
        """Switch between decimal and hex mode"""
        if self.hex_mode == to_hex:
            return
        
        self.hex_mode = to_hex
        self.update_mode_label()
        self.update_display()
        self.update_hex_buttons()
        
    def update_mode_label(self):
        if not hasattr(self, "mode_label"):
            return
        _str = "HEX" if self.hex_mode else "DEC"
        if self.memory_value != 0:
            _str += f" (M)"
        self.mode_label.setText(_str)
    
    def update_hex_buttons(self):
        """Enable/disable hex buttons based on mode"""
        if not hasattr(self, "buttons"):
            return
        enabled = self.hex_mode
        for letter in "ABCDEF":
            if letter in self.buttons:
                self.buttons[letter].setEnabled(enabled)
    
    def number_pressed(self, num):
        """Handle number button press"""
        if self.new_number:
            self.current_value = num
            self.new_number = False
        else:
            if self.hex_mode:
                self.current_value = (self.current_value * 16) + num
            else:
                self.current_value = (self.current_value * 10) + num
        
        self.update_display()
    
    def hex_digit_pressed(self, letter):
        """Handle hex digit (A-F) press"""
        if not self.hex_mode:
            return
        
        if letter is None or len(letter) != 1:
            return
        
        value = ord(letter) - ord('A') + 10
        
        if self.new_number:
            self.current_value = value
            self.new_number = False
        else:
            self.current_value = (self.current_value * 16) + value
        
        self.update_display()

    def operation_pressed(self, op):
        """Handle operation button press"""
        if self.operation and not self.new_number:
            self.equals_pressed()
        else:
            self.stored_value = self.current_value
        
        self.operation = op
        self.new_number = True
        
        # Update Pending Operation Label
        op_symbols = {
            "add": "+", "sub": "-", "mul": "*", "div": "/",
            "mod": "%", "and": "&", "or": "|", "xor": "^", "lshift": "<<", "rshift": ">>"
        }
        self.op_label.setText(op_symbols.get(op, op))
    
    def equals_pressed(self):
        """Handle equals button press"""
        
        # 1. Determine operands and operation
        if self.operation:
            # Normal case: Pending operation
            a = self.stored_value
            b = self.current_value
            op = self.operation
            
            # Save for repeat capability
            self.last_operation = op
            self.last_operand = b
            
        elif self.last_operation is not None:
            # Repeat case: No pending op, use previous
            a = self.current_value
            b = self.last_operand
            op = self.last_operation
        else:
            # Nothing to do
            return

        # 2. Calculate
        try:
            result = 0
            if op == "add":
                result = a + b
            elif op == "sub":
                result = a - b
            elif op == "mul":
                result = a * b
            elif op == "div":
                result = int(a / b) if b != 0 else 0
            elif op == "mod":
                result = a % b if b != 0 else 0
            elif op == "and":
                result = a & b
            elif op == "or":
                result = a | b
            elif op == "xor":
                result = a ^ b
            elif op == "lshift":
                result = a << b
            elif op == "rshift":
                result = a >> b
            
            # Add to history
            op_symbols = {
                "add": "+", "sub": "-", "mul": "*", "div": "/",
                "mod": "%", "and": "&", "or": "|", "xor": "^", "lshift": "<<", "rshift": ">>"
            }
            op_text = op_symbols.get(op, op)
            self.add_history(
                f"{self.format_value(a)} {op_text} {self.format_value(b)} = {self.format_value(result)}"
            )
            
            self.current_value = result
            self.operation = None
            self.op_label.setText("")
            self.new_number = True
            self.update_display()
            
        except Exception as e:
            self.display.setText("Error")
            print(f"Calculation error: {e}")
    
    def handle_escape(self):
        """Smart ESC: Clears pending Op first, then Number."""
        self.check_clear_counter()

        if self.operation is not None:
            # First press: Cancel pending operation
            self.operation = None
            self.op_label.setText("")
        else:
            # Second press (or no op): Clear current entry
            self.clear_entry()

    def clear_entry(self):
        """Clear current entry"""
        self.current_value = 0
        self.new_number = True
        self.update_display()
    
    def clear_all(self):
        """Clear all"""
        self.check_clear_counter()

        self.current_value = 0
        self.stored_value = 0
        self.operation = None
        self.op_label.setText("")
        
        self.last_operation = None
        self.last_operand = None
        
        self.new_number = True
        self.update_display()
    
    def format_value(self, value, force_mode=None):
        """Format value based on current mode with proper negative hex handling"""
        mode = force_mode if force_mode is not None else self.hex_mode
        
        if mode:  # Hex
            if value < 0:
                # Use 64-bit two's complement for negative numbers
                value = (1 << 64) + value
            hex_str = hex(value)[2:].upper()
            prefix = "0x" if self.config.get("hex_prefix", True) else ""
            return f"{prefix}{hex_str}"
        else:  # Decimal
            if self.config.get("show_commas", False):
                return f"{value:,}"
            return str(value)
    
    def update_display(self):
        """Update the display labels"""
        if not hasattr(self, "display") or not hasattr(self, "alt_display"):
            return
        # Main display
        self.display.setText(self.format_value(self.current_value))
        
        # Alternative representations
        hex_prefix = "0x" if self.config.get("hex_prefix", True) else ""
        bin_prefix = "0b" if self.config.get("bin_prefix", True) else ""
        
        # For binary representation, handle negatives with two's complement
        if self.current_value < 0:
            bin_val = (1 << 64) + self.current_value
            bin_str = bin(bin_val)[2:]
        else:
            bin_str = bin(self.current_value)[2:]
        
        if self.hex_mode:
            # Show decimal and binary
            dec_str = str(self.current_value)
            self.alt_display.setText(f"DEC: {dec_str}  BIN: {bin_prefix}{bin_str}")
        else:
            # Show hex and binary
            if self.current_value < 0:
                hex_val = (1 << 64) + self.current_value
                hex_str = hex(hex_val)[2:].upper()
            else:
                hex_str = hex(self.current_value)[2:].upper()
            self.alt_display.setText(f"HEX: {hex_prefix}{hex_str}  BIN: {bin_prefix}{bin_str}")
    
    def add_history(self, text):
        """Add entry to history panel"""
        self.history_panel.add_entry(text)
    
    def closeEvent(self, event):
        """Handle window close"""
        self.save_settings()
        event.accept()


def main():
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(theme="dark", custom_colors={"background": "#1e1e1e", "foreground": "#c5c5c5"})
    icon = icon_from_base64_png(ICON_PNG_BASE64)
    app.setWindowIcon(icon)
    
    calculator = ProgrammerCalculator()
    calculator.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()