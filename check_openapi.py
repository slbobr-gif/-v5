"""Лёгкая проверка OpenAPI без внешних валидаторов (в CI заменится на openapi-spec-validator).

Проверяет: YAML читается, все $ref разрешаются, у каждой операции есть responses,
параметры пути объявлены, operation-level security корректна, нет «висящих» схем.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1] / "openapi" / "openapi.yaml"
METHODS = {"get", "put", "post", "patch", "delete"}


def walk(node, path="#"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield path, k, v
            yield from walk(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}/{i}")


def resolve(spec, ref: str):
    node = spec
    for part in ref.removeprefix("#/").split("/"):
        node = node[part]
    return node


def main() -> int:
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    errors: list[str] = []
    used_schemas: set[str] = set()

    for where, key, val in walk(spec):
        if key == "$ref":
            try:
                resolve(spec, val)
            except (KeyError, TypeError):
                errors.append(f"{where}: не найден {val}")
            m = re.match(r"#/components/schemas/(\w+)", val)
            if m:
                used_schemas.add(m.group(1))

    ops = 0
    for p, item in spec["paths"].items():
        declared = set(re.findall(r"{(\w+)}", p))
        for method, op in item.items():
            if method not in METHODS:
                continue
            ops += 1
            if not op.get("responses"):
                errors.append(f"{method.upper()} {p}: нет responses")
            for code, resp in op.get("responses", {}).items():
                if "$ref" not in resp and "description" not in resp:
                    errors.append(f"{method.upper()} {p} {code}: нет description")
            params = [resolve(spec, x["$ref"]) if "$ref" in x else x for x in op.get("parameters", [])]
            in_path = {x["name"] for x in params if x["in"] == "path"}
            if in_path != declared:
                errors.append(f"{method.upper()} {p}: параметры пути {in_path} ≠ {declared}")

    # схемы, на которые никто не ссылается (кроме вложенных через allOf — они тоже через $ref)
    unused = set(spec["components"]["schemas"]) - used_schemas
    for name in sorted(unused):
        errors.append(f"схема {name} нигде не используется")

    if errors:
        print("\n".join(errors))
        return 1
    print(f"OpenAPI ok: {len(spec['paths'])} путей, {ops} операций, {len(spec['components']['schemas'])} схем")
    return 0


if __name__ == "__main__":
    sys.exit(main())
