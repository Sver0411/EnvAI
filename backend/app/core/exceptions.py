from typing import Any


class ApiError(Exception):
    """业务异常。code 为业务错误码（非 0），message 为人类可读信息。"""

    def __init__(self, code: int, message: str, *, detail: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


class NotFoundError(ApiError):
    def __init__(self, message: str = "资源不存在", *, detail: Any = None) -> None:
        super().__init__(404, message, detail=detail)


class AuthError(ApiError):
    def __init__(self, message: str = "认证失败", *, detail: Any = None) -> None:
        super().__init__(401, message, detail=detail)


class ForbiddenError(ApiError):
    def __init__(self, message: str = "无权限操作", *, detail: Any = None) -> None:
        super().__init__(403, message, detail=detail)


class ConflictError(ApiError):
    def __init__(self, message: str = "资源冲突", *, detail: Any = None) -> None:
        super().__init__(409, message, detail=detail)


class ValidationError(ApiError):
    def __init__(self, message: str = "参数校验失败", *, detail: Any = None) -> None:
        super().__init__(422, message, detail=detail)


class QuotaExceededError(ApiError):
    def __init__(self, message: str = "组织资源额度已达到上限", *, detail: Any = None) -> None:
        super().__init__(429, message, detail=detail)
