# LDAP Inviter Bot

## Roadmap
- [x] Implement `ldap-sync` command, that invites hardcoded users to hardcoded aliases
- [x] Create rooms behind aliases, if they don't exist
- [x] Only allow a list of admin users to run sync
- [ ] Support templating in room names `ldap-sync <1> <2> ...`
- [ ] Get list of users from LDAP


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