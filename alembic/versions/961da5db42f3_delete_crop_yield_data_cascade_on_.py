"""Delete crop_yield_data cascade on location_id

Revision ID: 961da5db42f3
Revises: d71f4b34ee85
Create Date: 2024-09-15 22:13:59.379076

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = '961da5db42f3'
down_revision: Union[str, None] = 'd71f4b34ee85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('crop_yield_data_location_id_fkey', 'crop_yield_data', type_='foreignkey')
    op.create_foreign_key(None, 'crop_yield_data', 'location', ['location_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'crop_yield_data', type_='foreignkey')
    op.create_foreign_key('crop_yield_data_location_id_fkey', 'crop_yield_data', 'location', ['location_id'], ['id'])
    # ### end Alembic commands ###
