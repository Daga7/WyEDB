"""Tipo `Result[T]` para manejo explícito de errores (estilo Railway Oriented).

Permite que las funciones devuelvan un éxito (`Ok`) o un fallo (`Err`) sin lanzar
excepciones, de modo que el flujo principal pueda decidir qué hacer con cada error
y **continuar procesando** el resto (requisito de robustez del proyecto).

Ejemplo
-------
    def dividir(a: int, b: int) -> Result[float]:
        if b == 0:
            return Err("No se puede dividir por cero")
        return Ok(a / b)

    r = dividir(10, 2)
    if r.is_ok():
        print(r.unwrap())          # 5.0
    else:
        print(r.error)             # mensaje de error
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Resultado exitoso que envuelve un valor."""

    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        """Devuelve el valor contenido."""
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value

    @property
    def error(self) -> str | None:
        return None


@dataclass(frozen=True, slots=True)
class Err:
    """Resultado fallido que envuelve un mensaje de error.

    Opcionalmente conserva la excepción original para diagnóstico/logging.
    """

    error: str
    exception: Exception | None = None

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> object:
        """Lanza un error: no se debe desempaquetar un `Err`."""
        raise ValueError(f"Se intentó desempaquetar un Err: {self.error}")

    def unwrap_or(self, default: U) -> U:
        return default

    @property
    def value(self) -> None:
        return None


# Un `Result[T]` es un `Ok[T]` o un `Err`.
Result = Ok[T] | Err
