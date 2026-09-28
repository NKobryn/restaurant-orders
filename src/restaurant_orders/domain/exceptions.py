"""Hierarchy of errors of the restaurant domain."""


class RestaurantError(Exception):
    """Base class for all errors of the restaurant domain."""


class CurrencyMismatchError(RestaurantError):
    """Raised when money in different currencies is combined."""


class DishNotFoundError(RestaurantError):
    """Raised when the menu has no dish with the requested id."""


class OrderNotFoundError(RestaurantError):
    """Raised when the repository has no order with the requested id."""


class OrderStateError(RestaurantError):
    """Raised when an operation is not allowed for the current order status."""


class PaymentError(RestaurantError):
    """Raised when a payment gateway cannot accept the payment."""


class DeliveryError(RestaurantError):
    """Raised when an order cannot be passed to delivery."""
