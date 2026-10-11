"""support problem aliases and multiple topics

Revision ID: bc0faa1b7f6d
Revises:
Create Date: 2026-10-11 22:00:55.281268

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bc0faa1b7f6d"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add aliases to existing problems.
    op.add_column(
        "problems",
        sa.Column(
            "aliases",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )

    # Create the many-to-many association table.
    op.create_table(
        "problem_topics",
        sa.Column("problem_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["problem_id"],
            ["problems.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("problem_id", "topic_id"),
    )

    # Preserve existing problem-topic assignments.
    op.execute(
        """
        INSERT INTO problem_topics (problem_id, topic_id)
        SELECT id, topic_id
        FROM problems
        WHERE topic_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_table("problem_topics")

    with op.batch_alter_table("problems") as batch_op:
        batch_op.drop_column("aliases")
