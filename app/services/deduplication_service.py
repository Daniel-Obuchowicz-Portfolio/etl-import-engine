from app.models.customer import Customer
from app.models.import_job import DuplicateStrategy


class DeduplicationService:
    def decision(self, existing: Customer | None, strategy: DuplicateStrategy) -> str:
        if existing is None:
            return "insert"
        return strategy.value
