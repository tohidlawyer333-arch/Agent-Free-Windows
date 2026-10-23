import os, sys
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QThread, Qt
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QDialog, QFormLayout, QComboBox, QMessageBox,
    QDialogButtonBox, QCheckBox)
import keyring
from providers import ProviderConfig, PRESETS
from agent import Agent

APP_NAME = "AgentFreeWindows"
WORKSPACE = str(Path.home() / "AgentFreeWorkspace")

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent); self.setWindowTitle("تنظیمات اتصال مدل"); self.setMinimumWidth(520)
        self.config = config
        layout = QFormLayout(self)
        self.provider = QComboBox(); self.provider.addItems(list(PRESETS)); self.provider.setCurrentText(config.name if config.name in PRESETS else "Custom OpenAI-compatible")
        self.base = QLineEdit(config.base_url); self.model = QLineEdit(config.model)
        self.key = QLineEdit(config.api_key); self.key.setEchoMode(QLineEdit.Password)
        self.show_key = QCheckBox("نمایش کلید"); self.show_key.toggled.connect(lambda on: self.key.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password))
        self.provider.currentTextChanged.connect(self.apply_preset)
        layout.addRow("ارائه‌دهنده", self.provider); layout.addRow("Base URL", self.base); layout.addRow("مدل", self.model)
        row = QHBoxLayout(); row.addWidget(self.key); row.addWidget(self.show_key); layout.addRow("API Key", row)
        note = QLabel("کلید با keyring سیستم ذخیره می‌شود. سهمیه و هزینه را در وب‌سایت ارائه‌دهنده بررسی کنید."); note.setWordWrap(True); layout.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addRow(buttons)
    def apply_preset(self, name):
        if name in PRESETS:
            url, model = PRESETS[name]; self.base.setText(url); self.model.setText(model)
    def result_config(self):
        return ProviderConfig(self.provider.currentText(), self.base.text().strip(), self.model.text().strip(), self.key.text())

class Worker(QObject):
    done = Signal(str); failed = Signal(str)
    def __init__(self, config, history, prompt, window): super().__init__(); self.config=config; self.history=history; self.prompt=prompt; self.window=window
    def run(self):
        try:
            agent = Agent(self.config, WORKSPACE, self.window.confirm_command_threadsafe)
            answer = agent.ask(self.history, self.prompt); self.done.emit(answer)
        except Exception as e: self.failed.emit(f"خطا در ارتباط با مدل: {e}")

class MainWindow(QMainWindow):
    approval_requested = Signal(str, object)
    def __init__(self):
        super().__init__(); self.setWindowTitle("Agent Free Windows"); self.resize(1000, 720); self.setLayoutDirection(Qt.RightToLeft)
        self.config = self.load_config(); self.history=[]; self.busy=False
        root=QWidget(); self.setCentralWidget(root); layout=QVBoxLayout(root)
        top=QHBoxLayout(); title=QLabel("Agent Free Windows | دستیار هوشمند ویندوز"); title.setStyleSheet("font-size:18px;font-weight:bold")
        settings=QPushButton("تنظیمات مدل"); settings.clicked.connect(self.open_settings); top.addWidget(title); top.addStretch(); top.addWidget(settings); layout.addLayout(top)
        self.chat=QTextEdit(); self.chat.setReadOnly(True); self.chat.setPlaceholderText("پیام‌ها اینجا نمایش داده می‌شوند."); layout.addWidget(self.chat)
        row=QHBoxLayout(); self.input=QLineEdit(); self.input.setPlaceholderText("درخواستت را بنویس…"); self.input.returnPressed.connect(self.send_message)
        self.send=QPushButton("ارسال"); self.send.clicked.connect(self.send_message); row.addWidget(self.input,1); row.addWidget(self.send); layout.addLayout(row)
        self.status=QLabel(f"فضای کاری: {WORKSPACE}"); layout.addWidget(self.status)
        self.approval_requested.connect(self._confirm_command, Qt.BlockingQueuedConnection)
        self.chat.append("سلام. برای شروع، در تنظیمات یک API endpoint و کلید معتبر وارد کن. اجرای فرمان‌های PowerShell قبل از اجرا نیازمند تأیید توست.")
    def load_config(self):
        name=keyring.get_password(APP_NAME,"provider") or "Google Gemini"
        base=keyring.get_password(APP_NAME,"base_url") or PRESETS.get(name, PRESETS["Google Gemini"])[0]
        model=keyring.get_password(APP_NAME,"model") or PRESETS.get(name, PRESETS["Google Gemini"])[1]
        key=keyring.get_password(APP_NAME,"api_key") or ""
        return ProviderConfig(name,base,model,key)
    def open_settings(self):
        dlg=SettingsDialog(self.config,self)
        if dlg.exec():
            self.config=dlg.result_config()
            for k,v in (("provider",self.config.name),("base_url",self.config.base_url),("model",self.config.model),("api_key",self.config.api_key)):
                keyring.set_password(APP_NAME,k,v)
            self.chat.append("[سیستم] تنظیمات ذخیره شد.")
    def confirm_command_threadsafe(self, command):
        box={"answer":False}; self.approval_requested.emit(command,box); return box["answer"]
    def _confirm_command(self, command, box):
        box["answer"] = QMessageBox.warning(self,"تأیید اجرای PowerShell",f"مدل درخواست اجرای این فرمان را دارد:\n\n{command}\n\nفرمان را فقط در صورتی تأیید کن که محتوایش را بررسی کرده‌ای.",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)==QMessageBox.Yes
    def send_message(self):
        prompt=self.input.text().strip()
        if not prompt or self.busy: return
        self.input.clear(); self.chat.append(f"<b>شما:</b> {prompt}"); self.busy=True; self.send.setEnabled(False); self.status.setText("در حال دریافت پاسخ…")
        self.thread=QThread(); self.worker=Worker(self.config,list(self.history),prompt,self); self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run); self.worker.done.connect(self.on_done); self.worker.failed.connect(self.on_failed)
        self.worker.done.connect(self.thread.quit); self.worker.failed.connect(self.thread.quit); self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater); self.thread.start()
        self._pending_prompt=prompt
    def on_done(self, answer):
        self.chat.append(f"<b>دستیار:</b> {answer}"); self.history.extend([{"role":"user","content":self._pending_prompt},{"role":"assistant","content":answer}]); self.finish()
    def on_failed(self, error): self.chat.append(f"<b>خطا:</b> {error}"); self.finish()
    def finish(self): self.busy=False; self.send.setEnabled(True); self.status.setText(f"فضای کاری: {WORKSPACE}")

def main():
    os.makedirs(WORKSPACE,exist_ok=True); app=QApplication(sys.argv); app.setStyle("Fusion"); w=MainWindow(); w.show(); sys.exit(app.exec())
if __name__=="__main__": main()
