from __future__ import annotations

import json
from pathlib import Path
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback


APP_TITLE = "微信聊天记录导出器"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
USER_HOME = Path.home()
PYTHON = USER_HOME / "AppData/Local/wechat-chat-export/venv/Scripts/python.exe"
REPOSITORY_ROOT = Path(__file__).resolve().parent
LOCAL_EXPORTER = REPOSITORY_ROOT / "scripts/export_wechat.py"
INSTALLED_EXPORTER = USER_HOME / ".codex/skills/wechat-chat-export/scripts/export_wechat.py"
EXPORTER = LOCAL_EXPORTER if LOCAL_EXPORTER.is_file() else INSTALLED_EXPORTER
DEFAULT_DATA_ROOT = USER_HOME / "Documents/xwechat_files"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "导出结果"


class ExporterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x680")
        self.minsize(760, 560)
        self.chats: list[dict] = []
        self.account_paths: dict[str, Path] = {}
        self._build_ui()
        self._discover_accounts()
        self._validate_installation()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        account_box = ttk.LabelFrame(self, text="1. 微信账号")
        account_box.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        account_box.columnconfigure(1, weight=1)
        ttk.Label(account_box, text="数据目录").grid(row=0, column=0, padx=8, pady=8)
        self.account_var = tk.StringVar()
        self.account_combo = ttk.Combobox(account_box, textvariable=self.account_var, state="readonly")
        self.account_combo.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        ttk.Button(account_box, text="刷新账号", command=self._discover_accounts).grid(row=0, column=2, padx=8, pady=8)

        search_box = ttk.LabelFrame(self, text="2. 搜索并选择会话（本步不读取正文）")
        search_box.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        search_box.columnconfigure(1, weight=1)
        ttk.Label(search_box, text="关键词").grid(row=0, column=0, padx=8, pady=8)
        self.keyword_var = tk.StringVar()
        keyword_entry = ttk.Entry(search_box, textvariable=self.keyword_var)
        keyword_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        keyword_entry.bind("<Return>", lambda _event: self.search_chats())
        self.search_button = ttk.Button(search_box, text="列出会话", command=self.search_chats)
        self.search_button.grid(row=0, column=2, padx=8, pady=8)

        chat_box = ttk.Frame(self)
        chat_box.grid(row=2, column=0, sticky="nsew", padx=12, pady=6)
        chat_box.columnconfigure(0, weight=1)
        chat_box.rowconfigure(0, weight=1)
        self.chat_list = tk.Listbox(chat_box, selectmode=tk.EXTENDED, exportselection=False, font=("Microsoft YaHei UI", 10))
        self.chat_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(chat_box, orient="vertical", command=self.chat_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_list.configure(yscrollcommand=scrollbar.set)

        settings = ttk.LabelFrame(self, text="3. 导出设置")
        settings.grid(row=3, column=0, sticky="ew", padx=12, pady=6)
        settings.columnconfigure(5, weight=1)

        self.range_mode = tk.StringVar(value="recent")
        ttk.Radiobutton(settings, text="最近", variable=self.range_mode, value="recent", command=self._toggle_time_fields).grid(row=0, column=0, padx=(8, 2), pady=6)
        self.amount_var = tk.StringVar(value="60")
        self.amount_entry = ttk.Entry(settings, textvariable=self.amount_var, width=8)
        self.amount_entry.grid(row=0, column=1, padx=2, pady=6)
        self.unit_var = tk.StringVar(value="分钟")
        self.unit_combo = ttk.Combobox(settings, textvariable=self.unit_var, values=("分钟", "小时", "天"), state="readonly", width=6)
        self.unit_combo.grid(row=0, column=2, padx=2, pady=6)
        ttk.Radiobutton(settings, text="全部历史", variable=self.range_mode, value="all", command=self._toggle_time_fields).grid(row=0, column=3, padx=8, pady=6)
        ttk.Radiobutton(settings, text="指定时间", variable=self.range_mode, value="custom", command=self._toggle_time_fields).grid(row=0, column=4, padx=8, pady=6)

        ttk.Label(settings, text="开始").grid(row=1, column=0, padx=8, pady=6)
        self.start_var = tk.StringVar()
        self.start_entry = ttk.Entry(settings, textvariable=self.start_var, width=22, state="disabled")
        self.start_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=2, pady=6)
        ttk.Label(settings, text="结束").grid(row=1, column=3, padx=8, pady=6)
        self.end_var = tk.StringVar()
        self.end_entry = ttk.Entry(settings, textvariable=self.end_var, width=22, state="disabled")
        self.end_entry.grid(row=1, column=4, columnspan=2, sticky="ew", padx=2, pady=6)
        ttk.Label(settings, text="格式：2026-11-01 00:00:00").grid(row=1, column=6, padx=8, pady=6)

        ttk.Label(settings, text="输出目录").grid(row=2, column=0, padx=8, pady=6)
        self.output_var = tk.StringVar(value=str(DEFAULT_OUTPUT))
        ttk.Entry(settings, textvariable=self.output_var).grid(row=2, column=1, columnspan=5, sticky="ew", padx=2, pady=6)
        ttk.Button(settings, text="浏览", command=self._choose_output).grid(row=2, column=6, padx=8, pady=6)

        action = ttk.Frame(self)
        action.grid(row=4, column=0, sticky="ew", padx=12, pady=6)
        action.columnconfigure(0, weight=1)
        self.status_var = tk.StringVar(value="准备就绪。请保持微信运行并登录。")
        ttk.Label(action, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        self.export_button = ttk.Button(action, text="开始导出", command=self.export_selected)
        self.export_button.grid(row=0, column=1, padx=(8, 0))

        log_box = ttk.LabelFrame(self, text="运行结果")
        log_box.grid(row=5, column=0, sticky="ew", padx=12, pady=(6, 12))
        log_box.columnconfigure(0, weight=1)
        self.log = tk.Text(log_box, height=8, wrap="word", state="disabled", font=("Consolas", 9))
        self.log.grid(row=0, column=0, sticky="ew", padx=6, pady=6)

    def _validate_installation(self) -> None:
        missing = [str(path) for path in (PYTHON, EXPORTER) if not path.is_file()]
        if missing:
            messagebox.showerror(APP_TITLE, "缺少后端文件：\n" + "\n".join(missing))
            self.search_button.configure(state="disabled")
            self.export_button.configure(state="disabled")

    def _discover_accounts(self) -> None:
        discovered: list[tuple[float, str, Path]] = []
        if DEFAULT_DATA_ROOT.is_dir():
            for db_dir in DEFAULT_DATA_ROOT.glob("*/db_storage"):
                if not db_dir.is_dir():
                    continue
                modified = db_dir.stat().st_mtime
                label = f"{db_dir.parent.name}  |  {db_dir}"
                discovered.append((modified, label, db_dir))
        self.account_paths = {
            label: path
            for _modified, label, path in sorted(discovered, key=lambda item: item[0], reverse=True)
        }
        labels = list(self.account_paths)
        self.account_combo.configure(values=labels)
        if labels:
            self.account_var.set(labels[0])
            self.status_var.set(f"发现 {len(labels)} 个账号目录；默认选择最近更新的账号。")
        else:
            self.account_var.set("")
            self.status_var.set("没有在 Documents/xwechat_files 下发现账号目录。")

    def _selected_account(self) -> Path | None:
        return self.account_paths.get(self.account_var.get())

    def _set_busy(self, busy: bool, message: str) -> None:
        state = "disabled" if busy else "normal"
        self.search_button.configure(state=state)
        self.export_button.configure(state=state)
        self.status_var.set(message)

    def _append_log(self, text: str, clear: bool = False) -> None:
        self.log.configure(state="normal")
        if clear:
            self.log.delete("1.0", tk.END)
        self.log.insert(tk.END, text.rstrip() + "\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def _run_backend(self, args: list[str]) -> tuple[dict, str]:
        command = [str(PYTHON), "-B", str(EXPORTER), *args]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=CREATE_NO_WINDOW,
        )
        payload = None
        for line in reversed(result.stdout.splitlines() + result.stderr.splitlines()):
            if not line.strip():
                continue
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and "status" in candidate:
                payload = candidate
                break
        if payload is None:
            payload = {"status": "failed", "reason": "后端没有返回可解析的结果"}
        details = "\n".join(part for part in (result.stderr.strip(), result.stdout.strip()) if part)
        return payload, details

    def search_chats(self) -> None:
        db_dir = self._selected_account()
        if db_dir is None:
            messagebox.showwarning(APP_TITLE, "请先选择微信账号目录。")
            return
        args = ["--db-dir", str(db_dir), "--list-chats"]
        keyword = self.keyword_var.get().strip()
        if keyword:
            args.append(keyword)
        self._set_busy(True, "正在只读扫描会话元数据……")
        self._append_log("正在列出会话；不会读取消息正文。", clear=True)

        def work() -> None:
            payload, details = self._run_backend(args)
            self.after(0, lambda: self._finish_search(payload, details))

        threading.Thread(target=work, daemon=True).start()

    def _finish_search(self, payload: dict, details: str) -> None:
        self._set_busy(False, "会话列表已更新。" if payload.get("status") == "listed" else "列出会话失败。")
        self._append_log(details or json.dumps(payload, ensure_ascii=False, indent=2), clear=True)
        if payload.get("status") != "listed":
            messagebox.showerror(APP_TITLE, payload.get("reason", "列出会话失败"))
            return
        self.chats = payload.get("chats", [])
        self.chat_list.delete(0, tk.END)
        for chat in self.chats:
            kind = "群聊" if chat.get("type") == "group" else "好友"
            self.chat_list.insert(tk.END, f"[{kind}] {chat.get('name')}    ({chat.get('username')})")
        self.status_var.set(f"找到 {len(self.chats)} 个会话。可按住 Ctrl 多选。")

    def _toggle_time_fields(self) -> None:
        custom = self.range_mode.get() == "custom"
        self.start_entry.configure(state="normal" if custom else "disabled")
        self.end_entry.configure(state="normal" if custom else "disabled")
        self.amount_entry.configure(state="normal" if self.range_mode.get() == "recent" else "disabled")
        self.unit_combo.configure(state="readonly" if self.range_mode.get() == "recent" else "disabled")

    def _time_args(self) -> list[str]:
        mode = self.range_mode.get()
        if mode == "all":
            return ["--all-history"]
        if mode == "custom":
            start = self.start_var.get().strip()
            end = self.end_var.get().strip()
            if not start:
                raise ValueError("指定时间模式必须填写开始时间。")
            args = ["--start", start]
            if end:
                args += ["--end", end]
            return args
        try:
            amount = int(self.amount_var.get())
        except ValueError as exc:
            raise ValueError("最近时间必须填写正整数。") from exc
        if amount <= 0:
            raise ValueError("最近时间必须大于 0。")
        multiplier = {"分钟": 1, "小时": 60, "天": 1440}[self.unit_var.get()]
        return ["--minutes", str(amount * multiplier)]

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_var.get() or str(DEFAULT_OUTPUT.parent))
        if selected:
            self.output_var.set(selected)

    def export_selected(self) -> None:
        indices = list(self.chat_list.curselection())
        if not indices:
            messagebox.showwarning(APP_TITLE, "请先列出会话并至少选择一个。")
            return
        db_dir = self._selected_account()
        if db_dir is None:
            messagebox.showwarning(APP_TITLE, "请先选择微信账号目录。")
            return
        output = Path(self.output_var.get().strip()).expanduser()
        try:
            time_args = self._time_args()
        except ValueError as exc:
            messagebox.showwarning(APP_TITLE, str(exc))
            return
        chat_args: list[str] = []
        selected_names: list[str] = []
        for index in indices:
            chat = self.chats[index]
            chat_args += ["--chat", chat["username"]]
            selected_names.append(chat["name"])
        args = ["--db-dir", str(db_dir), *chat_args, *time_args, "--output-root", str(output)]
        self._set_busy(True, "正在读取所选会话并导出……")
        self._append_log("即将导出：" + "、".join(selected_names), clear=True)

        def work() -> None:
            payload, details = self._run_backend(args)
            self.after(0, lambda: self._finish_export(payload, details, output))

        threading.Thread(target=work, daemon=True).start()

    def _finish_export(self, payload: dict, details: str, output: Path) -> None:
        complete = payload.get("status") == "complete"
        self._set_busy(False, "导出完成。" if complete else "导出未完成。")
        self._append_log(details or json.dumps(payload, ensure_ascii=False, indent=2), clear=True)
        if complete:
            messagebox.showinfo(APP_TITLE, f"导出完成并通过验证。\n\n输出位置：{output}")
        else:
            messagebox.showerror(APP_TITLE, payload.get("reason", "导出失败，请查看运行结果。"))


if __name__ == "__main__":
    try:
        ExporterApp().mainloop()
    except Exception:
        details = traceback.format_exc()
        log_path = Path(__file__).resolve().with_name("启动错误.log")
        log_path.write_text(details, encoding="utf-8")
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"程序启动失败，错误详情已保存到：\n{log_path}\n\n{details}",
                APP_TITLE,
                0x10,
            )
        except Exception:
            pass
