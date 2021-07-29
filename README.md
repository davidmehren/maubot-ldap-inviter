# LDAP Inviter Bot

## Roadmap
- [x] Implement `ldap-sync` command, that invites hardcoded users to hardcoded aliases
- [x] Create rooms behind aliases, if they don't exist
- [x] Only allow a list of admin users to run sync
- [x] Support templating in room names `ldap-sync <1> <2> ...`
  - Only implemented with one argument
- [ ] Get list of users from LDAP

## Note
The bot will quickly run into rate limits.
You can use the Synapse Admin API to remove rate limits for the bot user.
See https://matrix-org.github.io/synapse/latest/admin_api/user_admin_api.html#override-ratelimiting-for-users
for more details.

## Config
```yaml
# LDAP config (TBD)
ldap:
  uri: 'ldap://foo.bar.tls:389'
# Rooms that should be synced
sync_rooms:
    # Aliases can include '<1>' placeholders
  - alias: '#alias-<1>:matrix.server.tld'
    # Should the room be visible in the room list?
    # Can be 'private' or 'public'
    visibility: 'private'
    # Names can include '<1>' placeholders
    name: 'Foo <1>'
    # LDAP members for this room
    ldap_members:
        # Groups can include '<1>' placeholders
      - ldap_group: 'cn=users-<1>,cn=groups,dc=foo,dc=bar,dc=tld'
        power_level: 0
      - ldap_group: 'cn=admins-<1>,cn=groups,dc=foo,dc=bar,dc=tld'
        power_level: 100
    # Hardcoded members for this room
    members:
      - mxid: '@some.user:matrix.server.tld'
# Users that are allowed to run a sync
admin_users:
  - '@some.admin:matrix.server.tld'
```