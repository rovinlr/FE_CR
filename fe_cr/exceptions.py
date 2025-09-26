"""Excepciones personalizadas para el módulo de facturación electrónica."""


class ValidationError(ValueError):
    """Error lanzado cuando los datos no cumplen con la especificación v4.4."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field

    def __reduce__(self):  # pragma: no cover - compatibilidad pickle
        return (self.__class__, (str(self),), {"field": self.field})
