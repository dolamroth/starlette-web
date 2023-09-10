from starlette_web.common.utils.choices import TextChoices


def test_choices_values_and_labels():
    class ChoicesA(TextChoices):
        KEY_A = "value1", "label1"
        KEY_B = "value2", "label2"
        KEY_C = "value3"

    assert ChoicesA.labels == ["label1", "label2", "Key C"]
    assert ChoicesA.values == ["value1", "value2", "value3"]
    assert ChoicesA.choices == [("value1", "label1"), ("value2", "label2"), ("value3", "Key C")]
