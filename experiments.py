from dataclasses import asdict
from dataclasses import is_dataclass

from pydantic.dataclasses import dataclass
from pydantic.dataclasses import is_pydantic_dataclass


@dataclass
class A:
    a: int = None


@dataclass
class B:
    b: int = None
    c: A = None


tester = B(b=1, c=A(a=2))

d = asdict(tester)
print(d)
print(tester)

tester2 = B(**d)
print(tester2)

print(is_dataclass(B))
print(is_pydantic_dataclass(B))

print(dir(B))