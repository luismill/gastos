import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def create_main_window(process_file_callback: callable, export_callback: callable, export_subcategorias_callback: callable) -> tk.Tk:
    root = tk.Tk()
    root.title("Procesador de gastos")
    root.geometry("700x350")

    # Estilos
    style = ttk.Style()
    style.configure("Title.TLabel", font=("Arial", 18, "bold"))
    style.configure("Status.TLabel", foreground="blue", wraplength=650, anchor="w", justify="left")

    # Título grande
    ttk.Label(root, text="Procesador de Gastos", style="Title.TLabel").pack(pady=10)

    # Separador
    ttk.Separator(root, orient="horizontal").pack(fill="x", padx=10, pady=5)

    # Frame para seleccionar el banco
    bank_frame = ttk.Frame(root)
    bank_frame.pack(pady=10)

    ttk.Label(bank_frame, text="Selecciona el banco:").grid(row=0, column=0, padx=(0, 10), sticky="e")
    bank_var = tk.StringVar()
    bank_menu = ttk.OptionMenu(bank_frame, bank_var, None, "BBVA", "Laboral Kutxa", "Revolut")
    bank_menu.grid(row=0, column=1, sticky="w")

    # Centrar el frame manualmente
    bank_frame.pack(anchor="center", pady=10)

    def select_file():
        file_path = filedialog.askopenfilename()
        if file_path:
            if not bank_var.get():
                messagebox.showwarning(
                    "Banco no seleccionado",
                    "Por favor, selecciona un banco antes de procesar el fichero."
                )
                return
            process_file_callback(bank_var.get(), file_path, status_label)
        else:
            messagebox.showwarning(
                "Ningún fichero seleccionado",
                "Por favor, selecciona un fichero para procesar."
            )

    def export_notion():
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")]
        )
        if file_path:
            export_callback(file_path, status_label)
        else:
            messagebox.showwarning(
                "Ningún fichero seleccionado",
                "Por favor, selecciona un fichero para guardar."
            )

    ttk.Button(root, text="Seleccionar fichero", command=select_file).pack(pady=20)
    ttk.Button(root, text="Exportar Notion a CSV", command=export_notion).pack()
    ttk.Button(root, text="Exportar subcategorías a CSV", command=lambda: export_subcategorias_callback(None, status_label)).pack(pady=5)

    status_label = ttk.Label(root, text="", style="Status.TLabel")
    status_label.pack(pady=10, fill="x")
    return root
