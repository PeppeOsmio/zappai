"""Add soil type

Revision ID: 58ccf6374d4d
Revises: 9213ee217063
Create Date: 2024-07-20 11:12:03.693897

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = '58ccf6374d4d'
down_revision: Union[str, None] = '9213ee217063'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('soil_type',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', name='_name_nc')
    )
    op.add_column('location', sa.Column('soil_type_id', sa.Uuid(), nullable=False))
    op.create_foreign_key(None, 'location', 'soil_type', ['soil_type_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'location', type_='foreignkey') # type: ignore
    op.drop_column('location', 'soil_type_id')
    op.drop_table('soil_type')
    # ### end Alembic commands ###
