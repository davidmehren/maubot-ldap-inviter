# LDAP Inviter Bot

This is a [maubot](https://github.com/maubot/maubot) plugin that invites users to Matrix rooms
according to their membership in LDAP groups.
It was built in an educational context, where groups of students work on software projects.
The bot ensures that participating students are invited to all rooms
(general chat, announcement-only, helpdesk & their group chat) and that tutors have correct power levels in the corresponding rooms.

**Features:**
- Ensure that a room with the configured alias exists and has the correct name
- Invite users from LDAP and from the config and give them the configured power levels
- Set the room visibility
- Room aliases, room names and LDAP DNs are templateable.
- Matrix IDs of LDAP users are generated using the `uid` attribute from LDAP and a configurable homeserver.
- The bot does not remove or uninvite users from rooms. This is intentional, to allow students to join with their own Matrix accounts.

## Notes
### Dependencies
This Bot requires the `python-ldap` library.
It must be installed manually in the python environment used by your Maubot instance.
If you run Maubot via the official Docker image, run `apk add py3-pyldap` in the container.

### Rate Limiting
The bot will quickly run into rate limits.
You can use the Synapse Admin API to remove rate limits for the bot user.
See https://matrix-org.github.io/synapse/latest/admin_api/user_admin_api.html#override-ratelimiting-for-users
for more details.

## Config
```yaml
# LDAP config
ldap:
  uri: 'ldap://foo.bar.tld:389' # URI of your LDAP server
  base_dn: 'cn=users,dc=foo,dc=bar,dc=tld' # base-DN of your user objects
  connect_dn: 'uid=ldap-bot,cn=users,dc=foo,dc=bar,dc=tld' # DN of the user used to bind
  connect_password: 'verySecure' # password of the user used to bind
  user_filter:  '(objectClass=inetOrgPerson)'
  mxid_homeserver: 'matrix.server.tld' # Homeserver used to generate MXIDs from LDAP uids
  
# Rooms that should be synced
sync_rooms:
  - alias: '#event-<1>-group-1:matrix.server.tld' # Aliases can include '<1>' placeholders
    # Should the room be visible in the room list?
    # Can be 'private' or 'public'
    visibility: 'private'
    # Names can include '<1>' placeholders
    name: 'Foo <1>'
    # LDAP members for this room
    ldap_members:
      - ldap_group: 'cn=event-<1>-group1,cn=groups,dc=foo,dc=bar,dc=tld'
        power_level: 0
        # Groups can include '<1>' placeholders
      - ldap_group: 'cn=event-<1>-tutors1,cn=groups,dc=foo,dc=bar,dc=tld'
        power_level: 100
    # Hardcoded members for this room
    members:
      - mxid: '@super.admin:matrix.server.tld'
        power_level: 100
        
# Users that are allowed to run a sync
admin_users:
  - '@super.admin:matrix.server.tld'
```

## Usage
To check the connection to your LDAP server, write `!ldap-check` in a room with the bot.
It will print out the computed members for all configured rooms.

To run the actual invite process, write `!ldap-sync` in a room with the bot.