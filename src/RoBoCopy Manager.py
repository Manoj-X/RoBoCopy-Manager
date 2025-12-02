import os
import subprocess
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_DIR = Path.home() / ".robocopy_gui"
LOGS_DIR = APP_DIR / "logs"
APP_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


class RobocopyGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RoBoCopy Manager")
        self.geometry("550x500")
        self.process = None
        self._starting = False
        self.var_R = 1
        self.var_W = 1
        self.var_MT = 32
        # sources: list of dicts {"kind":"folder"|"files", "path":..., "files":[...]}
        self.sources = []
        self.dst_var = tk.StringVar()
        self._build_ui()

    def _build_ui(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(frm)
        top.pack(fill=tk.X)
        ttk.Label(top, text="Selected sources:", width=18).pack(side=tk.LEFT)
        self.sources_box = tk.Listbox(top, height=7)
        self.sources_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        col = ttk.Frame(top)
        col.pack(side=tk.LEFT)
        ttk.Button(col, text="Add Folder...", command=self._add_folder_native).pack(fill=tk.X, pady=2)
        ttk.Button(col, text="Add Files...", command=self._add_files_native).pack(fill=tk.X, pady=2)
        ttk.Button(col, text="Remove", command=self._remove).pack(fill=tk.X, pady=2)
        ttk.Button(col, text="Clear", command=self._clear).pack(fill=tk.X, pady=2)

        dst_row = ttk.Frame(frm)
        dst_row.pack(fill=tk.X, pady=8)
        ttk.Label(dst_row, text="Destination:", width=18).pack(side=tk.LEFT)
        ttk.Entry(dst_row, textvariable=self.dst_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dst_row, text="Browse", command=self._browse_dst).pack(side=tk.LEFT, padx=6)

        tip = ("Tip: Add files — multiple selections supported.\n"
               "Tip:Preset options used: /E /MT:32 /R:1 /W:1"
        )
        ttk.Label(frm, text=tip).pack(fill=tk.X, pady=6)

        ctrl = ttk.Frame(frm)
        ctrl.pack(fill=tk.X)
        self.preview_btn = ttk.Button(ctrl, text="Preview", command=self._preview)
        self.preview_btn.pack(side=tk.LEFT)
        self.run_btn = ttk.Button(ctrl, text="Run", command=self._run)
        self.run_btn.pack(side=tk.LEFT, padx=6)
        self.stop_btn = ttk.Button(ctrl, text="Stop", command=self._stop)
        self.stop_btn.pack(side=tk.LEFT)
        self.save_btn = ttk.Button(ctrl, text="Save Log", command=self._save_log)
        self.save_btn.pack(side=tk.LEFT, padx=6)
        self.open_logs_btn = ttk.Button(ctrl, text="Open Logs", command=self._open_logs)
        self.open_logs_btn.pack(side=tk.LEFT)

        out = ttk.LabelFrame(frm, text="Output")
        out.pack(fill=tk.BOTH, expand=True, pady=8)
        self.txt = tk.Text(out)
        self.txt.pack(fill=tk.BOTH, expand=True)

        # use keyword 'value' for initial StringVar value
        self.status = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status, relief=tk.SUNKEN).pack(fill=tk.X, side=tk.BOTTOM)

    # ---------------- Native add folder (single folder per dialog) ----------------
    def _add_folder_native(self):
        folder = filedialog.askdirectory(title="Select folder to add (native dialog)")
        if not folder:
            return
        folder = os.path.normpath(folder)
        # avoid duplicates
        if any(s["kind"] == "folder" and s["path"] == folder for s in self.sources):
            messagebox.showinfo("Already added", "That folder is already selected.")
            return
        self.sources.append({"kind": "folder", "path": folder, "files": []})
        self._refresh_sources()

    # ---------------- Native add files (can multi-select via native dialog) ----------------
    def _add_files_native(self):
        files = filedialog.askopenfilenames(title="Select files (use Ctrl+A/Ctrl-click/Shift-click to select multiple)")
        if not files:
            return
        files = [os.path.normpath(f) for f in files]
        parents = {os.path.dirname(f) for f in files}
        if len(parents) > 1:
            # Shouldn't happen with a single askopenfilenames call, but check defensively
            messagebox.showerror("Error", "Please select files from only one folder at a time.")
            return
        parent = parents.pop()
        names = sorted(files)
        # Avoid duplicate identical file-groups
        for s in self.sources:
            if s["kind"] == "files" and sorted(s["files"]) == names:
                messagebox.showinfo("Already added", "These files are already in the selection list.")
                return
        self.sources.append({"kind": "files", "path": parent, "files": files})
        self._refresh_sources()

    # ---------------- Remove / Clear ----------------
    def _remove(self):
        sel = self.sources_box.curselection()
        if not sel:
            return
        for i in reversed(sel):
            del self.sources[i]
        self._refresh_sources()

    def _clear(self):
        if not self.sources:
            return
        if not messagebox.askyesno("Clear all", "Remove all selected sources?"):
            return
        self.sources.clear()
        self._refresh_sources()

    def _refresh_sources(self):
        self.sources_box.delete(0, tk.END)
        for s in self.sources:
            if s["kind"] == "folder":
                self.sources_box.insert(tk.END, f"[FOLDER] {s['path']}")
            else:
                self.sources_box.insert(tk.END, f"[FILES] {s['path']} → {len(s['files'])} file(s)")

    # ---------------- Destination browse ----------------
    def _browse_dst(self):
        d = filedialog.askdirectory(title="Select destination folder")
        if d:
            self.dst_var.set(os.path.normpath(d))

    # ---------------- Build robocopy commands ----------------
    def _quote(self, s):
        if " " in s or "\t" in s:
            return f'"{s}"'
        return s

    def _build_all_commands(self):
        dst = self.dst_var.get().strip()
        if not dst:
            raise ValueError("Destination must be set")
        if not self.sources:
            raise ValueError("No sources selected")
        cmds = []
        for s in self.sources:
            if s["kind"] == "folder":
                src = s["path"]
                final_dst = os.path.join(dst, os.path.basename(src))
                cmd = ["robocopy", src, final_dst, "*.*", "/E", f"/MT:{int(self.var_MT)}", f"/R:{int(self.var_R)}", f"/W:{int(self.var_W)}"]
                cmds.append((cmd, f"Folder copy: {src} -> {final_dst}"))
            else:
                parent = s["path"]
                file_filters = [os.path.basename(f) for f in s["files"]]
                cmd = ["robocopy", parent, dst] + file_filters + ["/E", f"/MT:{int(self.var_MT)}", f"/R:{int(self.var_R)}", f"/W:{int(self.var_W)}"]
                cmds.append((cmd, f"Files copy: {len(s['files'])} files from {parent} -> {dst}"))
        return cmds

    # ---------------- Preview / Run ----------------
    def _preview(self):
        try:
            cmds = self._build_all_commands()
        except Exception as e:
            messagebox.showerror("Preview error", str(e))
            return
        self._append("Previewing commands:\n")
        for cmd, desc in cmds:
            self._append(desc + "\n")
            self._append("  " + " ".join(self._quote(c) for c in cmd) + "\n")
        self._append("\n")

    def _run(self):
        try:
            cmds = self._build_all_commands()
        except Exception as e:
            messagebox.showerror("Run error", str(e))
            return
        if not messagebox.askyesno("Confirm run", f"About to run {len(cmds)} robocopy operation(s). Proceed?"):
            return
        self._starting = True
        try:
            self.run_btn.config(state=tk.DISABLED)
            self.preview_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        except Exception:
            pass
        logfile = LOGS_DIR / f"robocopy_{int(time.time())}.log"
        self.status.set("Running...")
        self._append(f"Running {len(cmds)} operation(s)...\n")

        def target():
            try:
                for i, (cmd, desc) in enumerate(cmds, start=1):
                    self._append(f"\nOperation {i}/{len(cmds)}: {desc}\n")
                    self._append("  " + " ".join(self._quote(c) for c in cmd) + "\n")
                    startupinfo = None
                    creationflags = 0
                    if os.name == 'nt':
                        try:
                            creationflags = subprocess.CREATE_NO_WINDOW
                        except Exception:
                            creationflags = 0
                    self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, startupinfo=startupinfo, creationflags=creationflags, shell=False)
                    with open(logfile, 'a', encoding='utf-8') as f:
                        f.write(f"\n=== Operation {i}: {desc} ===\n")
                        for line in self.process.stdout:
                            f.write(line)
                            f.flush()
                            self._append(line)
                    ret = self.process.wait()
                    self._append(f"Operation {i} exited with code {ret}\n")
                    self.process = None
                    if not self._starting:
                        self._append("Stopped by user — remaining operations cancelled.\n")
                        break
                self._append("All operations finished.\n")
            except Exception as e:
                self._append(f"Error running operations: {e}\n")
            finally:
                self.process = None
                self._starting = False
                self.status.set("Ready")
                try:
                    self.run_btn.config(state=tk.NORMAL)
                    self.preview_btn.config(state=tk.NORMAL)
                    self.stop_btn.config(state=tk.DISABLED)
                except Exception:
                    pass

        threading.Thread(target=target, daemon=True).start()

    # ---------------- Stop ----------------
    def _stop(self):
        if not getattr(self, "process", None):
            if self._starting:
                self._starting = False
                self._append("Stop requested — will stop after current operation.\n")
                return
            messagebox.showinfo("Not running", "No robocopy process is currently running.")
            return
        try:
            self.process.terminate()
            self._append("Sent terminate signal to current robocopy process\n")
        except Exception as e:
            messagebox.showerror("Stop error", f"Failed to stop process: {e}")

    # ---------------- logs / helpers ----------------
    def _save_log(self):
        p = filedialog.asksaveasfilename(defaultextension=".log")
        if not p:
            return
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.txt.get("1.0", tk.END))
        messagebox.showinfo("Saved", f"Saved to {p}")

    def _open_logs(self):
        try:
            if os.name == 'nt':
                os.startfile(str(LOGS_DIR))
            elif os.name == 'posix':
                subprocess.Popen(['xdg-open', str(LOGS_DIR)])
            else:
                messagebox.showinfo("Logs folder", str(LOGS_DIR))
        except Exception:
            messagebox.showinfo("Logs folder", str(LOGS_DIR))

    def _append(self, text):
        try:
            self.txt.insert(tk.END, text)
            self.txt.see(tk.END)
        except Exception:
            pass


if __name__ == "__main__":
    app = RobocopyGUI()
    app.mainloop()
