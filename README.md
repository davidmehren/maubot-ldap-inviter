# LDAP Inviter Bot

## Roadmap
- [x] Implement `ldap-sync` command, that invites hardcoded users to hardcoded aliases
- [x] Create rooms behind aliases, if they don't exist
- [x] Only allow a list of admin users to run sync
- [ ] Support templating in room names `ldap-sync <1> <2> ...`
- [ ] Get list of users from LDAP

## Note
The bot will quickly run into rate limits.
You can use the Synapse Admin API to remove rate limits for the bot user.
See https://matrix-org.github.io/synapse/latest/admin_api/user_admin_api.html#override-ratelimiting-for-users
for more details.

## Config
```yaml
ldap:
  uri: 'ldap://foo.bar.tls:389'
  ...
sync_rooms:
  - alias: '#foo-<1>:server.tld'
    visibility: 'private'
    name: 'Foo <1>'
    members:
      - ldap_group: 'cn=users-<1>,cn=groups,dc=foo,dc=bar,dc=tld'
        power_level: 0
      - ldap_group: 'cn=admins-<1>,cn=groups,dc=foo,dc=bar,dc=tld'
        power_level: 100
```