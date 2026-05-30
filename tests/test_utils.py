from io import BytesIO

from multipart import parse_form_data

from web import utils


def test_group():
    assert list(utils.group([], 2)) == []
    assert list(utils.group([1, 2, 3, 4, 5, 6, 7, 8, 9], 3)) == [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
    ]
    assert list(utils.group([1, 2, 3, 4, 5, 6, 7, 8, 9], 4)) == [
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9],
    ]


class TestIterBetter:
    def test_iter(self):
        assert list(utils.IterBetter(iter([]))) == []
        assert list(utils.IterBetter(iter([1, 2, 3]))) == [1, 2, 3]


class TestStorify:
    def test_storify_with_non_files(self):
        assert utils.storify({"a": [1, 2]}).a == 2
        assert utils.storify({"a": [1, 2]}, a=[]).a == [1, 2]
        assert utils.storify({"a": 1}, a=[]).a == [1]
        assert utils.storify({}, a=[]).a == []

    def test_storify_with_a_unicode_file_value(self):
        assert utils.storify({"a": utils.storage(value=1)}).a == 1
        assert utils.storify({}, a={}).a == {}

        result = utils.storify({"a": utils.storage(value=1)}, a={}).a
        assert type(result) is utils.storage
        assert result.value == 1

    def test_storify_with_a_binary_file_value(self):
        # Prepare some raw multipart data with a binary file attachment
        binary_file_content = b"\x01\x02\x03\x04\x05"
        raw_data = (
            b"""--boundary\r
Content-Disposition: form-data; name="field1"\r
\r
value1\r
--boundary\r
Content-Disposition: form-data; name="field2"\r
\r
value2\r
--boundary\r
Content-Disposition: form-data; name="file"; filename="example.bin"\r
Content-Type: application/octet-stream\r
\r
"""
            + binary_file_content
            + b"\r\n--boundary--\r\n"
        )

        # Create a BytesIO object from the raw data
        buffer = BytesIO(raw_data)

        # Parse the multipart data
        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": "multipart/form-data; boundary=boundary",
            "CONTENT_LENGTH": str(len(raw_data)),
            "wsgi.input": buffer,
        }

        _, files = parse_form_data(environ)

        # Check if 'file' and 'raw' attributes exist
        file_obj = files.get("file")
        assert hasattr(file_obj, "file")
        assert hasattr(file_obj, "raw")

        # Ensure binary content matches.
        result = utils.storify({"files": file_obj})
        assert result.files == binary_file_content
