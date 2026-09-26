"""One-time setup wizard: a small GUI so a non-technical customer can
configure .env (Power BI MCP path, AI provider keys) without hand-editing
a text file. Uses only the Python standard library (tkinter), so it needs
no extra dependency beyond what install.bat already sets up.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


def update_env_file(path: Path, updates: dict[str, str]) -> None:
    """Rewrites only the given keys, preserving comments and existing order."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        new_lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            new_lines.append(f"{key}={value}")
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main() -> None:
    if not ENV_PATH.exists() and ENV_EXAMPLE_PATH.exists():
        ENV_PATH.write_text(ENV_EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    current = read_env(ENV_PATH)

    root = tk.Tk()
    root.title("إعداد قرار (Qrar) - أول تشغيل")
    root.geometry("580x420")

    fields: dict[str, tk.StringVar] = {}

    def add_row(row: int, label: str, key: str, default: str = "", browse: bool = False) -> None:
        var = tk.StringVar(value=current.get(key, default))
        fields[key] = var
        ttk.Label(root, text=label).grid(row=row, column=0, sticky="w", padx=10, pady=6)
        entry = ttk.Entry(root, textvariable=var, width=42)
        entry.grid(row=row, column=1, padx=5, pady=6)
        if browse:

            def pick() -> None:
                path = filedialog.askopenfilename(
                    title=label, filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
                )
                if path:
                    var.set(path)

            ttk.Button(root, text="استعراض...", command=pick).grid(row=row, column=2, padx=5)

    ttk.Label(
        root,
        text="أدخل إعدادات الاتصال. يمكنك تعديلها لاحقاً بإعادة تشغيل هذا المعالج،\n"
        "أو بتعديل ملف .env مباشرة.",
        justify="right",
    ).grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 15))

    add_row(1, "مسار powerbi-modeling-mcp.exe:", "POWERBI_MCP_PATH", browse=True)
    add_row(2, "عنوان خادم Ollama:", "OLLAMA_BASE_URL", "http://localhost:11434")
    add_row(3, "اسم نموذج Ollama:", "OLLAMA_MODEL", "llama3")
    add_row(4, "مفتاح OpenAI (اختياري):", "OPENAI_API_KEY")
    add_row(5, "مفتاح Gemini (اختياري):", "GEMINI_API_KEY")
    add_row(6, "ترتيب المزودين (Fallback):", "PROVIDER_ORDER", "ollama,openai,gemini")

    def save_and_close() -> None:
        updates = {key: var.get().strip() for key, var in fields.items()}
        mcp_path = updates.get("POWERBI_MCP_PATH", "")
        if mcp_path and not Path(mcp_path).exists():
            if not messagebox.askyesno(
                "تنبيه",
                "لم يتم العثور على الملف في المسار المحدد لـ powerbi-modeling-mcp.exe.\n"
                "يمكنك المتابعة وضبطه لاحقاً، لكن التطبيق لن يعمل بدونه.\n"
                "هل تريد الحفظ والمتابعة؟",
            ):
                return
        update_env_file(ENV_PATH, updates)
        messagebox.showinfo("تم", "تم حفظ الإعدادات بنجاح. يمكنك الآن إغلاق هذه النافذة.")
        root.destroy()

    ttk.Button(root, text="حفظ ومتابعة", command=save_and_close).grid(
        row=7, column=0, columnspan=3, pady=25
    )

    root.mainloop()


if __name__ == "__main__":
    main()
