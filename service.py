from repository import PredictionRepository


class ModerationService:
    def __init__(self, repository: PredictionRepository) -> None:
        self.repository = repository

    def predict(self, item_id: int, is_verified_seller: bool, images_qty: int) -> bool:
        has_violation = not is_verified_seller and images_qty == 0
        self.repository.save_prediction(item_id, has_violation)
        return has_violation
