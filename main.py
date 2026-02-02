#!/usr/bin/env python3
"""
Programmer's Calculator - A polished calculator with decimal/hex conversion
Updated with JSON config, pending op display, and smart ESC.
"""

import sys
import json
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QLabel, QDialog, QDialogButtonBox,
    QCheckBox, QFontDialog, QScrollArea, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeyEvent, QAction
import qdarktheme


def get_app_path():
    """Resolve the correct path for both script and frozen (PyInstaller) execution."""
    if getattr(sys, 'frozen', False):
        # Running as compiled EXE
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent


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
    
    def choose_font(self):
        """Open font dialog"""
        current_font = self.parent().display.font()
        font, ok = QFontDialog.getFont(current_font, self)
        if ok:
            self.selected_font = font


class HistoryPanel(QFrame):
    """History panel showing previous calculations"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.setMaximumWidth(320)
        self.setMinimumWidth(320)
        
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
    
    def add_entry(self, text):
        """Add a history entry"""
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("padding: 4px; background-color: #101010; border-radius: 3px;")
        font = QFont()
        font.setPointSize(9)
        label.setFont(font)
        
        # Insert at the top (before stretch)
        self.history_layout.insertWidget(0, label)
        self.history_items.insert(0, label)
        
        # Keep only last 50 items
        if len(self.history_items) > 50:
            old_label = self.history_items.pop()
            self.history_layout.removeWidget(old_label)
            old_label.deleteLater()
    
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
            "display_font": None
        }
        self.config_file = get_app_path() / "config.json"

        # Calculator state
        self.current_value = 0
        self.stored_value = 0
        self.operation = None
        
        # Repeat operation state
        self.last_operation = None
        self.last_operand = None
        
        self.hex_mode = False  # False = decimal, True = hex
        self.new_number = True
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Programmer's Calculator")
        
        # Central widget and main layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        
        # Left side - calculator
        calc_layout = QVBoxLayout()
        calc_layout.setSpacing(8)
        
        # Display area
        display_frame = QFrame()
        display_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        display_layout = QVBoxLayout()
        display_layout.setContentsMargins(10, 10, 10, 10)
        
        # Top info row (Mode + Pending Op)
        info_layout = QHBoxLayout()
        
        # Mode indicator
        self.mode_label = QLabel("DEC")
        mode_font = QFont()
        mode_font.setBold(True)
        mode_font.setPointSize(9)
        self.mode_label.setFont(mode_font)
        self.mode_label.setStyleSheet("color: #0066cc;")
        info_layout.addWidget(self.mode_label)
        
        info_layout.addStretch()
        
        # Pending Operation Indicator
        self.op_label = QLabel("")
        self.op_label.setFont(mode_font)
        self.op_label.setStyleSheet("color: #ffa500;") # Orange for visibility
        info_layout.addWidget(self.op_label)
        
        display_layout.addLayout(info_layout)
        
        # Main display
        self.display = QLabel("0")
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        display_font = QFont("Consolas", 24)
        self.display.setFont(display_font)
        self.display.setMinimumHeight(60)
        display_layout.addWidget(self.display)
        
        # Alternative representations
        self.alt_display = QLabel("HEX: 0x0  BIN: 0b0")
        alt_font = QFont("Consolas", 9)
        self.alt_display.setFont(alt_font)
        self.alt_display.setStyleSheet("padding: 5px; background-color: #f5f5f5; color: #666;")
        display_layout.addWidget(self.alt_display)
        
        display_frame.setLayout(display_layout)
        calc_layout.addWidget(display_frame)
        
        # Button grid
        button_layout = QGridLayout()
        button_layout.setSpacing(4)
        
        # Button definitions (text, row, col, operation/value)
        buttons = [
            # Row 0
            ("C", 0, 0, "clear"), ("CE", 0, 1, "clear_entry"), ("%", 0, 2, "mod"), ("/", 0, 3, "div"),
            # Row 1
            ("7", 1, 0, 7), ("8", 1, 1, 8), ("9", 1, 2, 9), ("*", 1, 3, "mul"),
            # Row 2
            ("4", 2, 0, 4), ("5", 2, 1, 5), ("6", 2, 2, 6), ("-", 2, 3, "sub"),
            # Row 3
            ("1", 3, 0, 1), ("2", 3, 1, 2), ("3", 3, 2, 3), ("+", 3, 3, "add"),
            # Row 4
            ("0", 4, 0, 0), ("AND", 4, 1, "and"), ("OR", 4, 2, "or"), ("=", 4, 3, "equals"),
            # Row 5 - Hex digits
            ("A", 5, 0, "A"), ("B", 5, 1, "B"), ("C", 5, 2, "C"), ("D", 5, 3, "D"),
            # Row 6
            ("E", 6, 0, "E"), ("F", 6, 1, "F"), ("XOR", 6, 2, "xor"), ("<<", 6, 3, "lshift"),
        ]
        
        self.buttons = {}
        for text, row, col, action in buttons:
            btn = QPushButton(text)
            btn.setMinimumSize(50, 40)
            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #a0a0a0;
                    border-radius: 3px;
                    font-size: 12pt;
                }
            """)
            
            if isinstance(action, int):
                btn.clicked.connect(lambda checked, a=action: self.number_pressed(a))
            elif action in ["A", "B", "C", "D", "E", "F"]:
                btn.clicked.connect(lambda checked, a=action: self.hex_digit_pressed(a))
                self.buttons[action] = btn
            elif action in ["add", "sub", "mul", "div", "mod", "and", "or", "xor", "lshift"]:
                btn.clicked.connect(lambda checked, a=action: self.operation_pressed(a))
                if action in ["add", "sub", "mul", "div"]:
                    btn.setStyleSheet(btn.styleSheet() + "QPushButton { background-color: #243036; }")
            elif action == "equals":
                btn.clicked.connect(self.equals_pressed)
                btn.setStyleSheet(btn.styleSheet() + "QPushButton { background-color: #1f2b27; font-weight: bold; }")
            elif action == "clear":
                btn.clicked.connect(self.clear_all)
            elif action == "clear_entry":
                btn.clicked.connect(self.handle_escape) # Map CE button to same smart logic if desired, or keep as clear_entry
            
            button_layout.addWidget(btn, row, col)
        
        calc_layout.addLayout(button_layout)
        
        # Mode switch hint
        # hint = QLabel("Press 'C' for DEC mode, 'X' for HEX mode")
        # hint.setStyleSheet("color: #666; font-size: 9pt;")
        # hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # calc_layout.addWidget(hint)
        
        main_layout.addLayout(calc_layout)
        
        # Right side - history panel
        self.history_panel = HistoryPanel()
        main_layout.addWidget(self.history_panel)
        
        central.setLayout(main_layout)
        
        # Menu bar
        menubar = self.menuBar()
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
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
        size_h = 540
        self.setMinimumSize(size_w, size_h)
        self.setMaximumSize(size_w, size_h)
        self.resize(size_w, size_h)
        # Prevent resize
        self.setFixedSize(size_w, size_h)
        # Prevent maximize
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)
        
        self.update_display()
        self.update_hex_buttons()
    
    def load_settings(self):
        """Load settings from JSON file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
            except Exception as e:
                print(f"Error loading config: {e}")

        # Apply Font
        font_str = self.config.get("display_font")
        if font_str:
            font = QFont()
            if font.fromString(font_str):
                self.display.setFont(font)
    
    def save_settings(self):
        """Save settings to JSON file"""
        self.config["display_font"] = self.display.font().toString()
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
            
            self.update_display()
    
    def show_shortcuts(self):
        """Show keyboard shortcuts help"""
        shortcuts = """
<h3>Keyboard Shortcuts</h3>
<table>
<tr><td><b>0-9</b></td><td>Number entry (numpad supported)</td></tr>
<tr><td><b>A-F</b></td><td>Hex digits (in HEX mode)</td></tr>
<tr><td><b>X</b></td><td>Toggle to HEX mode</td></tr>
<tr><td><b>+, -, *, /</b></td><td>Basic operations (numpad supported)</td></tr>
<tr><td><b>%</b></td><td>Modulo</td></tr>
<tr><td><b>Enter</b></td><td>Equals</td></tr>
<tr><td><b>ESC</b></td><td>Clear pending op (1st press), then entry (2nd)</td></tr>
<tr><td><b>Delete</b></td><td>Clear all</td></tr>
</table>
        """
        msg = QMessageBox(self)
        msg.setWindowTitle("Keyboard Shortcuts")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(shortcuts)
        msg.exec()
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard input"""
        key = event.key()
        text = event.text().upper()
        
        # Number keys (including numpad)
        if key in [Qt.Key.Key_0, Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_4,
                   Qt.Key.Key_5, Qt.Key.Key_6, Qt.Key.Key_7, Qt.Key.Key_8, Qt.Key.Key_9]:
            num = int(text) if text.isdigit() else key - Qt.Key.Key_0
            self.number_pressed(num)
        
        # Hex digits A-F
        elif text in "ABCDEF" and self.hex_mode:
            self.hex_digit_pressed(text)
        
        # Mode switching
        elif text == 'C' and not self.hex_mode:
            pass
        elif text == 'X':
            if self.hex_mode:
                self.switch_mode(False)
            else:
                self.switch_mode(True)
        
        # Operations
        elif key in [Qt.Key.Key_Plus, Qt.Key.Key_Equal] and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            self.operation_pressed("add")
        elif key == Qt.Key.Key_Plus:
            self.operation_pressed("add")
        elif key == Qt.Key.Key_Minus:
            self.operation_pressed("sub")
        elif key in [Qt.Key.Key_Asterisk, Qt.Key.Key_8] and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            self.operation_pressed("mul")
        elif key == Qt.Key.Key_Asterisk:
            self.operation_pressed("mul")
        elif key == Qt.Key.Key_Slash:
            self.operation_pressed("div")
        elif key in [Qt.Key.Key_Percent, Qt.Key.Key_5] and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            self.operation_pressed("mod")
        
        # Equals
        elif key in [Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Equal]:
            self.equals_pressed()
        
        # Clear / Smart ESC
        elif key == Qt.Key.Key_Escape:
            self.handle_escape()
        elif key == Qt.Key.Key_Delete:
            self.clear_all()
        
        else:
            super().keyPressEvent(event)
    
    def switch_mode(self, to_hex):
        """Switch between decimal and hex mode"""
        if self.hex_mode == to_hex:
            return
        
        self.hex_mode = to_hex
        self.mode_label.setText("HEX" if to_hex else "DEC")
        self.update_display()
        self.update_hex_buttons()
    
    def update_hex_buttons(self):
        """Enable/disable hex buttons based on mode"""
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
            "mod": "%", "and": "&", "or": "|", "xor": "^", "lshift": "<<"
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
            
            # Add to history
            op_symbols = {
                "add": "+", "sub": "-", "mul": "*", "div": "/",
                "mod": "%", "and": "&", "or": "|", "xor": "^", "lshift": "<<"
            }
            op_text = op_symbols.get(op, op)
            self.add_history(
                f"{self.format_value(a)} {op_text} {self.format_value(b)} = {self.format_value(result)}"
            )
            
            self.current_value = result
            self.operation = None # Clear pending op
            self.op_label.setText("") # Clear pending UI symbol
            self.new_number = True
            self.update_display()
            
        except Exception as e:
            self.display.setText("Error")
            print(f"Calculation error: {e}")
    
    def handle_escape(self):
        """Smart ESC: Clears pending Op first, then Number."""
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
        self.current_value = 0
        self.stored_value = 0
        self.operation = None
        self.op_label.setText("")
        
        self.last_operation = None
        self.last_operand = None
        
        self.new_number = True
        self.update_display()
    
    def format_value(self, value, force_mode=None):
        """Format value based on current mode"""
        mode = force_mode if force_mode is not None else self.hex_mode
        
        if mode:  # Hex
            hex_str = hex(value)[2:].upper() if value >= 0 else hex(value)[3:].upper()
            prefix = "0x" if self.config.get("hex_prefix", True) else ""
            return f"{prefix}{hex_str}"
        else:  # Decimal
            if self.config.get("show_commas", False):
                return f"{value:,}"
            return str(value)
    
    def update_display(self):
        """Update the display labels"""
        # Main display
        self.display.setText(self.format_value(self.current_value))
        
        # Alternative representations
        hex_prefix = "0x" if self.config.get("hex_prefix", True) else ""
        bin_prefix = "0b" if self.config.get("bin_prefix", True) else ""
        
        if self.hex_mode:
            # Show decimal and binary
            dec_str = str(self.current_value)
            # Add commas to alt display if enabled? Usually alt display is raw, but consistency is good. 
            # Let's keep alt display raw for readability unless requested otherwise.
            
            bin_str = bin(self.current_value)[2:] if self.current_value >= 0 else bin(self.current_value)[3:]
            self.alt_display.setText(f"DEC: {dec_str}  BIN: {bin_prefix}{bin_str}")
        else:
            # Show hex and binary
            hex_str = hex(self.current_value)[2:].upper() if self.current_value >= 0 else hex(self.current_value)[3:].upper()
            bin_str = bin(self.current_value)[2:] if self.current_value >= 0 else bin(self.current_value)[3:]
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
    qdarktheme.setup_theme()
    
    calculator = ProgrammerCalculator()
    calculator.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()