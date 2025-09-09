from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename

def validate_openapi(file_path: str):
    spec_dict, _ = read_from_filename(file_path)
    validate_spec(spec_dict)
