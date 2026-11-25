# Changelog

## 0.2.0 (2026-11-25)

- **Contact groups**: `client.groups` with `create`, `list`, `get`, `update`, `delete`, `list_members`,
  `list_all_members`, `add_members` and `remove_member`, on both clients. A group can have join keywords: people text one to your phone to
  join, and you get a `group.joined`
  webhook event.
- **Campaigns**: `client.campaigns` with `create`, `list`, `get`, `update`, `delete`, `preview`,
  `results`, `send`, `control` (pause or resume) and `cancel`.
- **Languages**: `language` on a send, a bulk send and a one-time code. A template with a text per
  language picks the recipient's language (from their contact) unless you name one.
- **Choosing the sender**: `phone` sends from one phone only; `from_` (sent as `from`) asks for a SIM by the
  name or number you gave it on the dashboard; `sim` alone now picks only the project's phones that have
  that slot.
- **Bulk sends to groups**: `group_ids` on a bulk send.

## 0.1.0 (2026-11-10)

- First release: messages, one-time codes, recurring schedules and webhook verification, sync and async clients.
