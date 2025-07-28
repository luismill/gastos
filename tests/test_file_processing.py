import sys, types
sys.modules["pandas"] = types.ModuleType("pandas")
from gastos.file_processing import process_gasto_ingreso

class SimpleSeries:
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name

    def apply(self, func):
        return [func(x) for x in self.parent.data[self.name]]

class SimpleDF:
    def __init__(self, data):
        self.data = {k: list(v) for k, v in data.items()}

    def __getitem__(self, key):
        return SimpleSeries(self, key)

    def __setitem__(self, key, value):
        self.data[key] = list(value)

    def drop(self, columns, inplace=True):
        for col in columns:
            self.data.pop(col, None)
        if not inplace:
            return self


def test_process_gasto_ingreso_splits_columns_and_drops():
    df = SimpleDF({"Gasto/Ingreso": [-50, 100, -20, 30]})
    result = process_gasto_ingreso(df)

    assert "Gasto/Ingreso" not in result.data
    assert result.data["Gasto"] == [50, None, 20, None]
    assert result.data["Ingreso"] == [None, 100, None, 30]
