import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import logging
import threading
import queue
import os
from src.services.processor import TransactionProcessor, ProcessorResult
from src.services.exporter import ExporterService
from src.services.notion_service import NotionClient
from src.extractors.laboral_kutxa import LaboralKutxaParser
from src.extractors.revolut import RevolutParser
from src.extractors.bbva import BBVAParser

logger = logging.getLogger(__name__)

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Gastos Notion (Refactorizado)")
        self.root.geometry("600x500")

        self.queue = queue.Queue()
        self._check_queue()

        # Initialize Services
        try:
            self.notion_client = NotionClient()
            self.processor = TransactionProcessor(self.notion_client)
            self.exporter = ExporterService(self.notion_client)
        except Exception as e:
            messagebox.showerror("Error de Configuración", f"No se pudo iniciar el cliente de Notion: {e}\nRevisa tu archivo .env")
            self.notion_client = None

        self._init_ui()

    def _check_queue(self):
        """Check the queue for tasks to run on the main thread."""
        try:
            while True:
                task = self.queue.get_nowait()
                func = task[0]
                args = task[1:]
                func(*args)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._check_queue)

    def _init_ui(self):
        # Frame Principal
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Label
        lbl_instr = tk.Label(main_frame, text="Selecciona el banco y el archivo para procesar:")
        lbl_instr.pack(pady=(0, 10))

        # Botones de Bancos
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(pady=10)

        self.banks = {
            "Laboral Kutxa": LaboralKutxaParser,
            "Revolut": RevolutParser,
            "BBVA": BBVAParser
        }

        for bank_name in self.banks:
            btn = tk.Button(btn_frame, text=bank_name, command=lambda b=bank_name: self.on_bank_select(b))
            btn.pack(side=tk.LEFT, padx=5)

        # Separator
        tk.Frame(main_frame, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, pady=20)

        # Export Buttons
        export_frame = tk.Frame(main_frame)
        export_frame.pack(pady=10)

        btn_export = tk.Button(export_frame, text="Exportar Notion a CSV", command=self.on_export)
        btn_export.pack(side=tk.LEFT, padx=5)

        btn_cat = tk.Button(export_frame, text="Exportar Categorías", command=self.on_export_categories)
        btn_cat.pack(side=tk.LEFT, padx=5)

        # Status / Log Area
        self.status_label = tk.Label(main_frame, text="Listo.", fg="blue")
        self.status_label.pack(pady=(10, 5))

        self.log_text = scrolledtext.ScrolledText(main_frame, height=10, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        """Thread-safe logging to UI."""
        self.queue.put((self._log_internal, message))

    def _log_internal(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        logging.info(message)

    def update_status(self, text, color="black"):
        """Thread-safe status update."""
        self.queue.put((self._update_status_internal, text, color))

    def _update_status_internal(self, text, color):
        self.status_label.config(text=text, fg=color)

    def show_message(self, type_, title, message):
        """Thread-safe message box."""
        self.queue.put((self._show_message_internal, type_, title, message))

    def _show_message_internal(self, type_, title, message):
        if type_ == "info":
            messagebox.showinfo(title, message)
        elif type_ == "error":
            messagebox.showerror(title, message)
        elif type_ == "warning":
            messagebox.showwarning(title, message)

    def on_bank_select(self, bank_name):
        if not self.notion_client:
            self.show_message("error", "Error", "Cliente Notion no inicializado.")
            return

        file_path = filedialog.askopenfilename(title=f"Selecciona archivo de {bank_name}")
        if not file_path:
            return

        threading.Thread(target=self.process_thread, args=(bank_name, file_path)).start()

    def process_thread(self, bank_name, file_path):
        self.update_status(f"Procesando {bank_name}...", "orange")
        self.log(f"--- Iniciando proceso para {bank_name} ---")

        try:
            parser_cls = self.banks[bank_name]
            parser = parser_cls()

            result = self.processor.process_file(file_path, parser)

            self.log(f"Resultados: {result.to_string()}")
            if result.errors:
                self.log("Errores encontrados:")
                for err in result.errors:
                    self.log(f" - {err}")

            self.update_status("Proceso finalizado.", "green")
            self.show_message("info", "Proceso finalizado", result.to_string())

        except Exception as e:
            self.log(f"Error crítico: {e}")
            self.update_status("Error.", "red")
            self.show_message("error", "Error", str(e))

    def on_export(self):
        if not self.notion_client: return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not file_path: return

        threading.Thread(target=self.export_thread, args=(file_path,)).start()

    def export_thread(self, file_path):
        self.update_status("Exportando...", "orange")
        self.log("Iniciando exportación...")
        if self.exporter.export_all_to_csv(file_path):
            self.log(f"Exportación exitosa en {file_path}")
            self.update_status("Exportación OK", "green")
        else:
            self.log("Falló la exportación.")
            self.update_status("Error exportación", "red")

    def on_export_categories(self):
        if not self.notion_client: return
        cat_db_id = os.environ.get("NOTION_CATEGORY_DATABASE_ID")
        if not cat_db_id:
            messagebox.showwarning("Falta Config", "No se definió NOTION_CATEGORY_DATABASE_ID en .env")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], initialfile="subcategorias.csv")
        if not file_path: return

        threading.Thread(target=self.export_categories_thread, args=(file_path, cat_db_id)).start()

    def export_categories_thread(self, file_path, cat_db_id):
        self.update_status("Exportando categorías...", "orange")
        if self.exporter.export_categories_to_csv(file_path, cat_db_id):
            self.log(f"Categorías exportadas en {file_path}")
            self.update_status("Exportación OK", "green")
        else:
            self.log("Falló la exportación de categorías.")
            self.update_status("Error exportación", "red")

def create_main_window():
    root = tk.Tk()
    app = AppGUI(root)
    return root
