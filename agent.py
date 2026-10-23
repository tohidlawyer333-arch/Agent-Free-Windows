import json
from openai import OpenAI
from providers import ProviderConfig, make_client
from tools import ToolRegistry

SYSTEM_PROMPT = """تو دستیار دسکتاپ ویندوزی هستی. فارسی پاسخ بده مگر کاربر زبان دیگری بخواهد. برای کار با فایل‌ها از ابزارها استفاده کن و هرگز ادعا نکن کاری انجام شده مگر ابزار آن را تأیید کرده باشد. ابزار PowerShell پرخطر است و فقط پس از تأیید صریح کاربر اجرا می‌شود. قبل از حذف، نصب، تغییر تنظیمات سیستم یا عملیات مخرب، توضیح بده و تأیید بگیر. کلیدهای API و اسرار را در خروجی چاپ نکن. فضای کاری محلی محدود به پوشه مشخص‌شده است."""

TOOLS = [
 {"type":"function","function":{"name":"list_files","description":"فهرست فایل‌ها و پوشه‌ها در فضای کاری","parameters":{"type":"object","properties":{"path":{"type":"string","default":"."}},"required":[]}}},
 {"type":"function","function":{"name":"read_file","description":"خواندن فایل متنی از فضای کاری","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
 {"type":"function","function":{"name":"write_file","description":"نوشتن فایل متنی در فضای کاری","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
 {"type":"function","function":{"name":"run_powershell","description":"اجرای فرمان PowerShell پس از تأیید جداگانه کاربر در رابط برنامه","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}},
]

class Agent:
    def __init__(self, config: ProviderConfig, workspace: str, approval_callback):
        self.config = config
        self.workspace = workspace
        self.approval_callback = approval_callback
        self.tools = ToolRegistry(workspace)

    def ask(self, history: list[dict], user_text: str) -> str:
        client = make_client(self.config)
        messages = [{"role":"system","content":SYSTEM_PROMPT}, *history, {"role":"user","content":user_text}]
        for _ in range(8):
            response = client.chat.completions.create(model=self.config.model, messages=messages, tools=TOOLS, tool_choice="auto")
            msg = response.choices[0].message
            if not msg.tool_calls:
                return msg.content or "مدل پاسخ متنی برنگرداند."
            messages.append({"role":"assistant","content":msg.content, "tool_calls":[tc.model_dump(exclude_none=True) for tc in msg.tool_calls]})
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                    if name == "list_files": result = self.tools.list_files(args.get("path", "."))
                    elif name == "read_file": result = self.tools.read_file(args["path"])
                    elif name == "write_file": result = self.tools.write_file(args["path"], args["content"])
                    elif name == "run_powershell":
                        command = args["command"]
                        if not self.approval_callback(command): result = "کاربر اجرای فرمان را رد کرد؛ فرمان اجرا نشد."
                        else: result = self.tools.run_powershell(command)
                    else: result = "ابزار ناشناخته است."
                except Exception as exc:
                    result = f"خطای ابزار: {exc}"
                messages.append({"role":"tool","tool_call_id":tc.id,"content":str(result)})
        return "برای جلوگیری از حلقه طولانی، اجرای ابزارها پس از ۸ مرحله متوقف شد. لطفاً کار را به چند درخواست تقسیم کنید."
