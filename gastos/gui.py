import tkinter as tk
from tkinter import filedialog, messagebox

def create_main_window(process_file_callback):
    root = tk.Tk()
    root.title("Bank Records Processor")
    root.geometry("700x300")

    tk.Label(root, text="Select Bank:").pack(pady=10)
    bank_var = tk.StringVar(value="BBVA")
    bank_menu = tk.OptionMenu(root, bank_var, "BBVA", "Laboral Kutxa")
    bank_menu.pack(pady=10)

    status_label = tk.Label(root, text="", fg="blue", wraplength=650, anchor="w", justify="left")
    status_label.pack(pady=10, fill="x")

    def select_file():
        file_path = filedialog.askopenfilename()
        if file_path:
            process_file_callback(bank_var.get(), file_path, status_label)
        else:
            messagebox.showwarning("No file selected", "Please select a file to process.")

    tk.Button(root, text="Select File", command=select_file).pack(pady=20)
    return root