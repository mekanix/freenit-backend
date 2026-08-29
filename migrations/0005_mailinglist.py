"""Auto-generated migration.

Created: 2026-08-29 03:12:05
"""

depends_on = "0004_lms"


def upgrade(ctx):
    """Apply migration."""
    ctx.create_table(
        "mailing_list",
        fields=[
            {
                'name': 'id',
                'column_type': {
                    'kind': 'big_integer'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': True,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'name',
                'column_type': {
                    'kind': 'string'
                },
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': True,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'address',
                'column_type': {
                    'kind': 'unknown'
                },
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': True,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'distribution_address',
                'column_type': {
                    'kind': 'unknown'
                },
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': True,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'archive_address',
                'column_type': {
                    'kind': 'unknown'
                },
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': True,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'description',
                'column_type': {
                    'kind': 'string'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'public',
                'column_type': {
                    'kind': 'boolean'
                },
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': '1',
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'archive_enabled',
                'column_type': {
                    'kind': 'boolean'
                },
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': '1',
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'moderation_enabled',
                'column_type': {
                    'kind': 'boolean'
                },
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': '0',
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'principal_id',
                'column_type': {
                    'kind': 'big_integer'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'inbox_principal_id',
                'column_type': {
                    'kind': 'big_integer'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'archive_principal_id',
                'column_type': {
                    'kind': 'big_integer'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'created_at',
                'column_type': {
                    'kind': 'date_time'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'updated_at',
                'column_type': {
                    'kind': 'date_time'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            }
        ],
    )
    ctx.create_table(
        "mailing_list_subscriber",
        fields=[
            {
                'name': 'id',
                'column_type': {
                    'kind': 'big_integer'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': True,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'email',
                'column_type': {
                    'kind': 'unknown'
                },
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'created_at',
                'column_type': {
                    'kind': 'date_time'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'mailing_list_id',
                'column_type': {
                    'kind': 'big_integer'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            }
        ],
        foreign_keys=[
            {
                'name': 'fk_mailing_list_subscriber_mailing_list_id',
                'columns': [
                    'mailing_list_id'
                ],
                'ref_table': 'mailing_list',
                'ref_columns': [
                    'id'
                ],
                'on_delete': 'CASCADE',
                'on_update': 'CASCADE'
            }
        ],
    )
    ctx.create_table(
        "moderation_message",
        fields=[
            {
                'name': 'id',
                'column_type': {
                    'kind': 'big_integer'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': True,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'message_id',
                'column_type': {
                    'kind': 'string'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'subject',
                'column_type': {
                    'kind': 'string'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'sender',
                'column_type': {
                    'kind': 'unknown'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'sent_at',
                'column_type': {
                    'kind': 'date_time'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'text_body',
                'column_type': {
                    'kind': 'string'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'html_body',
                'column_type': {
                    'kind': 'string'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'status',
                'column_type': {
                    'kind': 'string'
                },
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': "'pending'",
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'created_at',
                'column_type': {
                    'kind': 'date_time'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'decided_at',
                'column_type': {
                    'kind': 'date_time'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'mailing_list_id',
                'column_type': {
                    'kind': 'big_integer'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            }
        ],
        foreign_keys=[
            {
                'name': 'fk_moderation_message_mailing_list_id',
                'columns': [
                    'mailing_list_id'
                ],
                'ref_table': 'mailing_list',
                'ref_columns': [
                    'id'
                ],
                'on_delete': 'CASCADE',
                'on_update': 'CASCADE'
            }
        ],
    )
    ctx.create_table(
        "pending_subscriber",
        fields=[
            {
                'name': 'id',
                'column_type': {
                    'kind': 'big_integer'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': True,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'email',
                'column_type': {
                    'kind': 'unknown'
                },
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'token',
                'column_type': {
                    'kind': 'string'
                },
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'action',
                'column_type': {
                    'kind': 'string'
                },
                'db_type': None,
                'nullable': False,
                'primary_key': False,
                'unique': False,
                'default': "'subscribe'",
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'created_at',
                'column_type': {
                    'kind': 'date_time'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            },
            {
                'name': 'mailing_list_id',
                'column_type': {
                    'kind': 'big_integer'
                },
                'db_type': None,
                'nullable': True,
                'primary_key': False,
                'unique': False,
                'default': None,
                'auto_increment': False,
                'max_length': None,
                'max_digits': None,
                'decimal_places': None
            }
        ],
        foreign_keys=[
            {
                'name': 'fk_pending_subscriber_mailing_list_id',
                'columns': [
                    'mailing_list_id'
                ],
                'ref_table': 'mailing_list',
                'ref_columns': [
                    'id'
                ],
                'on_delete': 'CASCADE',
                'on_update': 'CASCADE'
            }
        ],
    )


def downgrade(ctx):
    """Revert migration."""
    ctx.drop_table("pending_subscriber")
    ctx.drop_table("moderation_message")
    ctx.drop_table("mailing_list_subscriber")
    ctx.drop_table("mailing_list")
