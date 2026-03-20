"""Custom exception hierarchy for the auction platform.

All application exceptions inherit from ``AuctionPlatformException``,
which carries a machine-readable ``code``, an HTTP ``status_code``, and
an optional list of field-level ``details``.  Callers can catch the base
class to handle any platform error uniformly, or catch specific subclasses
for fine-grained control.

Exception groups
----------------
- Authentication  : credential, token, and account-state failures (401/403).
- Authorization   : role and permission enforcement (403).
- Not Found       : missing resource lookups (404).
- Validation      : input and business-rule violations (409/422).
- Conflict        : duplicate or state-conflict errors (409).
- Financial       : wallet, escrow, and payment failures (400/500).
"""

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class AuctionPlatformException(Exception):  # noqa: N818
    """Root exception for all auction platform errors.

    Every domain exception inherits from this class so that a single
    ``except AuctionPlatformException`` clause can catch any platform
    error and serialise it into a consistent HTTP error response.

    Attributes:
        message: Human-readable description of the error.
        code: Upper-snake-case machine-readable error identifier,
            e.g. ``"INVALID_CREDENTIALS"``.
        status_code: HTTP status code that should be returned to the client.
        details: Optional list of supplementary error objects, typically
            used for field-level validation errors.

    """

    def __init__(
        self,
        message: str,
        code: str,
        status_code: int,
        details: list | None = None,
    ) -> None:
        """Initialise the exception with structured error metadata.

        Args:
            message: Human-readable error description.
            code: Machine-readable error code string.
            status_code: HTTP status code for the response.
            details: Optional list of supplementary error detail objects.

        """
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)


# ---------------------------------------------------------------------------
# Authentication  (HTTP 401 / 403)
# ---------------------------------------------------------------------------


class InvalidCredentialsException(AuctionPlatformException):
    """Raised when a login attempt fails due to wrong email or password."""

    def __init__(self, message: str = "Invalid credentials") -> None:
        """Initialise with error code ``INVALID_CREDENTIALS`` and HTTP 401."""
        super().__init__(
            message=message,
            code="INVALID_CREDENTIALS",
            status_code=401,
        )


class TokenExpiredException(AuctionPlatformException):
    """Raised when a JWT or session token has passed its expiry time."""

    def __init__(self, message: str = "Token has expired") -> None:
        """Initialise with error code ``TOKEN_EXPIRED`` and HTTP 401."""
        super().__init__(message=message, code="TOKEN_EXPIRED", status_code=401)


class TokenInvalidException(AuctionPlatformException):
    """Raised when a token cannot be decoded or its signature is invalid."""

    def __init__(self, message: str = "Token is invalid") -> None:
        """Initialise with error code ``TOKEN_INVALID`` and HTTP 401."""
        super().__init__(message=message, code="TOKEN_INVALID", status_code=401)


class EmailNotVerifiedException(AuctionPlatformException):
    """Raised when an action requires a verified email but the user has not done so.

    HTTP 403 is returned since the account exists but access is restricted
    until the email address is verified.
    """

    def __init__(self, message: str = "Email address is not verified") -> None:
        """Initialise with error code ``EMAIL_NOT_VERIFIED`` and HTTP 403."""
        super().__init__(message=message, code="EMAIL_NOT_VERIFIED", status_code=403)


class AccountSuspendedException(AuctionPlatformException):
    """Raised when a suspended account attempts an authenticated action."""

    def __init__(self, message: str = "Account has been suspended") -> None:
        """Initialise with error code ``ACCOUNT_SUSPENDED`` and HTTP 403."""
        super().__init__(message=message, code="ACCOUNT_SUSPENDED", status_code=403)


class AccountBannedException(AuctionPlatformException):
    """Raised when a permanently banned account attempts an authenticated action."""

    def __init__(self, message: str = "Account has been banned") -> None:
        """Initialise with error code ``ACCOUNT_BANNED`` and HTTP 403."""
        super().__init__(message=message, code="ACCOUNT_BANNED", status_code=403)


# ---------------------------------------------------------------------------
# Authorization  (HTTP 403)
# ---------------------------------------------------------------------------


class PermissionDeniedException(AuctionPlatformException):
    """Raised when an authenticated user lacks the required permission."""

    def __init__(self, message: str = "Permission denied") -> None:
        """Initialise with error code ``PERMISSION_DENIED`` and HTTP 403."""
        super().__init__(message=message, code="PERMISSION_DENIED", status_code=403)


class AdminRequiredException(AuctionPlatformException):
    """Raised when an endpoint is restricted to admin users only."""

    def __init__(self, message: str = "Admin access required") -> None:
        """Initialise with error code ``ADMIN_REQUIRED`` and HTTP 403."""
        super().__init__(message=message, code="ADMIN_REQUIRED", status_code=403)


class SellerRequiredException(AuctionPlatformException):
    """Raised when an endpoint requires a verified seller account."""

    def __init__(self, message: str = "Verified seller account required") -> None:
        """Initialise with error code ``SELLER_REQUIRED`` and HTTP 403."""
        super().__init__(message=message, code="SELLER_REQUIRED", status_code=403)


# ---------------------------------------------------------------------------
# Not Found  (HTTP 404)
# ---------------------------------------------------------------------------


class NotFoundException(AuctionPlatformException):
    """Base exception for any resource that cannot be located.

    Concrete subclasses supply a domain-specific ``code``; this class
    fixes the HTTP status at 404.
    """

    def __init__(self, message: str, code: str) -> None:
        """Initialise with the given message and code, HTTP 404.

        Args:
            message: Human-readable description of what was not found.
            code: Machine-readable error code for the missing resource type.

        """
        super().__init__(message=message, code=code, status_code=404)


class UserNotFoundException(NotFoundException):
    """Raised when a user record cannot be found by the given identifier."""

    def __init__(self, message: str = "User not found") -> None:
        """Initialise with error code ``USER_NOT_FOUND``."""
        super().__init__(message=message, code="USER_NOT_FOUND")


class AuctionNotFoundException(NotFoundException):
    """Raised when an auction cannot be found by the given identifier."""

    def __init__(self, message: str = "Auction not found") -> None:
        """Initialise with error code ``AUCTION_NOT_FOUND``."""
        super().__init__(message=message, code="AUCTION_NOT_FOUND")


class BidNotFoundException(NotFoundException):
    """Raised when a bid cannot be found by the given identifier."""

    def __init__(self, message: str = "Bid not found") -> None:
        """Initialise with error code ``BID_NOT_FOUND``."""
        super().__init__(message=message, code="BID_NOT_FOUND")


class OrderNotFoundException(NotFoundException):
    """Raised when an order cannot be found by the given identifier."""

    def __init__(self, message: str = "Order not found") -> None:
        """Initialise with error code ``ORDER_NOT_FOUND``."""
        super().__init__(message=message, code="ORDER_NOT_FOUND")


class WalletNotFoundException(NotFoundException):
    """Raised when a wallet cannot be found for the given user."""

    def __init__(self, message: str = "Wallet not found") -> None:
        """Initialise with error code ``WALLET_NOT_FOUND``."""
        super().__init__(message=message, code="WALLET_NOT_FOUND")


# ---------------------------------------------------------------------------
# Validation  (HTTP 422)
# ---------------------------------------------------------------------------


class ValidationException(AuctionPlatformException):
    """Raised when request input fails schema or business-rule validation.

    Accepts an optional ``details`` list to carry field-level error
    information back to the client.
    """

    def __init__(
        self,
        message: str = "Validation failed",
        details: list | None = None,
    ) -> None:
        """Initialise with error code ``VALIDATION_ERROR`` and HTTP 422.

        Args:
            message: Summary of the validation failure.
            details: Optional list of field-level error detail objects.

        """
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class InsufficientFundsException(AuctionPlatformException):
    """Raised when a user's available balance is too low for the operation."""

    def __init__(self, message: str = "Insufficient funds") -> None:
        """Initialise with error code ``INSUFFICIENT_FUNDS`` and HTTP 422."""
        super().__init__(message=message, code="INSUFFICIENT_FUNDS", status_code=422)


class InvalidBidAmountException(AuctionPlatformException):
    """Raised when a bid amount does not meet the auction's minimum increment."""

    def __init__(self, message: str = "Invalid bid amount") -> None:
        """Initialise with error code ``INVALID_BID_AMOUNT`` and HTTP 422."""
        super().__init__(message=message, code="INVALID_BID_AMOUNT", status_code=422)


# ---------------------------------------------------------------------------
# Conflict  (HTTP 409)
# ---------------------------------------------------------------------------


class AuctionNotActiveException(AuctionPlatformException):
    """Raised when an action requires an active auction but it is not active."""

    def __init__(self, message: str = "Auction is not active") -> None:
        """Initialise with error code ``AUCTION_NOT_ACTIVE`` and HTTP 409."""
        super().__init__(message=message, code="AUCTION_NOT_ACTIVE", status_code=409)


class AuctionEndedException(AuctionPlatformException):
    """Raised when an action is attempted on an auction that has already ended."""

    def __init__(self, message: str = "Auction has ended") -> None:
        """Initialise with error code ``AUCTION_ENDED`` and HTTP 409."""
        super().__init__(message=message, code="AUCTION_ENDED", status_code=409)


class AlreadyExistsException(AuctionPlatformException):
    """Raised when attempting to create a resource that already exists."""

    def __init__(self, message: str = "Resource already exists") -> None:
        """Initialise with error code ``ALREADY_EXISTS`` and HTTP 409."""
        super().__init__(message=message, code="ALREADY_EXISTS", status_code=409)


class AlreadyHighestBidderException(AuctionPlatformException):
    """Raised when a user bids again while already holding the highest bid."""

    def __init__(self, message: str = "You are already the highest bidder") -> None:
        """Initialise with error code ``ALREADY_HIGHEST_BIDDER`` and HTTP 409."""
        super().__init__(
            message=message, code="ALREADY_HIGHEST_BIDDER", status_code=409
        )


class SellerCannotBidException(AuctionPlatformException):
    """Raised when a seller attempts to bid on their own auction."""

    def __init__(
        self, message: str = "Sellers cannot bid on their own auctions"
    ) -> None:
        """Initialise with error code ``SELLER_CANNOT_BID`` and HTTP 409."""
        super().__init__(message=message, code="SELLER_CANNOT_BID", status_code=409)


class DisputeAlreadyExistsException(AuctionPlatformException):
    """Raised when a dispute is opened for an order that already has one."""

    def __init__(
        self, message: str = "A dispute already exists for this order"
    ) -> None:
        """Initialise with error code ``DISPUTE_ALREADY_EXISTS`` and HTTP 409."""
        super().__init__(
            message=message, code="DISPUTE_ALREADY_EXISTS", status_code=409
        )


# ---------------------------------------------------------------------------
# Financial  (HTTP 400 / 500)
# ---------------------------------------------------------------------------


class WalletLockException(AuctionPlatformException):
    """Raised when the system fails to lock funds in a user's wallet.

    Typically indicates a concurrency issue or an unexpected database error
    during the fund-locking step of the bid or checkout flow.
    """

    def __init__(self, message: str = "Failed to lock wallet funds") -> None:
        """Initialise with error code ``WALLET_LOCK_FAILED`` and HTTP 500."""
        super().__init__(message=message, code="WALLET_LOCK_FAILED", status_code=500)


class EscrowCreationException(AuctionPlatformException):
    """Raised when the system fails to create an escrow record for an order."""

    def __init__(self, message: str = "Failed to create escrow") -> None:
        """Initialise with error code ``ESCROW_CREATION_FAILED`` and HTTP 500."""
        super().__init__(
            message=message, code="ESCROW_CREATION_FAILED", status_code=500
        )


class PaymentVerificationException(AuctionPlatformException):
    """Raised when a payment gateway callback cannot be verified."""

    def __init__(self, message: str = "Payment verification failed") -> None:
        """Initialise with error code ``PAYMENT_VERIFICATION_FAILED`` and HTTP 400."""
        super().__init__(
            message=message,
            code="PAYMENT_VERIFICATION_FAILED",
            status_code=400,
        )
