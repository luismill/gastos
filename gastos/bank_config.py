class BankConfig:
    def __init__(self, bank):
        self.bank = bank
        self.file_format = None
        self.column_names = []

        self.set_config()

    def set_config(self):
        if self.bank == "Laboral Kutxa":
            self.file_format = "csv"
            self.column_names = ["Fecha valor", "Concepto", "Importe"]
        elif self.bank == "BBVA":
            self.file_format = "xlsx"
            self.column_names = ["F.Valor", "Concepto", "Importe"]
        else:
            raise ValueError("Unsupported bank")