from app.services.mapping_service import MappingService
from app.services.transformation_service import TransformationService
from app.services.validation_service import ValidationService


def test_mapping_is_dynamic() -> None:
    result = MappingService().apply(
        {"legacy_contact": "Jan", "legacy_mail": "JAN@EXAMPLE.COM"},
        {"legacy_contact": "full_name", "legacy_mail": "email"},
    )
    assert result == {"full_name": "Jan", "email": "JAN@EXAMPLE.COM"}


def test_transformations_normalize_strings_email_phone_and_company() -> None:
    result = TransformationService().transform(
        {
            "full_name": "  Jan   Kowalski ",
            "email": "  JAN@EXAMPLE.COM ",
            "phone": "+48 (111) 222-333",
            "company_name": " Example  Sp. z o. o. ",
            "empty": "   ",
        }
    )
    assert result["full_name"] == "Jan Kowalski"
    assert result["email"] == "jan@example.com"
    assert result["phone"] == "+48111222333"
    assert result["company_name"] == "Example Sp.z o.o."
    assert result["empty"] is None


def test_validation_reports_invalid_email_and_required_name() -> None:
    _, errors = ValidationService().validate({"full_name": "", "email": "jan@"})
    assert {error["field"] for error in errors} == {"full_name", "email"}
