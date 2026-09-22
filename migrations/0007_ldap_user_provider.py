"""Add provider column to the user table for LDAP tracking."""

depends_on = "0006_git"


def upgrade(ctx):
    ctx.add_column(
        "user",
        {
            "name": "provider",
            "python_type": "str",
            "db_type": None,
            "nullable": False,
            "primary_key": False,
            "unique": False,
            "default": "local",
            "auto_increment": False,
        },
    )


def downgrade(ctx):
    ctx.drop_column("user", "provider")
