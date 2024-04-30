from web.form import Form, Input, Validator


def test_form_validators():
    field_validator_name = "field should not be empty"
    field_validator = Validator(field_validator_name, lambda x: len(x) > 0)
    field = Input("field", field_validator)

    res = field.validate("")
    assert not res, "empty field should not validate"
    assert field.note == field_validator_name, "failing field should be in note"

    form_validator = Validator("form field should not be empty", lambda x: True)
    form = Form(field, validators=[form_validator])
    res = form.validates(source={"field": ""})
    assert not res, "form should not validate with empty field"
    assert (
        form.note == field_validator_name
    ), "failing field note should propagate to form note"
