from pathlib import Path
import subprocess

class ToolRegistry:
    def __init__(self, workspace: str):
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _path(self, rel: str) -> Path:
        p = (self.workspace / rel).resolve()
        if p != self.workspace and self.workspace not in p.parents:
            raise ValueError("مسیر خارج از پوشه کاری مجاز نیست.")
        return p

    def list_files(self, path: str = ".") -> str:
        p = self._path(path)
        if not p.exists(): return "مسیر پیدا نشد."
        if p.is_file(): return p.name
        return "\n".join(("[DIR] " if x.is_dir() else "[FILE] ") + x.name for x in sorted(p.iterdir()))[:12000]

    def read_file(self, path: str) -> str:
        p = self._path(path)
        if not p.is_file(): raise ValueError("فایل پیدا نشد.")
        if p.stat().st_size > 1_000_000: raise ValueError("فایل بزرگ‌تر از ۱ مگابایت است.")
        return p.read_text(encoding="utf-8", errors="replace")

    def write_file(self, path: str, content: str) -> str:
        p = self._path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"فایل ذخیره شد: {p.name}"

    def run_powershell(self, command: str) -> str:
        # This function is called only after the UI asks for explicit approval.
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            cwd=str(self.workspace), capture_output=True, text=True, timeout=60,
            encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        out = (result.stdout + "\n" + result.stderr).strip()
        return (out or f"فرمان با کد خروج {result.returncode} تمام شد.")[:16000]
