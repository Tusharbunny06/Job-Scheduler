from typing import Any
from sqlalchemy.orm import declarative_base

class CustomBase:
    id: Any

Base = declarative_base(cls=CustomBase)
