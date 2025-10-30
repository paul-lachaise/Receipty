from pydantic import BaseModel, Field, field_validator, model_validator, PositiveInt
from enum import Enum
from typing import List, Optional
from datetime import date, datetime
from uuid import UUID
from decimal import Decimal


# Enums for controlled vocabularies


class Status(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Categories(str, Enum):
    ALIMENTATION = "Alimentation"
    LOISIRS = "Loisirs"
    TRANSPORT = "Transport"
    MAISON = "Maison"
    VETEMENTS = "Vêtements"
    SANTE = "Santé"
    FACTURES = "Factures"
    TECHNOLOGIE = "Technologie"
    AUTRE = "Autre"


# Model representing a single item extracted by the LLM


class ItemData(BaseModel):
    """Represents a single item extracted from the receipt text by the LLM."""

    name: str = Field(..., min_length=1, description="The name of the item purchased.")
    quantity: PositiveInt = Field(
        ..., description="The quantity of the item purchased (must be 1 or more)."
    )
    price: Decimal = Field(
        ...,
        ge=0,
        description="The price for a single unit of the item. Must be non-negative.",
    )
    category: Categories = Field(
        default=Categories.AUTRE,
        description="The expense category assigned to this item.",
    )

    @field_validator("price", mode="before")
    @classmethod
    def price_must_be_decimal(cls, value):
        # Ensure price is handled as Decimal for financial accuracy
        try:
            # Handle potential currency symbols or spaces returned by LLM
            if isinstance(value, str):
                value = value.replace("€", "").replace("EUR", "").strip()
            dec_value = Decimal(value)
            if dec_value < 0:
                raise ValueError("Unit price must be non-negative")
            return dec_value
        except Exception:
            raise ValueError("Unit price must be a valid number")


# Model representing the structured data expected from the LLM


class StructuredReceiptData(BaseModel):
    """
    Defines the structure of the JSON data expected from the LLM after analyzing receipt text.
    This model serves as the contract for the LLM's output and includes validation.
    """

    merchant: str = Field(..., min_length=1, description="The name of the merchant.")
    receipt_date: date = Field(
        ..., description="The date of the transaction (YYYY-MM-DD format)."
    )
    total_amount: Decimal = Field(
        ..., ge=0, description="The final total amount paid. Must be non-negative."
    )
    items: List[ItemData] = Field(
        ...,
        min_length=1,
        description="A list containing details of each item purchased.",
    )

    @field_validator("total_amount", mode="before")
    @classmethod
    def total_amount_must_be_decimal(cls, value):
        try:
            # Handle potential currency symbols or spaces returned by LLM
            if isinstance(value, str):
                value = value.replace("€", "").replace("EUR", "").strip()
            dec_value = Decimal(value)
            if dec_value < 0:
                raise ValueError("Total amount must be non-negative")
            return dec_value
        except Exception:
            raise ValueError("Total amount must be a valid number")

    @field_validator("receipt_date", mode="before")
    @classmethod
    def parse_date(cls, value):
        # Allow LLM to return date as string, parse it here
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        elif isinstance(value, date):
            return value
        raise ValueError("Date must be a string in YYYY-MM-DD format or a date object")

    @model_validator(mode="after")
    def check_total_matches_items_sum(self) -> "StructuredReceiptData":
        """
        Validates that the sum of (price * quantity) for all items
        approximately matches the total_amount.
        """
        calculated_sum = sum(item.price * item.quantity for item in self.items)
        # Allow a small tolerance for potential rounding differences
        tolerance = Decimal("0.02")

        if abs(calculated_sum - self.total_amount) > tolerance:
            raise ValueError(
                f"Sum of item totals ({calculated_sum:.2f}) does not match "
                f"the receipt total amount ({self.total_amount:.2f}) within tolerance."
            )
        return self


# Models representing the database tables


class ReceiptDB(BaseModel):
    """Represents a row in the 'receipts' database table."""

    id: UUID
    user_id: UUID
    created_at: Optional[datetime] = None
    extracted_text: Optional[str] = Field(
        None, description="Raw text extracted by OCR."
    )
    status: Status = Field(
        default=Status.PENDING, description="Processing status of the receipt."
    )
    merchant: Optional[str] = Field(None, description="Merchant name extracted by LLM.")
    receipt_date: Optional[date] = Field(
        None, description="Transaction date extracted by LLM."
    )
    total_amount: Optional[Decimal] = Field(
        None, description="Total amount extracted by LLM."
    )

    class Config:
        from_attributes = True


class ItemDB(BaseModel):
    """Represents a row in the 'items' database table."""

    id: UUID
    receipt_id: UUID = Field(
        ..., description="Foreign key linking to the 'receipts' table."
    )
    name: str = Field(..., min_length=1, description="Name of the item.")
    price: Decimal = Field(
        ..., ge=0, description="Price for a single unit of the item."
    )
    quantity: PositiveInt = Field(..., description="Quantity purchased.")
    category: Categories = Field(..., description="Expense category.")

    class Config:
        from_attributes = True
