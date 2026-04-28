"""init

Revision ID: 698e3e71754c
Revises: c10318438058
Create Date: 2026-04-29 00:54:28.718233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '698e3e71754c'
down_revision: Union[str, Sequence[str], None] = 'c10318438058'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
