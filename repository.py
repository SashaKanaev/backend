class PredictionRepository:
    """Учебное хранилище в памяти; при перезапуске результаты теряются."""

    def __init__(self) -> None:
        self._predictions: dict[int, bool] = {}

    def save_prediction(self, item_id: int, has_violation: bool) -> None:
        self._predictions[item_id] = has_violation

    def get_prediction(self, item_id: int) -> bool | None:
        return self._predictions.get(item_id)
